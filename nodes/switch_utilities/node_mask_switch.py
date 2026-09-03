"""Node implementation: Mask Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperMaskSwitch(_TwoInputSwitch):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperMaskSwitch",
            display_name=node_title('Mask Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects Mask 1 or Mask 2 and passes only the selected mask "
                "tensor to the output using lazy branch evaluation."
            ),
            search_aliases=[
                "Mask Switch",
                "Mask Switch RvTools",
                "choose mask",
                "select mask input",
            ],
            inputs=_typed_inputs(io.Mask, "Mask"),
            outputs=_typed_output(io.Mask, "Mask"),
        )

__all__ = ['ReaperMaskSwitch']
