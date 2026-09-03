"""Neural latent super-resolution powered by the SesquiLSR models."""
from __future__ import annotations

import copy
from pathlib import Path

import torch
import torch.nn.functional as F
from safetensors.torch import load_file

import comfy.model_management
from comfy_api.latest import io

from ..global_configs import CATEGORIES, node_title
from .shared_latent_utilities import (
    LatentFormatAdaptor,
    LatentUpscaler,
    make_flux,
    make_flux2,
    make_ideogram4,
    make_identity,
    make_sdxl,
)

CATEGORY = CATEGORIES["latent_utilities"]

_MODEL_DIRECTORY = Path(__file__).resolve().parents[2] / "models" / "sesqui_lsr"
_FORMAT_CONFIG = {
    "SDXL": ("upscaler_SDXL.safetensors", 4, make_sdxl),
    "Flux": ("upscaler_Flux.safetensors", 16, make_flux),
    "Flux2": ("upscaler_Flux2.safetensors", 32, make_flux2),
    "Ideogram 4": ("upscaler_Flux2.safetensors", 32, make_ideogram4),
    "Wan 2.1": ("upscaler_Wan21.safetensors", 16, lambda: make_identity(16)),
}

_active_key: tuple[str, torch.dtype] | None = None
_active_model: LatentUpscaler | None = None
_adaptor_cache: dict[str, LatentFormatAdaptor] = {}


def _resolve_dtype(half_precision: bool, device: torch.device) -> torch.dtype:
    if not half_precision or device.type != "cuda":
        return torch.float32
    return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16


def _flatten_to_4d(
    samples: torch.Tensor, expected_channels: int
) -> tuple[torch.Tensor, tuple]:
    if samples.ndim == 4:
        if samples.shape[1] != expected_channels:
            raise ValueError(
                f"expected {expected_channels} channels, received {samples.shape[1]}"
            )
        return samples, ("image",)
    if samples.ndim != 5:
        raise ValueError(
            f"expected a 4D image latent or 5D video latent, received {samples.ndim}D"
        )
    if samples.shape[1] == expected_channels:
        batch, channels, frames, height, width = samples.shape
        flattened = samples.permute(0, 2, 1, 3, 4).reshape(
            batch * frames, channels, height, width
        )
        return flattened, ("bcthw", batch, channels, frames)
    if samples.shape[2] == expected_channels:
        batch, frames, channels, height, width = samples.shape
        return samples.reshape(batch * frames, channels, height, width), (
            "btchw",
            batch,
            frames,
            channels,
        )
    raise ValueError(
        f"could not find the expected {expected_channels}-channel axis in "
        f"latent shape {tuple(samples.shape)}"
    )


def _restore_layout(samples: torch.Tensor, layout: tuple) -> torch.Tensor:
    if layout[0] == "image":
        return samples
    if layout[0] == "bcthw":
        _, batch, channels, frames = layout
        return samples.reshape(batch, frames, channels, *samples.shape[-2:]).permute(
            0, 2, 1, 3, 4
        )
    _, batch, frames, channels = layout
    return samples.reshape(batch, frames, channels, *samples.shape[-2:])


def _resize_noise_mask(mask: torch.Tensor, target_size: tuple[int, int]) -> torch.Tensor:
    if mask.shape[-2:] == target_size:
        return mask
    original_device, original_dtype = mask.device, mask.dtype
    flat_mask = mask.reshape(-1, 1, *mask.shape[-2:]).float()
    resized = F.interpolate(flat_mask, size=target_size, mode="nearest")
    return resized.reshape(*mask.shape[:-2], *target_size).to(
        device=original_device, dtype=original_dtype
    )


def _load_upscaler(
    model_format: str, dtype: torch.dtype
) -> tuple[LatentUpscaler, LatentFormatAdaptor]:
    global _active_key, _active_model

    key = (model_format, dtype)
    if _active_key != key or _active_model is None:
        filename, channels, adaptor_factory = _FORMAT_CONFIG[model_format]
        model_path = _MODEL_DIRECTORY / filename
        if not model_path.is_file():
            raise FileNotFoundError(f"bundled model is missing: {model_path}")
        model = LatentUpscaler(in_channels=channels)
        model.load_state_dict(load_file(str(model_path)))
        _active_model = model.to(dtype=dtype).eval().requires_grad_(False)
        _active_key = key
        _adaptor_cache.setdefault(model_format, adaptor_factory())
    return _active_model, _adaptor_cache[model_format]


