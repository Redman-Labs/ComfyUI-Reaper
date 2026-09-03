"""Node implementation: Any Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperAnySwitch(_TwoInputSwitch):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperAnySwitch",
            display_name=node_title('Any Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects one of two optional inputs of any ComfyUI data type. "
                "The two inputs may hold different types, and only the selected "
                "connected branch is evaluated before its value is passed through."
            ),
            search_aliases=[
                "Any Switch",
                "Any Switch RvTools",
                "universal switch",
                "select any input",
                "Reaper switch",
            ],
            inputs=_typed_inputs(io.AnyType, "Value"),
            outputs=_typed_output(io.AnyType, "Value"),
        )

__all__ = ['ReaperAnySwitch']
