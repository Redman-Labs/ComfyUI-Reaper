"""Node implementation: Audio Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

ReaperAudioPasser = _make_matched_passer("ReaperAudioPasser", "Audio Passer", "audio", io.Audio)
ReaperAudioPasser.__module__ = __name__

__all__ = ['ReaperAudioPasser']
