"""Node implementation: Switch / Case."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class SwitchCase(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        result_template = io.MatchType.Template("reaper_switch_case")
        cases_template = io.Autogrow.TemplatePrefix(
            io.MatchType.Input(
                "case",
                template=result_template,
                lazy=True,
                tooltip="A selectable case value.",
            ),
            prefix="case_",
            min=0,
            max=100,
        )
        return io.Schema(
            node_id="ReaperSwitchCase",
            display_name=node_title('Switch / Case', branded=True),
            category=CATEGORY,
            description=(
                "Returns the numbered case selected by Index, or Default when "
                "that case does not exist."
            ),
            search_aliases=["switch case", "select by index", "Reaper"],
            inputs=[
                io.Int.Input("index", default=0, min=0, step=1),
                io.Autogrow.Input(
                    "cases",
                    template=cases_template,
                    display_name="Cases",
                    lazy=True,
                ),
                io.MatchType.Input(
                    "default",
                    template=result_template,
                    display_name="Default",
                    lazy=True,
                    optional=True,
                ),
            ],
            outputs=[
                io.MatchType.Output(
                    template=result_template,
                    id="result",
                    display_name="Result",
                )
            ],
        )

    @classmethod
    def check_lazy_status(
        cls,
        index: int,
        cases: dict[str, Any] | None = None,
        default: Any = MISSING,
    ) -> list[str]:
        cases = cases or {}
        case_name = f"case_{index}"
        if case_name in cases:
            return _needed(cases[case_name], case_name)
        if default is MISSING:
            return []
        return _needed(default, "default")

    @classmethod
    def execute(
        cls,
        index: int,
        cases: dict[str, Any],
        default: Any = None,
    ) -> io.NodeOutput:
        return io.NodeOutput(cases.get(f"case_{index}", default))

__all__ = ['SwitchCase']
