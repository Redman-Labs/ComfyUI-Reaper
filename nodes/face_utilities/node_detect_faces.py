"""Node implementation: Detect Faces."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperDetectFaces(io.ComfyNode):
    """Detect rotation-aware faces and retain their source-image metadata."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperDetectFaces",
            display_name=node_title('Detect Faces', branded=True),
            category=CATEGORY,
            description=(
                "Detects faces with the FaceTools YOLO model, estimates rotation-aware "
                "landmarks, and returns FACE objects for the other Face Tools nodes."
            ),
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Image",
                    tooltip="Image batch to scan. Each detected face remembers which image in the batch it came from.",
                ),
                io.Float.Input(
                    "threshold",
                    display_name="Detection Threshold",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Minimum YOLO confidence required to keep a face. Higher values reject uncertain detections.",
                ),
                io.Int.Input(
                    "min_size",
                    display_name="Minimum Face Size",
                    default=64,
                    min=0,
                    max=8192,
                    step=8,
                    tooltip="Rejects detections whose width and height are both smaller than this pixel size.",
                ),
                io.Int.Input(
                    "max_size",
                    display_name="Maximum Face Size",
                    default=512,
                    min=8,
                    max=8192,
                    step=8,
                    tooltip="Rejects detections whose width and height are both larger than this pixel size.",
                ),
                io.Mask.Input(
                    "mask",
                    display_name="Exclusion Mask",
                    optional=True,
                    tooltip="Optional mask that suppresses detection in white areas; black areas remain searchable.",
                ),
            ],
            outputs=[FaceCollection.Output("faces", display_name="Faces", tooltip="Detected FACE collection used by Face Tools filters and Crop Faces.")],
            search_aliases=["FaceTools DetectFaces", "face detector", "find faces"],
        )

    @classmethod
    def execute(cls, image, threshold: float, min_size: int, max_size: int, mask=None) -> io.NodeOutput:
        if min_size > max_size:
            raise ValueError("Minimum Face Size cannot be greater than Maximum Face Size.")
        masked = image
        if mask is not None:
            resized_mask = tv.transforms.functional.resize(
                mask.unsqueeze(1), image.shape[1:3], antialias=False
            ).squeeze(1)
            if resized_mask.shape[0] == 1 and image.shape[0] > 1:
                resized_mask = resized_mask.expand(image.shape[0], -1, -1)
            masked = image * (1.0 - resized_mask.clamp(0, 1))[..., None]

        faces = []
        for image_index, frame in enumerate((masked.clamp(0, 1) * 255).to(torch.uint8)):
            for face in detect_faces(frame, threshold):
                left, top, right, bottom = face.bbox
                height, width = abs(bottom - top), abs(right - left)
                if max(height, width) > max_size or max(height, width) < min_size:
                    continue
                face.image_idx = image_index
                face.img = image[image_index].detach().cpu()
                faces.append(face)
        return io.NodeOutput(faces)

__all__ = ['ReaperDetectFaces']
