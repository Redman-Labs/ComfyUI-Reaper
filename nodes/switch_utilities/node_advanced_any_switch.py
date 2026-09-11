"""Dynamic, lazy any-type switch adapted from Switch Pixaroma."""
from __future__ import annotations

from typing import Any

from comfy_api.latest import io

from ..global_configs import CATEGORIES, node_title


MAX_INPUTS = 32


def _active_index(value: Any) -> int:
    try:
        index = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 1
    return index if 1 <= index <= MAX_INPUTS else 1


class ReaperAdvancedAnySwitch(io.ComfyNode):
    """Route one of up to 32 arbitrary lazy inputs to a single output."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        inputs: list[io.Input] = [
            io.String.Input(
                "SwitchState",
                default="1",
                optional=True,
                tooltip="Internal one-based index of the active input row.",
            )
        ]
        inputs.extend(
            io.AnyType.Input(
                f"input_{index}",
                display_name=f"Input {index}",
                optional=True,
                lazy=True,
                tooltip="Any value can be connected. Only the selected row is evaluated.",
            )
            for index in range(1, MAX_INPUTS + 1)
        )
        return io.Schema(
            node_id="ReaperAdvancedAnySwitch",
            display_name=node_title("Any Switch Advanced"),
            category=CATEGORIES["switch_utilities"],
            description=(
                "A dynamic any-type switch adapted from Switch Pixaroma. Connect up to "
                "32 inputs and select the active row; only that lazy branch is evaluated "
                "and its value is passed through unchanged."
            ),
            search_aliases=["Switch Pixaroma", "advanced any switch", "dynamic switch"],
            inputs=inputs,
            outputs=[io.AnyType.Output(id="output", display_name="Output")],
        )

    @classmethod
    def check_lazy_status(cls, SwitchState: str = "1", **kwargs: Any) -> list[str]:
        key = f"input_{_active_index(SwitchState)}"
        return [key] if key in kwargs and kwargs[key] is None else []

    @classmethod
    def execute(cls, SwitchState: str = "1", **kwargs: Any) -> io.NodeOutput:
        index = _active_index(SwitchState)
        value = kwargs.get(f"input_{index}")
        if value is None:
            raise ValueError(
                "Any Switch Advanced: no input is connected to the selected row. "
                "Connect a value and select that input before running the workflow."
            )
        return io.NodeOutput(value)


__all__ = ["ReaperAdvancedAnySwitch"]
