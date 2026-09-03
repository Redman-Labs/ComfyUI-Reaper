"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

"""Image nodes for the Reaper ComfyUI extension.

All ComfyUI nodes registered in the Images category are consolidated
here. ``ReaperImageNodes`` is ordered alphabetically by display name.
"""

import torch

from comfy import model_management

from comfy_api.latest import io

from ..._helpers._types import CropInfo

import os

import random

import re

import time

import uuid

from concurrent.futures import ThreadPoolExecutor

import folder_paths

import numpy as np

from PIL import Image

import hashlib

import json

import logging

import math

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageSequence

from PIL.PngImagePlugin import PngInfo

import node_helpers

from ..._helpers._rlabs_resize_helpers import _resize_frame

from ..._helpers._load_images_folder import (
    DEFAULT_STATE as LOAD_IMAGES_FOLDER_DEFAULT_STATE,
    _ReaperLoadImagesFolderEngine,
)

from typing import Any

from dataclasses import replace

from comfy_extras.nodes_post_processing import (
    ResizeImageMaskNode,
    ResizeType,
    scale_dimensions,
)

import comfy.utils

from spandrel import ImageModelDescriptor, ModelLoader

try:
    from spandrel import MAIN_REGISTRY
    from spandrel_extra_arches import EXTRA_REGISTRY

    MAIN_REGISTRY.add(*EXTRA_REGISTRY)
except Exception:
    pass

def _rgb_to_hsv(image: torch.Tensor) -> torch.Tensor:
    r, g, b = image.unbind(-1)
    maximum, maximum_index = image.max(dim=-1)
    minimum = image.min(dim=-1).values
    difference = maximum - minimum
    safe_difference = difference + 1e-7

    hue = torch.zeros_like(maximum)
    hue = torch.where(maximum_index == 0, (g - b) / safe_difference, hue)
    hue = torch.where(maximum_index == 1, 2.0 + (b - r) / safe_difference, hue)
    hue = torch.where(maximum_index == 2, 4.0 + (r - g) / safe_difference, hue)
    hue = (hue / 6.0).remainder(1.0)
    saturation = difference / (maximum + 1e-7)
    value = maximum
    return torch.stack((hue, saturation, value), dim=-1)

def _hsv_to_rgb(hsv: torch.Tensor) -> torch.Tensor:
    hue, saturation, value = hsv.unbind(-1)
    hue = hue.remainder(1.0) * 6.0
    sector = torch.floor(hue).long().remainder(6)
    fraction = hue - torch.floor(hue)
    p = value * (1.0 - saturation)
    q = value * (1.0 - saturation * fraction)
    t = value * (1.0 - saturation * (1.0 - fraction))

    red = torch.where(
        sector == 0,
        value,
        torch.where(
            sector == 1,
            q,
            torch.where(sector == 2, p, torch.where(sector == 3, p, torch.where(sector == 4, t, value))),
        ),
    )
    green = torch.where(
        sector == 0,
        t,
        torch.where(
            sector == 1,
            value,
            torch.where(sector == 2, value, torch.where(sector == 3, q, p)),
        ),
    )
    blue = torch.where(
        sector == 0,
        p,
        torch.where(
            sector == 1,
            p,
            torch.where(sector == 2, t, torch.where(sector == 3, value, torch.where(sector == 4, value, q))),
        ),
    )
    return torch.stack((red, green, blue), dim=-1)

ReaperImageInfo = io.Custom("REAPER_IMAGE_INFO")

_MINI_DEFAULT_STATE = {
    "version": 1,
    "mode": "off",
    "max_mp": 1.0,
    "longest_side": 1024,
    "scale_factor": 1.0,
    "fit_w": 1024,
    "fit_h": 1024,
    "cover_w": 1024,
    "cover_h": 1024,
    "ratio_preset": "1:1",
    "ratio_w": 1,
    "ratio_h": 1,
    "ratio_action": "crop",
    "pad_color": "#808080",
    "pad_top": 0,
    "pad_bottom": 0,
    "pad_left": 0,
    "pad_right": 0,
    "crop_anchor": "center",
    "crop_scale": True,
    "snap": 0,
    "resample": "auto",
    "allow_upscale": True,
}

