"""Node implementation: Load Images from Folder."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperLoadImagesFolder(io.ComfyNode):
    """Load a user-selected list of images from an approved folder."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLoadImagesFolder",
            display_name=node_title('Load Images from Folder', branded=True),
            category=_CATEGORY,
            description=_ReaperLoadImagesFolderEngine.DESCRIPTION,
            inputs=[
                io.String.Input(
                    "LoadImagesFolderState",
                    display_name="Load Images Folder State",
                    default=json.dumps(LOAD_IMAGES_FOLDER_DEFAULT_STATE),
                    tooltip="Internal state managed by the node's custom interface.",
                ),
            ],
            outputs=[
                io.Image.Output("image", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[0], is_output_list=True),
                io.Mask.Output("mask", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[1], is_output_list=True),
                io.Int.Output("width", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[2], is_output_list=True),
                io.Int.Output("height", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[3], is_output_list=True),
                io.String.Output("filename", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[4], is_output_list=True),
                io.Int.Output("index", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[5], is_output_list=True),
                io.Int.Output("total", tooltip=_ReaperLoadImagesFolderEngine.OUTPUT_TOOLTIPS[6], is_output_list=True),
            ],
        )

    @classmethod
    def execute(cls, LoadImagesFolderState: str = "") -> io.NodeOutput:
        return io.NodeOutput(*_ReaperLoadImagesFolderEngine().load(LoadImagesFolderState))

    @classmethod
    def fingerprint_inputs(cls, LoadImagesFolderState: str = "") -> str:
        return _ReaperLoadImagesFolderEngine.IS_CHANGED(LoadImagesFolderState)

__all__ = ['ReaperLoadImagesFolder']
