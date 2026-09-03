"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['prompt_text_utilities']
_CATEGORY = CATEGORY

"""Prompt and text nodes for the Reaper ComfyUI extension."""

import json

import re

from typing import Any

from comfy_api.latest import io

_COMMENT_PATTERN = re.compile(
    r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
    re.DOTALL | re.MULTILINE,
)

def remove_comments(text: str) -> str:
    """Remove // and /* */ comments while preserving quoted string content."""

    def replace_match(match: re.Match[str]) -> str:
        value = match.group(0)
        return "" if value.startswith("/") else value

    return _COMMENT_PATTERN.sub(replace_match, text)

__all__ = [name for name in globals() if not name.startswith("__")]