def _parse_mini_state(value: str) -> dict:
    if not value:
        return dict(_MINI_DEFAULT_STATE)
    try:
        parsed = json.loads(value)
        state = dict(_MINI_DEFAULT_STATE)
        state.update({key: item for key, item in parsed.items() if key in state})
        return state
    except Exception:
        return dict(_MINI_DEFAULT_STATE)

def _parse_original_name(value: str) -> str:
    try:
        name = json.loads(value).get("orig_name") if value else ""
        return name if isinstance(name, str) else ""
    except Exception:
        return ""

_RESIZE_MODES = [
    "Off",
    "Max Megapixels",
    "Longest Side",
    "Scale By",
    "Fit Inside",
    "Crop to Fill",
    "Match Ratio",
]

_RESAMPLE = {
    "Nearest": Image.Resampling.NEAREST,
    "Bilinear": Image.Resampling.BILINEAR,
    "Bicubic": Image.Resampling.BICUBIC,
    "Lanczos": Image.Resampling.LANCZOS,
}

def _image_files() -> list[str]:
    root = folder_paths.get_input_directory()
    files: list[str] = []
    if os.path.isdir(root):
        for directory, _subdirectories, names in os.walk(root):
            relative_root = os.path.relpath(directory, root)
            for name in names:
                relative = name if relative_root == "." else os.path.join(relative_root, name)
                files.append(relative.replace("\\", "/"))
    return sorted(folder_paths.filter_files_content_types(files, ["image"]))

