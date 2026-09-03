"""Node implementation: Gender Face Filter."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperGenderFaceFilter(io.ComfyNode):
    """Classify aligned face crops with the source package's gender model."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperGenderFaceFilter",
            display_name=node_title('Gender Face Filter', branded=True),
            category=CATEGORY,
            description=(
                "Uses dima806/man_woman_face_image_detection to divide FACE objects by the selected model label. "
                "The model predicts visual presentation and may be inaccurate; do not treat it as identity data."
            ),
            inputs=[
                FaceCollection.Input("faces", display_name="Faces", tooltip="FACE collection to classify and divide."),
                io.Combo.Input("gender", display_name="Model Label", options=["man", "woman"], default="man", tooltip="Faces whose highest-scoring model label matches this selection are sent to Filtered."),
            ],
            outputs=[
                FaceCollection.Output("filtered", display_name="Filtered", tooltip="Faces matching the selected model label."),
                FaceCollection.Output("rest", display_name="Rest", tooltip="Faces assigned the other model label."),
            ],
            search_aliases=["FaceTools GenderFaceFilter", "face classifier"],
        )

    @classmethod
    def execute(cls, faces, gender: str) -> io.NodeOutput:
        classifier = _gender_classifier()
        filtered, rest = [], []
        for face in faces:
            (filtered if _classify_face(face, classifier) == gender else rest).append(face)
        return io.NodeOutput(filtered, rest)

__all__ = ['ReaperGenderFaceFilter']
