"""Node implementation: Crop Faces."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_face_utilities._shared import *

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

class ReaperCropFaces(io.ComfyNode):
    """Create aligned face crops, crop masks, and affine transforms."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperCropFaces",
            display_name=node_title('Crop Faces', branded=True),
            category=CATEGORY,
            description=(
                "Aligns and crops every FACE entry into a square batch. It also creates "
                "a matching mask and returns the affine WARP metadata for compatible workflows."
            ),
            inputs=[
                FaceCollection.Input("faces", display_name="Faces", tooltip="FACE collection from Detect Faces or a Face Filter node."),
                io.Int.Input(
                    "crop_size",
                    display_name="Crop Size",
                    default=512,
                    min=128,
                    max=4096,
                    step=64,
                    tooltip="Width and height of every aligned square crop in pixels. Larger values preserve more detail but use more memory.",
                ),
                io.Float.Input(
                    "crop_factor",
                    display_name="Crop Factor",
                    default=1.5,
                    min=1.0,
                    max=3.0,
                    step=0.1,
                    tooltip="Amount of context around the aligned face. 1.0 is tight; larger values include more hair, neck, and background.",
                ),
                io.Combo.Input(
                    "mask_type",
                    display_name="Mask Type",
                    options=list(mask_types),
                    default="convex_hull",
                    tooltip="simple_square uses the transformed face box; convex_hull follows MediaPipe landmarks; BiSeNet and jonathandinu use semantic face parsing.",
                ),
            ],
            outputs=[
                io.Image.Output("crops", display_name="Crops", tooltip="Batch of aligned square face crops."),
                io.Mask.Output("masks", display_name="Masks", tooltip="One crop-space mask for each face."),
                FaceWarp.Output("warps", display_name="Warps", tooltip="Affine crop transforms retained for compatibility with WARP-aware workflows."),
            ],
            search_aliases=["FaceTools CropFaces", "aligned face crop", "face details"],
        )

    @classmethod
    def execute(cls, faces, crop_size: int, crop_factor: float, mask_type: str) -> io.NodeOutput:
        if not faces:
            return io.NodeOutput(
                torch.zeros((1, crop_size, crop_size, 3), dtype=torch.float32),
                torch.zeros((1, crop_size, crop_size), dtype=torch.float32),
                [np.array([[1, 0, -crop_size], [0, 1, -crop_size]], dtype=np.float32)],
            )
        crops, masks, warps = [], [], []
        for face in faces:
            warp, crop = face.crop(crop_size, crop_factor)
            mask = mask_crop(face, warp, crop, mask_type)
            crops.append(crop[0].detach().cpu().numpy())
            masks.append(mask[0].detach().cpu().numpy())
            warps.append(warp)
        return io.NodeOutput(
            torch.from_numpy(np.asarray(crops)).to(torch.float32),
            torch.from_numpy(np.asarray(masks)).to(torch.float32),
            warps,
        )

__all__ = ['ReaperCropFaces']
