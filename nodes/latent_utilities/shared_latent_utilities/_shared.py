"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['latent_utilities']
_CATEGORY = CATEGORY

"""Latent processing tools for the Reaper ComfyUI extension."""

import copy

import torch

import torch.nn.functional as F

import comfy.latent_formats

import comfy.model_management

from comfy_api.latest import io

from ..._helpers._vae_utils_models import (
    LATENT_UPSCALE_MODELS,
    load_latent_upscale_model,
    load_wan_latent_projector,
)

LATENT_FORMATS = {
    name: value
    for name, value in vars(comfy.latent_formats).items()
    if isinstance(value, type)
    and issubclass(value, comfy.latent_formats.LatentFormat)
    and value is not comfy.latent_formats.LatentFormat
}

__all__ = [name for name in globals() if not name.startswith("__")]
