"""Node implementation: Is Connected."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class IsConnected(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperIsConnected",
            display_name=node_title('Is Connected', branded=True),
            category=CATEGORY,
            description=(
                "Returns true when Input supplies a non-None value. ComfyUI "
                "does not distinguish an unconnected socket from a connected "
                "socket whose evaluated value is None."
            ),
            search_aliases=["input connected", "has value", "Reaper"],
            inputs=[io.AnyType.Input("input", optional=True)],
            outputs=[
                io.Boolean.Output(
                    id="is_connected",
                    display_name="Is Connected",
                )
            ],
        )

    @classmethod
    def execute(cls, input: Any = None) -> io.NodeOutput:
        return io.NodeOutput(input is not None)

__all__ = ['IsConnected']
