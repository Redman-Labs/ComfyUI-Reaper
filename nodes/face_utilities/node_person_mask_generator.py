"""Node implementation: Person Mask Generator."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperPersonMaskGenerator(io.ComfyNode):
    """Create one union mask from person classes and precise face regions."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        toggle = lambda name, label, default=False, tooltip=None: io.Boolean.Input(
            name,
            display_name=label,
            default=default,
            label_on="Enabled",
            label_off="Disabled",
            tooltip=tooltip,
        )
        return io.Schema(
            node_id="ReaperPersonMaskGenerator",
            display_name=node_title('Person Mask Generator', branded=True),
            category=CATEGORY,
            description=(
                "Creates a combined mask from MediaPipe person segmentation "
                "classes and precise facial landmarks. Enabled regions are unioned."
            ),
            inputs=[
                io.Image.Input("images", display_name="Images"),
                toggle("face_mask", "Face", True, "Segmented facial skin."),
                toggle("background_mask", "Background"),
                toggle("hair_mask", "Hair"),
                toggle("body_mask", "Body / Skin"),
                toggle("clothes_mask", "Clothes"),
                toggle("left_eyebrow", "Left Eyebrow"),
                toggle("right_eyebrow", "Right Eyebrow"),
                toggle("left_eye", "Left Eye"),
                toggle("right_eye", "Right Eye"),
                toggle("left_pupil", "Left Pupil"),
                toggle("right_pupil", "Right Pupil"),
                toggle("lips", "Lips"),
                io.Int.Input(
                    "number_of_faces",
                    display_name="Number of Faces",
                    default=1,
                    min=1,
                    max=20,
                    step=1,
                    tooltip="Maximum number of faces used for landmark masks.",
                ),
                io.Float.Input(
                    "confidence",
                    display_name="Confidence",
                    default=0.40,
                    min=0.01,
                    max=1.0,
                    step=0.01,
                ),
                toggle(
                    "refine_mask",
                    "Refine Segmentation",
                    True,
                    "Repeats person segmentation on a padded detected crop.",
                ),
                toggle(
                    "invert_mask",
                    "Invert Mask",
                    False,
                    "Inverts the final mask so selected areas become black and unselected areas become white.",
                ),
            ],
            outputs=[io.Mask.Output("masks", display_name="Masks")],
            search_aliases=[
                "A Person Mask Generator",
                "face landmark mask",
                "MediaPipe person mask",
                "Reaper person mask",
            ],
        )

    @classmethod
    def execute(
        cls,
        images: torch.Tensor,
        face_mask: bool = True,
        background_mask: bool = False,
        hair_mask: bool = False,
        body_mask: bool = False,
        clothes_mask: bool = False,
        left_eyebrow: bool = False,
        right_eyebrow: bool = False,
        left_eye: bool = False,
        right_eye: bool = False,
        left_pupil: bool = False,
        right_pupil: bool = False,
        lips: bool = False,
        number_of_faces: int = 1,
        confidence: float = 0.40,
        refine_mask: bool = True,
        invert_mask: bool = False,
    ) -> io.NodeOutput:
        class_flags = [
            background_mask,
            hair_mask,
            body_mask,
            face_mask,
            clothes_mask,
        ]
        classes = [index for index, enabled in enumerate(class_flags) if enabled]
        region_flags = {
            "left_eyebrow": left_eyebrow,
            "right_eyebrow": right_eyebrow,
            "left_eye": left_eye,
            "right_eye": right_eye,
            "left_pupil": left_pupil,
            "right_pupil": right_pupil,
            "lips": lips,
        }
        regions = [name for name, enabled in region_flags.items() if enabled]

        segmenter = None
        landmarker = None
        try:
            if classes:
                options = mp.tasks.vision.ImageSegmenterOptions(
                    base_options=mp.tasks.BaseOptions(
                        model_asset_path=_model_path(_SEGMENTER_MODEL)
                    ),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    output_confidence_masks=True,
                )
                segmenter = mp.tasks.vision.ImageSegmenter.create_from_options(options)
            if regions:
                options = mp.tasks.vision.FaceLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(
                        model_asset_path=_model_path(_LANDMARKER_MODEL)
                    ),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    num_faces=number_of_faces,
                    min_face_detection_confidence=confidence,
                    min_face_presence_confidence=confidence,
                )
                landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

            output = []
            for image in images:
                rgb = np.clip(image.detach().cpu().numpy() * 255.0, 0, 255).astype(
                    np.uint8
                )
                combined = np.zeros(rgb.shape[:2], dtype=np.float32)
                if segmenter is not None:
                    combined = np.maximum(
                        combined,
                        _segment(segmenter, rgb, classes, confidence, refine_mask),
                    )
                if landmarker is not None:
                    combined = np.maximum(
                        combined,
                        _landmarks(landmarker, rgb, regions),
                    )
                if invert_mask:
                    combined = 1.0 - combined
                output.append(torch.from_numpy(combined))
            return io.NodeOutput(torch.stack(output, dim=0))
        finally:
            if landmarker is not None:
                landmarker.close()
            if segmenter is not None:
                segmenter.close()

__all__ = ['ReaperPersonMaskGenerator']
