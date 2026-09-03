"""Node implementation: ControlNet Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperControlNetPasser = _make_matched_passer(
    "ReaperControlNetPasser", "ControlNet Passer", "control_net", io.ControlNet
)
ReaperControlNetPasser.__module__ = __name__

__all__ = ['ReaperControlNetPasser']
