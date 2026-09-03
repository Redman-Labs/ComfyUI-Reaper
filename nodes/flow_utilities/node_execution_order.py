"""Node implementation: Execution Order."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class ExecutionOrder(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperExecutionOrder",
            display_name=node_title('Execution Order', branded=True),
            category=CATEGORY,
            description=(
                "Chain the Order sockets to create an explicit dependency and "
                "optionally pass another node output through unchanged."
            ),
            search_aliases=["force execution order", "sequence", "Reaper"],
            inputs=[
                EXECUTION_ORDER.Input(
                    "order",
                    display_name="Order",
                    optional=True,
                ),
                io.AnyType.Input(
                    "value",
                    display_name="Any Node Output",
                    optional=True,
                ),
            ],
            outputs=[
                EXECUTION_ORDER.Output(id="order", display_name="Order"),
                io.AnyType.Output(id="value", display_name="Passthrough"),
            ],
        )

    @classmethod
    def execute(cls, order: Any = None, value: Any = None) -> io.NodeOutput:
        return io.NodeOutput(None, value)

__all__ = ['ExecutionOrder']
