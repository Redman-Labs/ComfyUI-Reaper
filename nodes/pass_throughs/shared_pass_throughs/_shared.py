"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

"""ComfyUI V3 pass-through nodes for workflow routing and organization."""

from typing import Any

import comfy.model_management

from comfy_api.latest import io

class _PassThrough(io.ComfyNode):
    """Shared execution behavior for typed pass-through nodes."""

    @classmethod
    def execute(cls, **kwargs: Any) -> io.NodeOutput:
        return io.NodeOutput(next(iter(kwargs.values())))

def _matched_schema(
    *,
    node_id: str,
    display_name: str,
    socket_name: str,
    data_type: type,
) -> io.Schema:
    template = io.MatchType.Template(socket_name, [data_type])
    return io.Schema(
        node_id=node_id,
        display_name=display_name,
        category=CATEGORY,
        description=f"Passes {display_name.removesuffix(' Passer').lower()} data through unchanged.",
        search_aliases=[display_name, "pass through", "passthrough", "Reaper"],
        inputs=[
            io.MatchType.Input(
                socket_name,
                template=template,
                tooltip="Value to pass through unchanged.",
            )
        ],
        outputs=[
            io.MatchType.Output(
                template,
                id=socket_name,
                display_name=display_name.removesuffix(" Passer"),
                tooltip="The original input, returned unchanged.",
            )
        ],
    )

def _make_matched_passer(class_name: str, display_name: str, socket_name: str, data_type: type) -> type:
    def define_schema(cls) -> io.Schema:
        return _matched_schema(
            node_id=class_name,
            display_name=display_name,
            socket_name=socket_name,
            data_type=data_type,
        )

    return type(class_name, (_PassThrough,), {"define_schema": classmethod(define_schema)})

__all__ = [name for name in globals() if not name.startswith("__")]
