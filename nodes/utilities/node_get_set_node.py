"""Node implementations: SetNode, GetNode."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_utilities._shared import *

CATEGORY = CATEGORIES['utilities']
_CATEGORY = CATEGORY

class ReaperSetNode(io.ComfyNode):
    """Metadata definition for the frontend-only Reaper Set node."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperSetNode",
            display_name=node_title('SetNode', branded=True),
            category=CATEGORY,
            description=(
                "Stores any connection under a name for one or more Get "
                "Reaper nodes. This is a virtual editor node, so its "
                "passthrough resolves directly to the original source."
            ),
            search_aliases=[
                "set variable",
                "wireless connection",
                "named value",
                "Reaper",
            ],
            inputs=[
                io.String.Input(
                    "name",
                    default="",
                    tooltip=(
                        "Unique name used by GetNode (Reaper) instances. "
                        "When Value is connected, an empty name is filled from "
                        "the connected output name and numbered if necessary. "
                        "You can edit the generated name at any time."
                    ),
                ),
                io.AnyType.Input(
                    "value",
                    optional=True,
                    tooltip=(
                        "Any ComfyUI value to store. The output passes this "
                        "same connection through without changing it."
                    ),
                ),
            ],
            outputs=[
                io.AnyType.Output(
                    id="value",
                    display_name="Value",
                    tooltip="The unchanged value connected to the input.",
                )
            ],
        )

    @classmethod
    def execute(cls, name: str = "", value: Any = None) -> io.NodeOutput:
        # The frontend marks this node virtual and resolves its source directly.
        # Returning the value keeps the schema safe if a third-party frontend
        # submits it as a normal backend node.
        return io.NodeOutput(value)

class ReaperGetNode(io.ComfyNode):
    """Metadata definition for the frontend-only Reaper Get node."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperGetNode",
            display_name=node_title('GetNode', branded=True),
            category=CATEGORY,
            description=(
                "Reads the value from a named SetNode (Reaper) without "
                "drawing a cable across the workflow. Sets in parent graphs "
                "are visible inside nested subgraphs."
            ),
            search_aliases=[
                "get variable",
                "wireless connection",
                "named value",
                "Reaper",
            ],
            outputs=[
                io.AnyType.Output(
                    id="value",
                    display_name="Value",
                    tooltip=(
                        "The value supplied to the selected SetNode (Reaper) "
                        "node, with its matching ComfyUI type."
                    ),
                )
            ],
        )

    @classmethod
    def execute(cls) -> io.NodeOutput:
        # Normal ComfyUI submission removes this virtual node before execution.
        return io.NodeOutput(None)

__all__ = ['ReaperSetNode', 'ReaperGetNode']
