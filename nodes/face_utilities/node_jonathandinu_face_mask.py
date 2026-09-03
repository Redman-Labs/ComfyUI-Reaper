"""Node implementation: Jonathandinu Face Mask."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperJonathandinuMask(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        defaults = {"eyeglasses": False, "earring": False}
        return io.Schema(
            node_id="ReaperJonathandinuMask",
            display_name=node_title('Jonathandinu Face Mask', branded=True),
            category=CATEGORY,
            description=(
                "Creates detailed semantic face masks with jonathandinu/face-parsing from Hugging Face. "
                "The model downloads on first use and generally consumes more memory than BiSeNet."
            ),
            inputs=_mask_inputs(defaults),
            outputs=[io.Mask.Output("mask", display_name="Mask", tooltip="Union mask of every enabled semantic region, one mask per input crop.")],
            search_aliases=["FaceTools JonathandinuMask", "SegFormer face parsing"],
        )

    @classmethod
    def execute(cls, crop, **parts) -> io.NodeOutput:
        return io.NodeOutput(mask_jonathandinu(crop, **_part_kwargs(parts)))

__all__ = ['ReaperJonathandinuMask']
