"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['utilities']
_CATEGORY = CATEGORY

from typing import Any

from comfy_api.latest import io

from comfy_execution.graph_utils import ExecutionBlocker

EXECUTION_ORDER = io.Custom("REAPER_EXECUTION_ORDER")

MISSING = object()

def _dynamic_value(value):
    """Unwrap a V3 dynamic input while retaining its original prompt key."""
    if isinstance(value, tuple) and len(value) == 2:
        return value
    return value, None

def _needed(value, fallback_name: str) -> list[str]:
    resolved, original_name = _dynamic_value(value)
    if resolved is None:
        return [original_name or fallback_name]
    return []

__all__ = [name for name in globals() if not name.startswith("__")]
