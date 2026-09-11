"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['model_utilities']
_CATEGORY = CATEGORY

"""Tiled-model utilities for Reaper."""

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
