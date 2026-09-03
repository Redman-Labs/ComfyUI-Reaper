"""Node implementation: Detect Face By Index."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperDetectFaceByIndex(io.ComfyNode):
    """Detect faces and return one positionally selected FACE object."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperDetectFaceByIndex",
            display_name=node_title('Detect Face By Index', branded=True),
            category=CATEGORY,
            description=(
                "Detects faces, orders them from left to right, and returns one face by its zero-based index. "
                "An optional visual-presentation classifier can be applied before or after index selection."
            ),
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Image",
                    tooltip="Image batch to scan for faces. Faces are ordered by batch position and then from left to right within each image.",
                ),
                io.Float.Input(
                    "threshold",
                    display_name="Detection Threshold",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Minimum YOLO confidence required to keep a detection. Increase it to reject uncertain faces; decrease it to find harder faces.",
                ),
                io.Int.Input(
                    "min_size",
                    display_name="Minimum Face Size",
                    default=64,
                    min=0,
                    max=8192,
                    step=8,
                    tooltip="Rejects detections whose largest dimension is smaller than this number of pixels.",
                ),
                io.Int.Input(
                    "max_size",
                    display_name="Maximum Face Size",
                    default=512,
                    min=8,
                    max=8192,
                    step=8,
                    tooltip="Rejects detections whose largest dimension exceeds this number of pixels.",
                ),
                io.Int.Input(
                    "face_index",
                    display_name="Face Index",
                    default=0,
                    min=0,
                    max=1024,
                    step=1,
                    tooltip="Zero-based left-to-right selection: 0 chooses the leftmost eligible face, 1 chooses the next face, and so on.",
                ),
                io.Combo.Input(
                    "gender_filter",
                    display_name="Presentation Filter",
                    options=["any", "man", "woman"],
                    default="any",
                    tooltip="Any disables classification. Man or Woman keeps only faces assigned that visual-presentation label by the classifier; predictions can be inaccurate.",
                ),
                io.Combo.Input(
                    "priority_mode",
                    display_name="Selection Priority",
                    options=["index_first", "filter_first"],
                    default="index_first",
                    tooltip="Index First selects the indexed face and then checks its label. Filter First removes nonmatching faces before applying Face Index.",
                ),
                io.Mask.Input(
                    "mask",
                    display_name="Exclusion Mask",
                    optional=True,
                    tooltip="Optional mask that suppresses detection in white areas; black areas remain searchable.",
                ),
            ],
            outputs=[
                FaceCollection.Output("faces", display_name="Face", tooltip="A FACE collection containing the selected face, or an empty collection when no eligible index exists."),
                io.Boolean.Output("has_face", display_name="Has Face", tooltip="True when a face was selected; false when detection, filtering, or indexing produced no match."),
            ],
            search_aliases=["DetectFaceByIndex", "SunxAI face index", "select face by position", "leftmost face"],
        )

    @classmethod
    def execute(
        cls,
        image,
        threshold: float,
        min_size: int,
        max_size: int,
        face_index: int,
        gender_filter: str,
        priority_mode: str,
        mask=None,
    ) -> io.NodeOutput:
        faces = list(
            ReaperDetectFaces.execute(
                image, threshold, min_size, max_size, mask
            ).result[0]
        )
        faces.sort(key=lambda face: (getattr(face, "image_idx", 0), face.bbox[0]))

        if gender_filter == "any":
            selected = faces[face_index:face_index + 1]
            return io.NodeOutput(selected, bool(selected))

        classifier = _gender_classifier()
        if priority_mode == "filter_first":
            eligible = [
                face for face in faces
                if _classify_face(face, classifier) == gender_filter
            ]
            selected = eligible[face_index:face_index + 1]
        else:
            selected = faces[face_index:face_index + 1]
            if selected and _classify_face(selected[0], classifier) != gender_filter:
                selected = []
        return io.NodeOutput(selected, bool(selected))

__all__ = ['ReaperDetectFaceByIndex']
