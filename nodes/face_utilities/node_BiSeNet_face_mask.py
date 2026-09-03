"""Node implementation: BiSeNet Face Mask."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperBiSeNetMask(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperBiSeNetMask",
            display_name=node_title('BiSeNet Face Mask', branded=True),
            category=CATEGORY,
            description=(
                "Creates semantic masks for selected facial and surrounding regions with the local BiSeNet face-parsing model. "
                "Requires models/bisenet/79999_iter.pth."
            ),
            inputs=_mask_inputs(),
            outputs=[io.Mask.Output("mask", display_name="Mask", tooltip="Union mask of every enabled semantic region, one mask per input crop.")],
            search_aliases=["FaceTools BiSeNetMask", "face parsing mask"],
        )

    @classmethod
    def execute(cls, crop, **parts) -> io.NodeOutput:
        return io.NodeOutput(mask_BiSeNet(crop, **_part_kwargs(parts)))

__all__ = ['ReaperBiSeNetMask']
