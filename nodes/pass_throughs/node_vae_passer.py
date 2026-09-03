"""Node implementation: VAE Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperVAEPasser = _make_matched_passer("ReaperVAEPasser", "VAE Passer", "vae", io.Vae)
ReaperVAEPasser.__module__ = __name__

__all__ = ['ReaperVAEPasser']
