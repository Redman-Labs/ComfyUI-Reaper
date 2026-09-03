"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['vae_utilities']
_CATEGORY = CATEGORY

"""VAE loading, offload, and decoding tools for Reaper."""

import copy

import math

from typing import Any

import torch

import torch.nn.functional as F

import comfy.model_management

import comfy.utils

from comfy_api.latest import io

from nodes import VAELoader

def _vae_names() -> list[str]:
    """Use ComfyUI's current loader list, including its built-in TAE entries."""
    try:
        return list(VAELoader.vae_list(VAELoader))
    except TypeError:
        return list(VAELoader.vae_list())

__all__ = [name for name in globals() if not name.startswith("__")]
