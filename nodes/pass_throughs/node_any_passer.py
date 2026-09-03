"""Node implementation: Any Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

class ReaperAnyPasser(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("input", [io.AnyType])
        return io.Schema(
            node_id="ReaperAnyPasser",
            display_name=node_title('Any Passer', branded=False),
            category=CATEGORY,
            description="Passes a value of any ComfyUI datatype through unchanged.",
            search_aliases=["Any Passer", "universal pass through", "Reaper"],
            is_input_list=True,
            inputs=[io.MatchType.Input("input", template=template)],
            outputs=[io.MatchType.Output(template, id="output", is_output_list=True)],
        )

    @classmethod
    def execute(cls, input: Any) -> io.NodeOutput:
        if input is None or not input or all(item is None for item in input):
            return io.NodeOutput([None])
        return io.NodeOutput(input)

__all__ = ['ReaperAnyPasser']
