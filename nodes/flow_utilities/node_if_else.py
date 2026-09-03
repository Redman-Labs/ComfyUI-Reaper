"""Node implementation: If / Else."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class IfElse(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("reaper_if_else")
        return io.Schema(
            node_id="ReaperIfElse",
            display_name=node_title('If / Else', branded=True),
            category=CATEGORY,
            description=(
                "Evaluates only the selected lazy branch and returns its value."
            ),
            search_aliases=["if else", "conditional", "branch", "Reaper"],
            inputs=[
                io.Boolean.Input(
                    "condition",
                    default=True,
                    tooltip="True selects If True; false selects If False.",
                ),
                io.MatchType.Input(
                    "if_true",
                    template=template,
                    display_name="If True",
                    lazy=True,
                ),
                io.MatchType.Input(
                    "if_false",
                    template=template,
                    display_name="If False",
                    lazy=True,
                ),
            ],
            outputs=[
                io.MatchType.Output(
                    template=template,
                    id="result",
                    display_name="Result",
                )
            ],
        )

    @classmethod
    def check_lazy_status(
        cls,
        condition: bool,
        if_true: Any = None,
        if_false: Any = None,
    ) -> list[str]:
        return _needed(if_true, "if_true") if condition else _needed(
            if_false, "if_false"
        )

    @classmethod
    def execute(cls, condition: bool, if_true: Any, if_false: Any) -> io.NodeOutput:
        return io.NodeOutput(if_true if condition else if_false)

__all__ = ['IfElse']
