"""Node implementation: Ordered Face Filter."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperOrderedFaceFilter(io.ComfyNode):
    """Sort faces by area and select a contiguous range."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperOrderedFaceFilter",
            display_name=node_title('Ordered Face Filter', branded=True),
            category=CATEGORY,
            description="Sorts detected faces by pixel area, returns a selected range, and sends every other face to Rest.",
            inputs=[
                FaceCollection.Input("faces", display_name="Faces", tooltip="FACE collection to sort and divide."),
                io.Combo.Input("criteria", display_name="Sort Criterion", options=["area"], default="area", tooltip="Measurement used for sorting. Area is face-box width multiplied by height."),
                io.Combo.Input("order", display_name="Sort Order", options=["descending", "ascending"], default="descending", tooltip="Descending starts with the largest faces; ascending starts with the smallest."),
                io.Int.Input("take_start", display_name="Start Index", default=0, min=0, step=1, tooltip="Zero-based position in the sorted list where selection begins."),
                io.Int.Input("take_count", display_name="Face Count", default=1, min=1, step=1, tooltip="Maximum number of consecutive faces to place in Filtered."),
            ],
            outputs=[
                FaceCollection.Output("filtered", display_name="Filtered", tooltip="Selected range from the sorted face list."),
                FaceCollection.Output("rest", display_name="Rest", tooltip="All faces outside the selected range."),
            ],
            search_aliases=["FaceTools OrderedFaceFilter", "largest face", "smallest face"],
        )

    @classmethod
    def execute(cls, faces, criteria: str, order: str, take_start: int, take_count: int) -> io.NodeOutput:
        del criteria
        ordered = sorted(faces, key=lambda face: face.w * face.h, reverse=order == "descending")
        end = take_start + take_count
        return io.NodeOutput(ordered[take_start:end], ordered[:take_start] + ordered[end:])

__all__ = ['ReaperOrderedFaceFilter']
