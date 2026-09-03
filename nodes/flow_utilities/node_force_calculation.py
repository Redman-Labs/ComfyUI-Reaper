"""Node implementation: Force Calculation."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_flow_utilities._shared import *

CATEGORY = CATEGORIES['flow_utilities']
_CATEGORY = CATEGORY

class ForceCalculation(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperForceCalculation",
            display_name=node_title('Force Calculation', branded=True),
            category=CATEGORY,
            description=(
                "Passes Value through while forcing this dependency path to "
                "recalculate on every queued run."
            ),
            search_aliases=["disable cache", "always execute", "Reaper"],
            is_output_node=True,
            not_idempotent=True,
            inputs=[io.AnyType.Input("value")],
            outputs=[io.AnyType.Output(id="value", display_name="Value")],
        )

    @classmethod
    def fingerprint_inputs(cls, value: Any) -> float:
        return float("nan")

    @classmethod
    def execute(cls, value: Any) -> io.NodeOutput:
        return io.NodeOutput(value)

__all__ = ['ForceCalculation']
