"""Node implementation: Boolean Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

class ReaperBooleanPasser(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperBooleanPasser",
            display_name=node_title('Boolean Passer', branded=False),
            category=CATEGORY,
            description="Passes a boolean through, or returns false when no input is connected.",
            inputs=[io.Boolean.Input("input", optional=True, force_input=True)],
            outputs=[io.Boolean.Output(id="output")],
        )

    @classmethod
    def execute(cls, input: bool | None = None) -> io.NodeOutput:
        return io.NodeOutput(input if input is not None else False)

__all__ = ['ReaperBooleanPasser']