def _snap(value: int, multiple: int) -> int:
    value = max(8, min(int(value), 16384))
    if multiple > 1:
        value = max(8, (value // multiple) * multiple)
    return value

def _resample(method: str, factor: float):
    if method == "Auto":
        return Image.Resampling.LANCZOS if factor < 1.0 else Image.Resampling.BILINEAR
    return _RESAMPLE.get(method, Image.Resampling.BILINEAR)

def _anchor(anchor: str, outer_w: int, outer_h: int, inner_w: int, inner_h: int):
    lower = anchor.lower()
    x = 0 if "left" in lower else outer_w - inner_w if "right" in lower else (outer_w - inner_w) // 2
    y = 0 if "top" in lower else outer_h - inner_h if "bottom" in lower else (outer_h - inner_h) // 2
    return max(0, x), max(0, y)

def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    try:
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
    except (ValueError, TypeError):
        return (0, 0, 0)

def _resize_pair(
    image: Image.Image,
    mask: Image.Image,
    mode: str,
    max_megapixels: float,
    longest_side: int,
    scale_by: float,
    target_width: int,
    target_height: int,
    ratio_width: int,
    ratio_height: int,
    ratio_action: str,
    crop_anchor: str,
    pad_color: str,
    multiple_of: int,
    resampling: str,
    allow_upscale: bool,
) -> tuple[Image.Image, Image.Image]:
    width, height = image.size
    new_width, new_height = width, height
    crop_box = None
    pad_size = None

    if mode == "Max Megapixels":
        factor = math.sqrt(max_megapixels * 1024 * 1024 / max(1, width * height))
        factor = min(factor, 8.0) if allow_upscale else min(factor, 1.0)
        new_width, new_height = round(width * factor), round(height * factor)
    elif mode == "Longest Side":
        factor = longest_side / max(width, height)
        factor = min(factor, 8.0) if allow_upscale else min(factor, 1.0)
        new_width, new_height = round(width * factor), round(height * factor)
    elif mode == "Scale By":
        factor = min(scale_by, 8.0) if allow_upscale else min(scale_by, 1.0)
        new_width, new_height = round(width * factor), round(height * factor)
    elif mode == "Fit Inside":
        factor = min(target_width / width, target_height / height)
        factor = min(factor, 8.0) if allow_upscale else min(factor, 1.0)
        new_width, new_height = round(width * factor), round(height * factor)
    elif mode == "Crop to Fill":
        factor = max(target_width / width, target_height / height)
        factor = min(factor, 8.0) if allow_upscale else min(factor, 1.0)
        scaled_width, scaled_height = round(width * factor), round(height * factor)
        if scaled_width >= target_width and scaled_height >= target_height:
            x, y = _anchor(crop_anchor, scaled_width, scaled_height, target_width, target_height)
            crop_box = (x, y, x + target_width, y + target_height)
            new_width, new_height = scaled_width, scaled_height
        else:
            new_width, new_height = scaled_width, scaled_height
    elif mode == "Match Ratio":
        target_ratio = ratio_width / max(1, ratio_height)
        source_ratio = width / height
        if ratio_action == "Crop":
            crop_width = round(height * target_ratio) if source_ratio > target_ratio else width
            crop_height = height if source_ratio > target_ratio else round(width / target_ratio)
            x, y = _anchor(crop_anchor, width, height, crop_width, crop_height)
            crop_box = (x, y, x + crop_width, y + crop_height)
        else:
            pad_width = width if source_ratio > target_ratio else round(height * target_ratio)
            pad_height = round(width / target_ratio) if source_ratio > target_ratio else height
            pad_size = (pad_width, pad_height)

    defer_snap = mode in ("Crop to Fill", "Match Ratio")
    new_width = _snap(new_width, 0 if defer_snap else multiple_of)
    new_height = _snap(new_height, 0 if defer_snap else multiple_of)
    factor = new_width / width
    if (new_width, new_height) != image.size:
        image = image.resize((new_width, new_height), _resample(resampling, factor))
        mask = mask.resize((new_width, new_height), Image.Resampling.NEAREST)
    if crop_box is not None:
        image = image.crop(crop_box)
        mask = mask.crop(crop_box)
    if pad_size is not None:
        canvas = Image.new("RGB", pad_size, _hex_rgb(pad_color))
        mask_canvas = Image.new("L", pad_size, 255)
        x, y = _anchor("Center", pad_size[0], pad_size[1], image.width, image.height)
        canvas.paste(image, (x, y))
        mask_canvas.paste(mask, (x, y))
        image, mask = canvas, mask_canvas
    if defer_snap:
        final_width = _snap(image.width, multiple_of)
        final_height = _snap(image.height, multiple_of)
        if (final_width, final_height) != image.size:
            factor = final_width / image.width
            image = image.resize((final_width, final_height), _resample(resampling, factor))
            mask = mask.resize((final_width, final_height), Image.Resampling.NEAREST)
    return image, mask

def _json_safe(value: Any) -> Any:
    """Replace non-finite floats so execution metadata remains valid JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value

def _tensor_to_pil(frame: torch.Tensor) -> Image.Image:
    array = frame.detach().cpu().numpy()
    if array.ndim == 3 and array.shape[-1] > 3:
        array = array[..., :3]
    array = (array * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(array)

def _pil_to_tensor(image: Image.Image) -> torch.Tensor:
    array = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(array)[None, ...]

def _snapshot_path(node_id: Any) -> str:
    safe_id = (
        "".join(
            character
            for character in str(node_id)
            if character.isalnum() or character in "_-"
        )
        or "node"
    )
    temp_directory = folder_paths.get_temp_directory()
    os.makedirs(temp_directory, exist_ok=True)
    return os.path.join(temp_directory, f"reaper_pause_{safe_id}.png")

PIXELS_PER_MEGAPIXEL = 1_048_576

_COLOR_MATCH_LOGGER = logging.getLogger("Reaper.ColorMatch")

def _haar_decompose(x):
    # Orthonormal Haar wavelet decomposition.
    # Input: [B, C, H, W] → Output: LL, LH, HL, HH each [B, C, H//2, W//2]
    x = x.float()
    x00 = x[:, :, 0::2, 0::2]
    x01 = x[:, :, 0::2, 1::2]
    x10 = x[:, :, 1::2, 0::2]
    x11 = x[:, :, 1::2, 1::2]
    norm = 0.5 / (2**0.5)
    LL = (x00 + x01 + x10 + x11) * norm
    LH = (x00 - x01 + x10 - x11) * norm
    HL = (x00 + x01 - x10 - x11) * norm
    HH = (x00 - x01 - x10 + x11) * norm
    return LL, LH, HL, HH

def _haar_reconstruct(LL, LH, HL, HH):
    # Orthonormal inverse Haar reconstruction.
    # Input: LL, LH, HL, HH [B, C, H, W] → Output: [B, C, H*2, W*2]
    norm = 1.0 / (2**0.5)
    B, C, H, W = LL.shape
    x00 = (LL + LH + HL + HH) * norm
    x01 = (LL - LH + HL - HH) * norm
    x10 = (LL + LH - HL - HH) * norm
    x11 = (LL - LH - HL + HH) * norm
    out = torch.zeros(B, C, H * 2, W * 2, device=LL.device, dtype=LL.dtype)
    out[:, :, 0::2, 0::2] = x00
    out[:, :, 0::2, 1::2] = x01
    out[:, :, 1::2, 0::2] = x10
    out[:, :, 1::2, 1::2] = x11
    return out

def _wavelet_color_transfer(src_bchw, ref_bchw, strength):
    # Transfer color via Haar wavelets: match LL band statistics, keep detail bands.
    # Operates in LAB space for perceptually uniform transfer.
    import kornia  # type: ignore

    src_lab = kornia.color.rgb_to_lab(src_bchw)

    # Resize ref to match src dimensions (we only need color statistics, not spatial layout)
    _, _, src_H, src_W = src_bchw.shape
    _, _, ref_H, ref_W = ref_bchw.shape
    if ref_H != src_H or ref_W != src_W:
        ref_resized = torch.nn.functional.interpolate(
            ref_bchw, size=(src_H, src_W), mode="bilinear", align_corners=False
        )
    else:
        ref_resized = ref_bchw
    ref_lab = kornia.color.rgb_to_lab(ref_resized)

    B = src_lab.shape[0]
    _, _, H, W = src_lab.shape

    # Pad to even dimensions if needed
    pad_h = H % 2
    pad_w = W % 2
    if pad_h or pad_w:
        src_lab = torch.nn.functional.pad(src_lab, (0, pad_w, 0, pad_h), mode="reflect")
        ref_lab = torch.nn.functional.pad(ref_lab, (0, pad_w, 0, pad_h), mode="reflect")

    src_LL, src_LH, src_HL, src_HH = _haar_decompose(src_lab)
    ref_LL, _, _, _ = _haar_decompose(ref_lab)

    # AdaIN on LL band: normalize src LL, scale/shift by ref LL statistics
    for b in range(B):
        ref_idx = min(b, ref_LL.shape[0] - 1)
        for c in range(3):  # L, A, B channels
            s_mean = src_LL[b, c].mean()
            s_std = src_LL[b, c].std().clamp(min=1e-6)
            r_mean = ref_LL[ref_idx, c].mean()
            r_std = ref_LL[ref_idx, c].std().clamp(min=1e-6)
            src_LL[b, c] = (src_LL[b, c] - s_mean) / s_std * r_std + r_mean

    # Reconstruct with matched LL + original detail bands
    out_lab = _haar_reconstruct(src_LL, src_LH, src_HL, src_HH)

    # Remove padding
    if pad_h or pad_w:
        out_lab = out_lab[:, :, :H, :W]

    out_rgb = kornia.color.lab_to_rgb(out_lab)

    # Apply strength blending
    if strength != 1.0:
        out_rgb = (1.0 - strength) * src_bchw + strength * out_rgb

    return out_rgb.clamp_(0, 1)

def _scattersort_transfer(src_bchw, ref_bchw, strength):
    # Per-channel histogram matching via sort-scatter.
    B, C, H, W = src_bchw.shape
    src_flat = src_bchw.reshape(B, C, -1)  # [B, C, N]
    ref_flat = ref_bchw.reshape(ref_bchw.shape[0], C, -1)

    out_flat = src_flat.clone()
    for b in range(B):
        ref_idx = min(b, ref_flat.shape[0] - 1)
        for c in range(C):
            src_ch = src_flat[b, c]  # [N]
            ref_ch = ref_flat[ref_idx, c]

            # Sort reference values
            ref_sorted = ref_ch.sort()[0]

            # If different pixel counts, interpolate reference distribution
            if src_ch.numel() != ref_ch.numel():
                # Resample ref distribution to src length
                ref_sorted = torch.nn.functional.interpolate(
                    ref_sorted.unsqueeze(0).unsqueeze(0),
                    size=src_ch.numel(),
                    mode="linear",
                    align_corners=True,
                ).squeeze()

            # Get sort indices for src, scatter ref sorted values back
            src_idx = src_ch.argsort()
            out_flat[b, c].scatter_(0, src_idx, ref_sorted)

    if strength != 1.0:
        out_flat = (1.0 - strength) * src_flat + strength * out_flat

    return out_flat.reshape(B, C, H, W).clamp_(0, 1)

_RESAMPLE_OPTIONS = ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"]

def _apply_sharpen(
    s, sharpen_enabled, sharpen_amount, sharpen_ratio, noise_radius, preserve_edges
):
    if not sharpen_enabled:
        return s
    try:
        import kornia  # type: ignore
    except ImportError:
        raise ImportError(
            "kornia is required for Smart Sharpen. Please install it in your ComfyUI environment: "
            "/mnt/data/AI/comfy_env/bin/python -m pip install kornia"
        )
    import cv2  # type: ignore

    p_edges = preserve_edges
    if p_edges > 0:
        p_edges = max(1 - p_edges, 0.05)

    output = []
    for img in s:
        if noise_radius > 1:
            sigma = 0.3 * ((noise_radius - 1) * 0.5 - 1) + 0.8
            img_np = img.cpu().numpy()
            blurred = cv2.bilateralFilter(img_np, noise_radius, p_edges, sigma)
            blurred = torch.from_numpy(blurred).to(device=img.device, dtype=img.dtype)
        else:
            blurred = img

        if sharpen_amount > 0:
            sharpened = kornia.enhance.sharpness(
                img.permute(2, 0, 1), sharpen_amount
            ).permute(1, 2, 0)
        else:
            sharpened = img

        sharpened_img = sharpen_ratio * sharpened + (1 - sharpen_ratio) * blurred
        sharpened_img = torch.clamp(sharpened_img, 0, 1)
        output.append(sharpened_img)

    return torch.stack(output)

def _stack_and_force_size(
    tensors_list: list, resampling: str = "lanczos"
) -> torch.Tensor:
    if not tensors_list:
        return torch.empty((0, 64, 64, 3))
    first_tensor = tensors_list[0]
    target_h, target_w = first_tensor.shape[1], first_tensor.shape[2]
    adjusted_list = []
    for t in tensors_list:
        if t.shape[1] != target_h or t.shape[2] != target_w:
            t_bchw = t.movedim(-1, 1)  # [1, C, H, W]
            t_resized = comfy.utils.common_upscale(
                t_bchw, target_w, target_h, resampling, "disabled"
            )
            t = t_resized.movedim(1, -1)  # [1, H, W, C]
        adjusted_list.append(t)
    return torch.cat(adjusted_list, dim=0)

_FILTER_LUT_CACHE: dict[str, torch.Tensor] = {}

def _filter_unwrap_value(value: Any, default: Any = None) -> Any:
    if isinstance(value, list):
        return _filter_unwrap_value(value[0], default) if value else default
    return value if value is not None else default

def _filter_was_input_batch(images: Any) -> bool:
    if isinstance(images, list) and len(images) == 1:
        images = images[0]
    return isinstance(images, torch.Tensor) and images.dim() == 4

def _filter_prepare_output(images: torch.Tensor, was_batch: bool) -> list[torch.Tensor]:
    if was_batch:
        return [images]
    return [images[index:index + 1] for index in range(images.shape[0])]

def parse_cube(file_path):
    size = None
    rgb_list = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "LUT_3D_SIZE":
                size = int(parts[1])
            elif parts[0] in ("DOMAIN_MIN", "DOMAIN_MAX", "LUT_1D_SIZE", "TITLE"):
                continue
            elif len(parts) == 3:
                try:
                    rgb_list.append([float(x) for x in parts])
                except ValueError:
                    pass
    if size is None:
        raise ValueError(f"LUT_3D_SIZE not found in cube file: {file_path}")
    if len(rgb_list) != size**3:
        raise ValueError(
            f"Expected {size**3} data points in cube file, but got {len(rgb_list)}"
        )

    lut_tensor = torch.tensor(rgb_list, dtype=torch.float32)
    lut_tensor = lut_tensor.reshape(size, size, size, 3)
    lut_tensor = lut_tensor.permute(3, 0, 1, 2).unsqueeze(0)  # [1, 3, size, size, size]
    return lut_tensor

def load_lut_cached(lut_name):
    if lut_name in _FILTER_LUT_CACHE:
        return _FILTER_LUT_CACHE[lut_name]

    lut_path = folder_paths.get_full_path_or_raise("luts", lut_name)
    lut_tensor = parse_cube(lut_path)

    _FILTER_LUT_CACHE[lut_name] = lut_tensor
    return lut_tensor

def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    max_val, max_idx = torch.max(rgb, dim=-1)
    min_val, _ = torch.min(rgb, dim=-1)
    d = max_val - min_val

    eps = 1e-7
    d_safe = torch.where(
        d == 0.0, torch.tensor(eps, device=rgb.device, dtype=rgb.dtype), d
    )

    r_max = max_idx == 0
    g_max = max_idx == 1
    b_max = max_idx == 2

    h = torch.zeros_like(max_val)
    h[r_max] = (((g[r_max] - b[r_max]) / d_safe[r_max]) % 6) / 6.0
    h[g_max] = (((b[g_max] - r[g_max]) / d_safe[g_max]) + 2) / 6.0
    h[b_max] = (((r[b_max] - g[b_max]) / d_safe[b_max]) + 4) / 6.0

    s = torch.zeros_like(max_val)
    max_val_safe = torch.where(
        max_val == 0.0, torch.tensor(eps, device=rgb.device, dtype=rgb.dtype), max_val
    )
    s = d / max_val_safe

    v = max_val

    return torch.stack((h, s, v), dim=-1)

def hsv_to_rgb(hsv):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    c = v * s
    x = c * (1.0 - torch.abs((h * 6.0) % 2.0 - 1.0))
    m = v - c

    h_mod = (h * 6.0).to(torch.int32) % 6

    r = torch.zeros_like(h)
    g = torch.zeros_like(h)
    b = torch.zeros_like(h)

    cond = h_mod == 0
    r[cond], g[cond], b[cond] = c[cond], x[cond], 0.0

    cond = h_mod == 1
    r[cond], g[cond], b[cond] = x[cond], c[cond], 0.0

    cond = h_mod == 2
    r[cond], g[cond], b[cond] = 0.0, c[cond], x[cond]

    cond = h_mod == 3
    r[cond], g[cond], b[cond] = 0.0, x[cond], c[cond]

    cond = h_mod == 4
    r[cond], g[cond], b[cond] = x[cond], 0.0, c[cond]

    cond = h_mod == 5
    r[cond], g[cond], b[cond] = c[cond], 0.0, x[cond]

    rgb = torch.stack((r + m, g + m, b + m), dim=-1)
    return rgb

def adjust_hue(image, hue_shift):
    if hue_shift == 0.0:
        return image
    hsv = rgb_to_hsv(image)
    hsv[..., 0] = (hsv[..., 0] + (hue_shift / 360.0)) % 1.0
    return hsv_to_rgb(hsv).clamp(0.0, 1.0)

def adjust_temperature_and_tint(image, temperature, tint):
    if temperature == 0.0 and tint == 0.0:
        return image

    r = image[..., 0]
    g = image[..., 1]
    b = image[..., 2]

    if temperature != 0.0:
        if temperature > 0.0:
            r = r * (1.0 + temperature)
            g = g * (1.0 + temperature * 0.4)
        else:
            b = b * (1.0 - temperature)

    if tint != 0.0:
        if tint > 0.0:
            r = r * (1.0 + tint * 0.1)
            b = b * (1.0 + tint * 0.1)
        else:
            g = g * (1.0 - tint * 0.1)

    return torch.stack((r, g, b), dim=-1).clamp(0.0, 1.0)

def apply_vignette(image, intensity, center_x, center_y):
    if intensity <= 0.0:
        return image

    B, H, W, C = image.shape
    device = image.device
    dtype = image.dtype

    y = torch.linspace(0, 1, H, device=device, dtype=dtype)
    x = torch.linspace(0, 1, W, device=device, dtype=dtype)
    grid_y, grid_x = torch.meshgrid(y, x, indexing="ij")

    dist = torch.sqrt((grid_x - center_x) ** 2 + (grid_y - center_y) ** 2)
    max_dist = torch.sqrt(
        torch.tensor(
            max(center_x, 1.0 - center_x) ** 2 + max(center_y, 1.0 - center_y) ** 2,
            device=device,
            dtype=dtype,
        )
    )
    dist = dist / max_dist

    mask = 1.0 - intensity * (dist**2)
    mask = torch.clamp(mask, 0.0, 1.0).view(1, H, W, 1)

    return image * mask

def apply_film_grain(image, strength, size, saturation):
    if strength <= 0.0:
        return image

    B, H, W, C = image.shape
    device = image.device
    dtype = image.dtype

    if size > 1.0:
        noise_h = max(2, int(H / size))
        noise_w = max(2, int(W / size))
    else:
        noise_h, noise_w = H, W

    gray_noise = torch.randn(B, noise_h, noise_w, 1, device=device, dtype=dtype)

    if saturation > 0.0:
        color_noise = torch.randn(B, noise_h, noise_w, 3, device=device, dtype=dtype)
        noise = torch.lerp(gray_noise, color_noise, saturation)
    else:
        noise = gray_noise.expand(-1, -1, -1, 3)

    if size > 1.0:
        noise = noise.movedim(-1, 1)
        noise = torch.nn.functional.interpolate(
            noise, size=(H, W), mode="bilinear", align_corners=False
        )
        noise = noise.movedim(1, -1)

    lum = (image * torch.tensor([0.299, 0.587, 0.114], device=device, dtype=dtype)).sum(
        dim=-1, keepdim=True
    )
    grain_mask = 4.0 * lum * (1.0 - lum)

    grain = noise * strength * grain_mask
    return torch.clamp(image + grain, 0.0, 1.0)

def apply_solarize(image, threshold):
    if threshold <= 0.0:
        return image
    return torch.where(image < threshold, image, 1.0 - image)

def apply_chromatic_aberration(image, ca_amount):
    if ca_amount <= 0.0:
        return image

    B, H, W, C = image.shape
    device = image.device
    dtype = image.dtype

    img_bchw = image.movedim(-1, 1)

    y = torch.linspace(-1, 1, H, device=device, dtype=dtype)
    x = torch.linspace(-1, 1, W, device=device, dtype=dtype)
    grid_y, grid_x = torch.meshgrid(y, x, indexing="ij")
    grid = torch.stack((grid_x, grid_y), dim=-1).unsqueeze(0).expand(B, -1, -1, -1)

    shift = ca_amount * 0.02
    grid_r = grid * (1.0 - shift)
    out_r = torch.nn.functional.grid_sample(
        img_bchw[:, 0:1],
        grid_r,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )

    out_g = img_bchw[:, 1:2]

    grid_b = grid * (1.0 + shift)
    out_b = torch.nn.functional.grid_sample(
        img_bchw[:, 2:3],
        grid_b,
        mode="bilinear",
        padding_mode="border",
        align_corners=True,
    )

    out_img = torch.cat((out_r, out_g, out_b), dim=1).movedim(1, -1)
    return out_img

def apply_lut(image, lut_name, strength=1.0):
    if lut_name == "none" or not lut_name:
        return image

    lut_tensor = load_lut_cached(lut_name)
    B, H, W, C = image.shape
    device = image.device
    dtype = image.dtype

    lut = lut_tensor.to(device=device, dtype=dtype).expand(B, -1, -1, -1, -1)
    grid = image.clamp(0.0, 1.0) * 2.0 - 1.0
    grid = grid.unsqueeze(1)

    out = torch.nn.functional.grid_sample(
        lut, grid, mode="bilinear", padding_mode="border", align_corners=True
    )

    out = out.squeeze(2).permute(0, 2, 3, 1)

    if strength < 1.0:
        out = torch.lerp(image, out, strength)

    return out

_IMAGE_PREVIEW_OUTPUT_DIR = folder_paths.get_temp_directory()

_IMAGE_PREVIEW_PREFIX = "_temp_" + "".join(
    random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5)
)

_PREFIX_APPEND = "_imgcmp_" + "".join(
    random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5)
)

_COMPRESS_LEVEL = 1

def _flatten_comparer_images(images: Any) -> list[torch.Tensor]:
    """Flatten nested image inputs into single-image BHWC tensors."""
    flattened: list[torch.Tensor] = []

    def process(item: Any) -> None:
        if isinstance(item, (list, tuple)):
            for nested in item:
                process(nested)
        elif isinstance(item, torch.Tensor):
            if item.dim() == 4:
                flattened.extend(item[index:index + 1] for index in range(item.shape[0]))
            elif item.dim() == 3:
                flattened.append(item.unsqueeze(0))

    if images is not None:
        process(images)
    return flattened

def _normalize_to_tensor(image):
    # Coerce an image input to a 4-D [B, H, W, C] tensor.
    # Handles: None, Python list of tensors (from image-list connections), 3-D tensors.
    if image is None:
        return None
    if isinstance(image, (list, tuple)):
        if not image:
            return None
        parts = []
        for item in image:
            if isinstance(item, torch.Tensor):
                parts.append(item.unsqueeze(0) if item.dim() == 3 else item)
        return torch.cat(parts, dim=0) if parts else None
    if not isinstance(image, torch.Tensor):
        return None
    if image.dim() == 3:
        image = image.unsqueeze(0)
    return image

def _save_images_to_temp(image_list, side, metadata=None):
    # Save image tensor in list to temp folder and return metadata list for UI.
    results = []
    if not image_list:
        return results

    first_img = image_list[0]
    output_dir = folder_paths.get_temp_directory()
    filename_prefix = f"ReaperCompareSimple{side}" + _PREFIX_APPEND
    full_output_folder, filename, counter, subfolder, _ = (
        folder_paths.get_save_image_path(
            filename_prefix, output_dir, first_img.shape[2], first_img.shape[1]
        )
    )

    for batch_number, image in enumerate(image_list):
        if image.dim() == 4 and image.shape[0] == 1:
            image = image[0]
        i = 255.0 * image.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

        filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
        timestamp = int(time.time() * 1000) % 100000000
        file = f"{filename_with_batch_num}_{counter:05}_{timestamp}_.png"
        img.save(
            os.path.join(full_output_folder, file),
            pnginfo=metadata,
            compress_level=_COMPRESS_LEVEL,
        )

        results.append({"filename": file, "subfolder": subfolder, "type": "temp"})
        counter += 1

    return results

__all__ = [name for name in globals() if not name.startswith("__")]
