"""Node implementation: Conditioning Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperConditioningPasser = _make_matched_passer(
    "ReaperConditioningPasser", "Conditioning Passer", "conditioning", io.Conditioning
)
ReaperConditioningPasser.__module__ = __name__

__all__ = ['ReaperConditioningPasser']
