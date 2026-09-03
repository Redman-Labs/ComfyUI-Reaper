"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['mask_utilities']
_CATEGORY = CATEGORY

"""Mask nodes for the Reaper ComfyUI extension."""

import numpy as np

import torch

from comfy_api.latest import io

def _color_tensor(color: str, *, device, dtype) -> torch.Tensor:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    if len(value) == 8:
        value = value[:6]
    if len(value) != 6:
        raise ValueError(f"Expected a hex color such as #ffffff, received {color!r}")
    try:
        channels = [int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)]
    except ValueError as error:
        raise ValueError(f"Invalid hex color: {color!r}") from error
    return torch.tensor(channels, device=device, dtype=dtype)

__all__ = [name for name in globals() if not name.startswith("__")]
