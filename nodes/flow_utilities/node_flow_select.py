"""Node implementation: Flow Select."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class FlowSelect(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperFlowSelect",
            display_name=node_title('Flow Select', branded=True),
            category=CATEGORY,
            description=(
                "Routes Value to either the True or False output and blocks "
                "the unselected output."
            ),
            search_aliases=["route flow", "boolean router", "Reaper"],
            inputs=[
                io.AnyType.Input("value"),
                io.Boolean.Input("select", default=True),
            ],
            outputs=[
                io.AnyType.Output(id="true", display_name="True"),
                io.AnyType.Output(id="false", display_name="False"),
            ],
        )

    @classmethod
    def execute(cls, value: Any, select: bool = True) -> io.NodeOutput:
        blocker = ExecutionBlocker(None)
        if select:
            return io.NodeOutput(value, blocker)
        return io.NodeOutput(blocker, value)

__all__ = ['FlowSelect']
