"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['model_utilities']
_CATEGORY = CATEGORY

"""Model enhancement and tiled-model utilities for Reaper."""

import math

from typing import Any

import torch

import comfy.patcher_extension

from comfy_api.latest import io

import copy

import torch.nn.functional as F

import comfy.latent_formats

import comfy.model_management

import comfy.utils

from nodes import VAELoader

from ..._helpers._vae_utils_models import (
    LATENT_UPSCALE_MODELS,
    load_latent_upscale_model,
    load_wan_latent_projector,
)

BASIC_WRAPPER_KEY = "reaper_krea2t_prompt_adherence_enhancer"

BASIC_CONFIG_KEY = "reaper_krea2t_prompt_adherence_enhancer"

BASIC_ORIGINAL_ATTR = "_reaper_krea2t_original_forward"

ADVANCED_WRAPPER_KEY = "reaper_krea2t_prompt_adherence_enhancer_advanced"

ADVANCED_CONFIG_KEY = "reaper_krea2t_prompt_adherence_enhancer_advanced"

ADVANCED_ORIGINAL_ATTR = "_reaper_krea2t_advanced_original_forward"

KREA2_TAP_LAYERS = (2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35)

KREA2_TAP_DIM = 2560

KREA2_CHUNK_COUNT = 24

KREA2_CHUNK_DIM = 1280

ENHANCER_PROFILE_12 = (
    1.0,
    1.0,
    1.0,
    1.0,
    1.0,
    1.0,
    1.0,
    2.5,
    5.0,
    1.1,
    4.0,
    1.0,
)

ENHANCER_CHUNK_PROFILE = ENHANCER_PROFILE_12 + ENHANCER_PROFILE_12

ENHANCER_GLOBAL_MULTIPLIER = 15.0

TXTFUSION_TOKEN_REL_CAP = 0.75

_MISSING = object()

def _is_krea2_dm(dm: Any) -> bool:
    return (
        hasattr(dm, "txtfusion")
        and hasattr(dm, "txtmlp")
        and hasattr(dm, "blocks")
        and hasattr(dm, "_unpack_context")
        and int(getattr(dm, "txtlayers", 0)) == len(KREA2_TAP_LAYERS)
        and int(getattr(dm, "txtdim", 0)) == KREA2_TAP_DIM
    )

