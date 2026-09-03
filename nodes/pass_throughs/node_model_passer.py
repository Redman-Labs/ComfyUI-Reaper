"""Node implementation: Model Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperModelPasser = _make_matched_passer("ReaperModelPasser", "Model Passer", "model", io.Model)
ReaperModelPasser.__module__ = __name__

__all__ = ['ReaperModelPasser']
