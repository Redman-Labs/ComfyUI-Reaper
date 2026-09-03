"""Node implementation: If / Elif / Else."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class IfElifElse(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        result_template = io.MatchType.Template("reaper_if_elif_else")
        condition_template = io.Autogrow.TemplatePrefix(
            io.Boolean.Input(
                "condition",
                lazy=True,
                tooltip=(
                    "Additional Boolean condition for this numbered Else If "
                    "branch. Conditions are evaluated from the lowest number "
                    "upward, and evaluation stops at the first true condition."
                ),
            ),
            prefix="Else_If_",
            min=0,
            max=20,
        )
        value_template = io.Autogrow.TemplatePrefix(
            io.MatchType.Input(
                "value",
                template=result_template,
                lazy=True,
                tooltip=(
                    "Value returned when the Else If condition with the same "
                    "number is the first condition that evaluates to true. "
                    "This input is evaluated lazily only when selected."
                ),
            ),
            prefix="Then_",
            min=0,
            max=20,
        )
        return io.Schema(
            node_id="ReaperIfElifElse",
            display_name=node_title('If / Elif / Else', branded=True),
            category=CATEGORY,
            description=(
                "Returns the first matching branch. Add equally numbered "
                "Condition and Value sockets for each elif branch."
            ),
            search_aliases=[
                "if elif else",
                "multiple conditions",
                "conditional",
                "Reaper",
            ],
            inputs=[
                io.Boolean.Input(
                    "condition",
                    display_name="If",
                    force_input=True,
                    tooltip=(
                        "Primary Boolean condition. When true, the Then input "
                        "is returned and all Else If and Else branches remain "
                        "unevaluated. This input requires a connection."
                    ),
                ),
                io.MatchType.Input(
                    "then",
                    template=result_template,
                    display_name="Then",
                    lazy=True,
                    tooltip=(
                        "Value returned when If is true. This input accepts "
                        "any ComfyUI data type and is evaluated lazily only "
                        "when the primary condition is selected."
                    ),
                ),
                io.Autogrow.Input(
                    "conditions",
                    template=condition_template,
                    display_name="Elif Conditions",
                    optional=True,
                    tooltip=(
                        "Numbered Else If conditions. Connecting the available "
                        "socket adds the next numbered condition."
                    ),
                ),
                io.Autogrow.Input(
                    "values",
                    template=value_template,
                    display_name="Elif Values",
                    optional=True,
                    tooltip=(
                        "Numbered Then values paired with the correspondingly "
                        "numbered Else If conditions."
                    ),
                ),
                io.MatchType.Input(
                    "otherwise",
                    template=result_template,
                    display_name="Else",
                    lazy=True,
                    optional=True,
                    tooltip=(
                        "Fallback value returned when If is false and no "
                        "numbered Else If condition is true. This input is "
                        "evaluated lazily only when no earlier branch matches."
                    ),
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

    @staticmethod
    def _indices(conditions: dict[str, Any]) -> list[int]:
        indices = []
        for name in conditions:
            if name.startswith("Else_If_"):
                try:
                    indices.append(int(name.removeprefix("Else_If_")))
                except ValueError:
                    continue
        return sorted(indices)

    @classmethod
    def check_lazy_status(
        cls,
        condition: bool,
        then: Any = None,
        conditions: dict[str, Any] | None = None,
        values: dict[str, Any] | None = None,
        otherwise: Any = MISSING,
    ) -> list[str]:
        if condition:
            return _needed(then, "then")

        conditions = conditions or {}
        values = values or {}
        for index in cls._indices(conditions):
            condition_name = f"Else_If_{index}"
            branch_condition, original_name = _dynamic_value(
                conditions[condition_name]
            )
            if branch_condition is None:
                return [original_name or condition_name]
            if branch_condition:
                value_name = f"Then_{index}"
                if value_name not in values:
                    return []
                return _needed(values[value_name], value_name)

        if otherwise is MISSING:
            return []
        return _needed(otherwise, "otherwise")

    @classmethod
    def execute(
        cls,
        condition: bool,
        then: Any,
        conditions: dict[str, Any] | None = None,
        values: dict[str, Any] | None = None,
        otherwise: Any = None,
    ) -> io.NodeOutput:
        if condition:
            return io.NodeOutput(then)

        conditions = conditions or {}
        values = values or {}
        for index in cls._indices(conditions):
            if conditions[f"Else_If_{index}"]:
                return io.NodeOutput(values.get(f"Then_{index}"))
        return io.NodeOutput(otherwise)

__all__ = ['IfElifElse']
