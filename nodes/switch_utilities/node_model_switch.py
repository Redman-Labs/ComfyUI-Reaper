"""Node implementation: Model Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperModelSwitch(_TwoInputSwitch):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperModelSwitch",
            display_name=node_title('Model Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects Model 1 or Model 2 and passes only the selected "
                "diffusion model patcher to the output using lazy evaluation."
            ),
            search_aliases=[
                "Model Switch",
                "Model Switch RvTools",
                "choose model",
                "select diffusion model",
            ],
            inputs=_typed_inputs(io.Model, "Model"),
            outputs=_typed_output(io.Model, "Model"),
        )

__all__ = ['ReaperModelSwitch']
