"""Node implementation: Image Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperImageSwitch(_TwoInputSwitch):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperImageSwitch",
            display_name=node_title('Image Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects Image 1 or Image 2 and passes only the selected image "
                "or image batch to the output using lazy branch evaluation."
            ),
            search_aliases=[
                "Image Switch",
                "Image Switch RvTools",
                "choose image",
                "select image input",
            ],
            inputs=_typed_inputs(io.Image, "Image"),
            outputs=_typed_output(io.Image, "Image"),
        )

__all__ = ['ReaperImageSwitch']
