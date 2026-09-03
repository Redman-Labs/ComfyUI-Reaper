"""Node implementation: CLIP Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperClipSwitch(_TwoInputSwitch):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperClipSwitch",
            display_name=node_title('CLIP Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects CLIP 1 or CLIP 2 and passes only the selected text "
                "encoder object to the output using lazy branch evaluation."
            ),
            search_aliases=[
                "Clip Switch",
                "CLIP Switch RvTools",
                "choose CLIP",
                "select text encoder",
            ],
            inputs=_typed_inputs(io.Clip, "CLIP"),
            outputs=_typed_output(io.Clip, "CLIP"),
        )

__all__ = ['ReaperClipSwitch']
