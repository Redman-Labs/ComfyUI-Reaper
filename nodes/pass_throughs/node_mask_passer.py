"""Node implementation: Mask Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperMaskPasser = _make_matched_passer("ReaperMaskPasser", "Mask Passer", "mask", io.Mask)
ReaperMaskPasser.__module__ = __name__

__all__ = ['ReaperMaskPasser']
