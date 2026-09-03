"""Node implementation: Clip Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperClipPasser = _make_matched_passer("ReaperClipPasser", "Clip Passer", "clip", io.Clip)
ReaperClipPasser.__module__ = __name__

__all__ = ['ReaperClipPasser']