class ReaperLatentUpscaleByModel(io.ComfyNode):
    """Upscale image or video latents with a compact neural model."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLatentUpscaleByModel",
            display_name=node_title("Latent Upscale by Model", branded=False),
            category=CATEGORY,
            description=(
                "Upscales image or video LATENT samples with a compact SesquiLSR "
                "neural super-resolution model. Choose the format that matches the "
                "latent producer, then select any spatial scale from 1x to 2x. The "
                "node preserves the LATENT dictionary and resizes its noise mask, if "
                "present. SDXL mode is not compatible with SD 1.5 latents."
            ),
            search_aliases=[
                "SesquiLSR",
                "latent super resolution",
                "upscale latent model",
                "neural latent upscale",
            ],
            inputs=[
                io.Latent.Input(
                    "latent",
                    display_name="Latent",
                    tooltip=(
                        "LATENT data to enlarge. Supports 4D image samples and 5D "
                        "video samples; the channel layout must match Model Format."
                    ),
                ),
                io.Combo.Input(
                    "model_format",
                    options=list(_FORMAT_CONFIG),
                    default="SDXL",
                    display_name="Model Format",
                    tooltip=(
                        "Select the latent family: SDXL for 4-channel SDXL; Flux for "
                        "Flux, Z-Image Turbo, or Lumina; Flux2 for BN-packed Flux2; "
                        "Ideogram 4 for shift/scale-packed Flux2 latents; Wan 2.1 for "
                        "Wan 2.x, Krea 2, Anima, or Qwen Image."
                    ),
                ),
                io.Float.Input(
                    "scale",
                    default=1.5,
                    min=1.0,
                    max=2.0,
                    step=0.05,
                    display_name="Scale",
                    tooltip=(
                        "Spatial enlargement multiplier. 1.0 keeps the current latent "
                        "dimensions; 2.0 doubles latent width and height."
                    ),
                ),
                io.Boolean.Input(
                    "half_precision",
                    default=True,
                    display_name="Half Precision",
                    tooltip=(
                        "Use BF16 when supported, otherwise FP16, for model inference "
                        "on CUDA to reduce memory use. CPU inference remains FP32."
                    ),
                ),
            ],
            outputs=[
                io.Latent.Output(
                    id="latent",
                    display_name="Upscaled Latent",
                    tooltip=(
                        "A copied LATENT dictionary with neurally upscaled samples and "
                        "a matching resized noise mask when the input contained one."
                    ),
                )
            ],
        )

    @classmethod
    def execute(
        cls,
        latent: dict[str, torch.Tensor],
        model_format: str,
        scale: float,
        half_precision: bool,
    ) -> io.NodeOutput:
        if model_format not in _FORMAT_CONFIG:
            raise ValueError(f"unknown model format: {model_format}")
        if "samples" not in latent:
            raise ValueError("the LATENT input does not contain a samples tensor")

        samples = latent["samples"]
        device = comfy.model_management.get_torch_device()
        dtype = _resolve_dtype(half_precision, device)
        model, adaptor = _load_upscaler(model_format, dtype)
        samples_4d, layout = _flatten_to_4d(samples, adaptor.external_channels)
        target_size = tuple(round(size * scale) for size in samples.shape[-2:])

        try:
            model.to(device=device)
            external = samples_4d.to(device=device, dtype=torch.float32)
            internal = adaptor.to_vae_latent(external)
            internal_target = adaptor.vae_target_size(target_size)
            with torch.inference_mode():
                upscaled = model(internal.to(dtype=dtype), internal_target)
            restored = adaptor.from_vae_latent(upscaled.float())
            restored = restored.to(device=samples.device, dtype=samples.dtype)
            restored = _restore_layout(restored, layout)
        except Exception as error:
            raise ValueError(
                f"Latent Upscale by Model ({model_format}) failed: {error}"
            ) from error
        finally:
            model.to(comfy.model_management.unet_offload_device())

        result = copy.copy(latent)
        result["samples"] = restored
        if "noise_mask" in result:
            result["noise_mask"] = _resize_noise_mask(
                result["noise_mask"], restored.shape[-2:]
            )
        return io.NodeOutput(result)


__all__ = ["ReaperLatentUpscaleByModel"]
