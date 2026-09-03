"""Node implementation: Continue Flow."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class ContinueFlow(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperContinueFlow",
            display_name=node_title('Continue Flow', branded=True),
            category=CATEGORY,
            description=(
                "Passes Value through when Continue is enabled; otherwise "
                "blocks every downstream branch."
            ),
            search_aliases=["execution blocker", "stop flow", "Reaper"],
            inputs=[
                io.AnyType.Input("value"),
                io.Boolean.Input("continue_flow", default=True),
                io.String.Input(
                    "message",
                    default="",
                    multiline=True,
                    optional=True,
                    tooltip=(
                        "Optional execution error message. Leave blank to block "
                        "silently."
                    ),
                ),
            ],
            outputs=[io.AnyType.Output(id="value", display_name="Value")],
        )

    @classmethod
    def execute(
        cls,
        value: Any,
        continue_flow: bool = True,
        message: str = "",
    ) -> io.NodeOutput:
        if continue_flow:
            return io.NodeOutput(value)
        return io.NodeOutput(ExecutionBlocker(message or None))

__all__ = ['ContinueFlow']