def _bounded_float(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        result = default
    if not math.isfinite(result):
        result = default
    return max(lo, min(hi, result))

def _step_progress(transformer_options: dict[str, Any]) -> tuple[float, float]:
    sigma = transformer_options.get("sigmas")
    sigma_value = 0.0
    if torch.is_tensor(sigma) and sigma.numel() > 0:
        sigma_value = float(sigma.detach().flatten()[0].float().item())
    elif isinstance(sigma, (int, float)):
        sigma_value = float(sigma)

    sample_sigmas = transformer_options.get("sample_sigmas")
    if torch.is_tensor(sample_sigmas) and sample_sigmas.numel() > 1:
        values = sample_sigmas.detach().float().flatten()
        index = int(torch.argmin((values - sigma_value).abs()).item())
        progress = index / max(1, int(values.numel()) - 1)
        return float(progress), sigma_value
    return 0.0, sigma_value

def _rms_scalar(value: torch.Tensor) -> float:
    as_float = value.detach().float()
    return float(torch.sqrt(torch.mean(as_float * as_float)).item())

def _cosine_scalar(first: torch.Tensor, second: torch.Tensor) -> float:
    first_flat = first.detach().float().flatten()
    second_flat = second.detach().float().flatten()
    denominator = torch.linalg.vector_norm(first_flat).clamp_min(
        1e-8
    ) * torch.linalg.vector_norm(second_flat).clamp_min(1e-8)
    return float(torch.dot(first_flat, second_flat).div(denominator).item())

def _chunk_gains(
    device: torch.device,
    dtype: torch.dtype,
    strength: float,
) -> torch.Tensor:
    base = torch.tensor(
        ENHANCER_CHUNK_PROFILE,
        device=device,
        dtype=torch.float32,
    )
    gains = 1.0 + float(strength) * (base - 1.0)
    return gains.to(dtype=dtype)

def _run_refiners(txtfusion, y_text, mask=None, transformer_options=None):
    output = y_text
    for block in txtfusion.refiner_blocks:
        output = block(
            output,
            mask=mask,
            transformer_options=transformer_options or {},
        )
    return output

def _run_txtfusion_parts(txtfusion, value, mask=None, transformer_options=None):
    transformer_options = transformer_options or {}
    batch, sequence, taps, dimension = value.shape
    output = value.reshape(batch * sequence, taps, dimension)
    for block in txtfusion.layerwise_blocks:
        output = block(
            output.contiguous(),
            mask=None,
            transformer_options=transformer_options,
        )
    tap_mix = (
        output.reshape(batch, sequence, taps, dimension)
        .permute(0, 1, 3, 2)
        .contiguous()
    )
    projected = txtfusion.projector(tap_mix).squeeze(-1)
    output = _run_refiners(
        txtfusion,
        projected,
        mask=mask,
        transformer_options=transformer_options,
    )
    return output, projected

def _enhanced_txtfusion_forward(
    txtfusion,
    value,
    mask=None,
    transformer_options=None,
    strength=1.0,
    collect_debug=False,
    original_attribute=BASIC_ORIGINAL_ATTR,
):
    transformer_options = transformer_options or {}
    batch, sequence, taps, dimension = value.shape
    if taps != len(KREA2_TAP_LAYERS) or dimension != KREA2_TAP_DIM:
        original_forward = getattr(txtfusion, original_attribute)
        output = original_forward(
            value,
            mask=mask,
            transformer_options=transformer_options,
        )
        return output, None

    reference_output, reference_projected = _run_txtfusion_parts(
        txtfusion,
        value,
        mask=mask,
        transformer_options=transformer_options,
    )

    if strength != 0.0:
        gains = _chunk_gains(value.device, value.dtype, strength)
        global_multiplier = 1.0 + float(strength) * (
            ENHANCER_GLOBAL_MULTIPLIER - 1.0
        )
        scaled_value = (
            value.reshape(
                batch,
                sequence,
                KREA2_CHUNK_COUNT,
                KREA2_CHUNK_DIM,
            )
            * gains.view(1, 1, KREA2_CHUNK_COUNT, 1)
            * global_multiplier
        ).reshape_as(value)
        candidate_output, candidate_projected = _run_txtfusion_parts(
            txtfusion,
            scaled_value,
            mask=mask,
            transformer_options=transformer_options,
        )
    else:
        global_multiplier = 1.0
        scaled_value = value
        candidate_output = reference_output
        candidate_projected = reference_projected

    post_delta = (
        candidate_output.detach().float() - reference_output.detach().float()
    )
    token_base_rms = torch.sqrt(
        torch.mean(reference_output.detach().float() ** 2, dim=-1, keepdim=True)
    ).clamp_min(1e-8)
    token_delta_rms = torch.sqrt(
        torch.mean(post_delta**2, dim=-1, keepdim=True)
    ).clamp_min(1e-8)
    token_relative = token_delta_rms / token_base_rms
    token_scale = (TXTFUSION_TOKEN_REL_CAP / token_relative).clamp(max=1.0)
    output = (
        reference_output.detach().float() + post_delta * token_scale
    ).to(candidate_output.dtype)

    debug = None
    if collect_debug:
        reference_rms = _rms_scalar(reference_projected)
        candidate_rms = _rms_scalar(candidate_projected)
        output_delta = output.detach().float() - reference_output.detach().float()
        output_base_rms = _rms_scalar(reference_output)
        debug = {
            "shape": "x".join(str(int(item)) for item in output.shape),
            "global_multiplier": float(global_multiplier),
            "projector_rms_ratio": float(
                candidate_rms / max(reference_rms, 1e-8)
            ),
            "output_rel_delta": float(
                _rms_scalar(output_delta) / max(output_base_rms, 1e-8)
            ),
            "output_cosine": _cosine_scalar(reference_output, output),
            "clamp_mean": float(token_scale.mean().item()),
            "token_raw_rel_mean": float(token_relative.mean().item()),
            "input_tap_rms": [
                float(item)
                for item in torch.sqrt(
                    torch.mean(value.detach().float() ** 2, dim=(0, 1, 3))
                )
                .detach()
                .cpu()
                .tolist()
            ],
            "scaled_tap_rms": [
                float(item)
                for item in torch.sqrt(
                    torch.mean(scaled_value.detach().float() ** 2, dim=(0, 1, 3))
                )
                .detach()
                .cpu()
                .tolist()
            ],
        }
    return output, debug

def _transformer_options(args, kwargs) -> dict[str, Any]:
    options = kwargs.get("transformer_options")
    if options is None:
        options = next((item for item in args if isinstance(item, dict)), {})
    return options

def _remove_existing_wrapper(patched, wrapper_key: str) -> None:
    wrapper_type = comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL
    if hasattr(patched, "remove_wrappers_with_key"):
        patched.remove_wrappers_with_key(wrapper_type, wrapper_key)
    transformer_options = patched.model_options.setdefault(
        "transformer_options", {}
    )
    wrappers = transformer_options.get("wrappers", {})
    diffusion_wrappers = wrappers.get(wrapper_type, {})
    diffusion_wrappers.pop(wrapper_key, None)

def _install_wrapper(patched, wrapper_key: str, wrapper) -> None:
    _remove_existing_wrapper(patched, wrapper_key)
    patched.add_wrapper_with_key(
        comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL,
        wrapper_key,
        wrapper,
    )

def krea2t_enhancer_wrapper(executor, *args, **kwargs):
    transformer_options = _transformer_options(args, kwargs)
    config = transformer_options.get(BASIC_CONFIG_KEY, {})
    if not config or not config.get("enabled", True):
        return executor(*args, **kwargs)
    if config.get("_active", False):
        return executor(*args, **kwargs)

    diffusion_model = executor.class_obj
    if not _is_krea2_dm(diffusion_model):
        if config.get("debug", False):
            print(
                "[ReaperKrea2TEnhancer] skipped: diffusion model does not "
                "match the Krea2 text-fusion layout"
            )
        return executor(*args, **kwargs)

    strength = _bounded_float(config.get("strength", 1.0), 1.0, 0.0, 2.0)
    if strength == 0.0:
        return executor(*args, **kwargs)

    txtfusion = diffusion_model.txtfusion
    if hasattr(txtfusion, BASIC_ORIGINAL_ATTR):
        txtfusion.forward = getattr(txtfusion, BASIC_ORIGINAL_ATTR)
        delattr(txtfusion, BASIC_ORIGINAL_ATTR)
    original_forward = txtfusion.forward
    previous_active = config.get("_active", _MISSING)
    progress, sigma = _step_progress(transformer_options)
    debug_enabled = bool(config.get("debug", False))

    def enhanced_forward(value, mask=None, transformer_options=None):
        setattr(txtfusion, BASIC_ORIGINAL_ATTR, original_forward)
        try:
            output, debug = _enhanced_txtfusion_forward(
                txtfusion,
                value,
                mask=mask,
                transformer_options=transformer_options or {},
                strength=strength,
                collect_debug=debug_enabled,
                original_attribute=BASIC_ORIGINAL_ATTR,
            )
        finally:
            if hasattr(txtfusion, BASIC_ORIGINAL_ATTR):
                delattr(txtfusion, BASIC_ORIGINAL_ATTR)

        if debug is not None and int(config.setdefault("_debug_prints", 0)) < int(
            config.get("max_debug_prints", 8)
        ):
            config["_debug_prints"] = int(config.get("_debug_prints", 0)) + 1
            print(
                "[ReaperKrea2TEnhancer] "
                f"strength={strength:.3f} progress={progress:.3f} "
                f"sigma={sigma:.6g} global={debug['global_multiplier']:.6g} "
                f"proj_ratio={debug['projector_rms_ratio']:.6g} "
                f"out_rel={debug['output_rel_delta']:.6g} "
                f"out_cos={debug['output_cosine']:.6g} "
                f"clamp={debug['clamp_mean']:.6g}"
            )
        return output

    try:
        config["_active"] = True
        txtfusion.forward = enhanced_forward
        return executor(*args, **kwargs)
    finally:
        txtfusion.forward = original_forward
        if previous_active is _MISSING:
            config.pop("_active", None)
        else:
            config["_active"] = previous_active

def _install_txtmlp_scale(txtmlp_module, scale: float):
    if scale == 1.0:
        return None, None
    original_forward = txtmlp_module.forward

    def scaled_forward(value):
        return original_forward(value) * float(scale)

    txtmlp_module.forward = scaled_forward
    return txtmlp_module, original_forward

def krea2t_enhancer_advanced_wrapper(executor, *args, **kwargs):
    transformer_options = _transformer_options(args, kwargs)
    config = transformer_options.get(ADVANCED_CONFIG_KEY, {})
    if not config or not config.get("enabled", True):
        return executor(*args, **kwargs)
    if config.get("_active", False):
        return executor(*args, **kwargs)

    diffusion_model = executor.class_obj
    if not _is_krea2_dm(diffusion_model):
        if config.get("debug", False):
            print(
                "[ReaperKrea2TEnhancerAdvanced] skipped: diffusion model "
                "does not match the Krea2 text-fusion layout"
            )
        return executor(*args, **kwargs)

    strength = _bounded_float(config.get("strength", 1.0), 1.0, 0.0, 2.0)
    text_scale = _bounded_float(
        config.get("text_scale", 1.0), 1.0, 0.25, 4.0
    )
    if strength == 0.0 and text_scale == 1.0:
        return executor(*args, **kwargs)

    txtfusion = diffusion_model.txtfusion
    if hasattr(txtfusion, ADVANCED_ORIGINAL_ATTR):
        txtfusion.forward = getattr(txtfusion, ADVANCED_ORIGINAL_ATTR)
        delattr(txtfusion, ADVANCED_ORIGINAL_ATTR)

    original_txtfusion_forward = txtfusion.forward
    txtmlp_module = None
    original_txtmlp_forward = None
    previous_active = config.get("_active", _MISSING)
    progress, sigma = _step_progress(transformer_options)
    debug_enabled = bool(config.get("debug", False))

    def enhanced_forward(value, mask=None, transformer_options=None):
        setattr(txtfusion, ADVANCED_ORIGINAL_ATTR, original_txtfusion_forward)
        try:
            output, debug = _enhanced_txtfusion_forward(
                txtfusion,
                value,
                mask=mask,
                transformer_options=transformer_options or {},
                strength=strength,
                collect_debug=debug_enabled,
                original_attribute=ADVANCED_ORIGINAL_ATTR,
            )
        finally:
            if hasattr(txtfusion, ADVANCED_ORIGINAL_ATTR):
                delattr(txtfusion, ADVANCED_ORIGINAL_ATTR)

        if debug is not None:
            print(
                "[ReaperKrea2TEnhancerAdvanced] "
                f"strength={strength:.3f} text_scale={text_scale:.3f} "
                f"progress={progress:.3f} sigma={sigma:.6g} "
                f"global={debug['global_multiplier']:.6g} "
                f"proj_ratio={debug['projector_rms_ratio']:.6g} "
                f"out_rel={debug['output_rel_delta']:.6g} "
                f"out_cos={debug['output_cosine']:.6g} "
                f"clamp={debug['clamp_mean']:.6g}"
            )
        return output

    try:
        config["_active"] = True
        txtmlp_module, original_txtmlp_forward = _install_txtmlp_scale(
            diffusion_model.txtmlp,
            text_scale,
        )
        if strength != 0.0:
            txtfusion.forward = enhanced_forward
        return executor(*args, **kwargs)
    finally:
        txtfusion.forward = original_txtfusion_forward
        if txtmlp_module is not None and original_txtmlp_forward is not None:
            txtmlp_module.forward = original_txtmlp_forward
        if previous_active is _MISSING:
            config.pop("_active", None)
        else:
            config["_active"] = previous_active

def _enhancer_inputs(include_text_scale: bool = False) -> list[io.Input]:
    inputs: list[io.Input] = [
        io.Model.Input(
            "model",
            display_name="model",
            tooltip=(
                "Krea2 diffusion MODEL to patch. Non-Krea2 models pass through "
                "safely without applying the text-fusion enhancement."
            ),
        ),
        io.Boolean.Input(
            "enabled",
            display_name="Enable Enhancer",
            default=True,
            label_on="True",
            label_off="False",
            tooltip=(
                "Enables or disables the runtime Krea2 text-fusion patch. The "
                "node still returns a cloned model when disabled."
            ),
        ),
        io.Float.Input(
            "strength",
            display_name="Enhancer Strength",
            default=1.0,
            min=0.0,
            max=2.0,
            step=0.05,
            tooltip=(
                "Enhancement blend strength. 0.0 is neutral, 1.0 is the "
                "original enhancer level, and 2.0 is the strongest setting."
            ),
        ),
    ]
    if include_text_scale:
        inputs.append(
            io.Float.Input(
                "text_scale",
                display_name="Text Strength",
                default=1.0,
                min=0.25,
                max=4.0,
                step=0.05,
                tooltip=(
                    "Multiplies fused text tokens directly after txtmlp and "
                    "before they enter Krea2's shared stream. 1.0 is neutral; "
                    "the source project suggests starting around 1.50 to 2.00."
                ),
            )
        )
    inputs.append(
        io.Boolean.Input(
            "debug",
            default=False,
            label_on="True",
            label_off="False",
            tooltip=(
                "Prints runtime Krea2 layout, strength, sampling-progress, "
                "and enhancement diagnostics to the ComfyUI console."
            ),
        )
    )
    return inputs

def _model_output() -> list[io.Output]:
    return [
        io.Model.Output(
            id="model",
            display_name="model",
            tooltip="Cloned MODEL carrying the selected Krea2 enhancement patch.",
        )
    ]

def get_tiles(length: int, tile_size: int, min_overlap: int) -> list[tuple[int, int]]:
    if length < 1 or tile_size < 1:
        raise ValueError("Length and Tile Size must both be at least 1.")
    if min_overlap < 0:
        raise ValueError("Minimum Overlap cannot be negative.")
    if length <= tile_size:
        return [(0, length)]
    if min_overlap >= tile_size:
        raise ValueError(
            "Minimum Overlap must be smaller than Tile Size when multiple tiles are needed."
        )

    maximum_step = tile_size - min_overlap
    total_shift = length - tile_size
    tile_count = math.ceil(total_shift / maximum_step) + 1
    base_step, remainder = divmod(total_shift, tile_count - 1)

    starts = [0]
    for index in range(tile_count - 1):
        starts.append(starts[-1] + base_step + (1 if index < remainder else 0))
    return [(start, start + tile_size) for start in starts]

def get_1d_mask(
    index: int,
    tiles: list[tuple[int, int]],
    drop_first: int = 0,
) -> torch.Tensor:
    tile_start, tile_end = tiles[index]
    mask = torch.ones(tile_end - tile_start)

    if index > 0:
        previous_end = tiles[index - 1][1]
        overlap = max(0, previous_end - tile_start)
        dropped = min(max(0, drop_first), overlap)
        ramp_size = overlap - dropped
        if dropped:
            mask[:dropped] = 0
        if ramp_size:
            ramp = (
                torch.arange(1, ramp_size + 1, dtype=mask.dtype) / ramp_size
            )
            mask[dropped:overlap] *= ramp

    if index < len(tiles) - 1:
        next_start = tiles[index + 1][0]
        overlap = max(0, tile_end - next_start)
        if overlap:
            ramp = torch.arange(
                overlap, 0, -1, dtype=mask.dtype
            ) / overlap
            mask[-overlap:] *= ramp
    return mask

__all__ = [name for name in globals() if not name.startswith("__")]
