"""Node implementation: Image Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperImagePasser = _make_matched_passer("ReaperImagePasser", "Image Passer", "image", io.Image)
ReaperImagePasser.__module__ = __name__

__all__ = ['ReaperImagePasser']
