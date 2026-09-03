"""Node implementation: Load Image Info."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperLoadImageInfo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLoadImageInfo",
            display_name=node_title('Load Image Info', branded=True),
            category=_CATEGORY,
            description="Unpacks the typed metadata bundle from Load Image (Reaper).",
            inputs=[ReaperImageInfo.Input("image_info", display_name="Image Info", tooltip="Image Info output from Load Image (Reaper).")],
            outputs=[
                io.Image.Output("image", display_name="Image", tooltip="Same loaded image batch carried by the bundle."),
                io.Mask.Output("mask", display_name="Mask", tooltip="Alpha-derived mask; black when the source has no transparency."),
                io.Int.Output("width", display_name="Width", tooltip="Final image width in pixels after resizing."),
                io.Int.Output("height", display_name="Height", tooltip="Final image height in pixels after resizing."),
                io.String.Output("filename", display_name="Filename", tooltip="Source filename without its extension."),
            ],
            is_output_node=True,
            search_aliases=["Image Info Pixaroma", "image metadata", "image dimensions"],
        )

    @classmethod
    def execute(cls, image_info) -> io.NodeOutput:
        if not isinstance(image_info, dict):
            image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            mask = torch.zeros((1, 64, 64), dtype=torch.float32)
            return io.NodeOutput(image, mask, 0, 0, "")
        image = image_info.get("image")
        if not isinstance(image, torch.Tensor):
            image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
        mask = image_info.get("mask")
        if not isinstance(mask, torch.Tensor):
            mask = torch.zeros(image.shape[:3], dtype=image.dtype, device=image.device)
        width = image_info.get("width")
        height = image_info.get("height")
        filename = image_info.get("filename")
        width = width if isinstance(width, int) and width > 0 else int(image.shape[2])
        height = height if isinstance(height, int) and height > 0 else int(image.shape[1])
        filename = filename if isinstance(filename, str) else ""
        return io.NodeOutput(
            image,
            mask,
            width,
            height,
            filename,
            ui={
                "reaper_image_info": [
                    {"width": width, "height": height, "filename": filename}
                ]
            },
        )

__all__ = ['ReaperLoadImageInfo']
