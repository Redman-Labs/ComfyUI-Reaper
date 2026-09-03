"""Node implementation: Model Visualize Tiles."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_model_utilities._shared import *

CATEGORY = CATEGORIES['model_utilities']
_CATEGORY = CATEGORY

class ReaperVisualizeTiles(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperVisualizeTiles",
            display_name=node_title('Model Visualize Tiles', branded=True),
            category=CATEGORY,
            description=(
                "Draws each calculated one-dimensional tile and its blending "
                "mask as an image row, making overlap and dropped regions easy to inspect."
            ),
            search_aliases=[
                "Visualize Tiles VAE Utils",
                "tile overlap preview",
                "tile blend mask",
            ],
            inputs=[
                io.Int.Input(
                    "length",
                    display_name="Length",
                    default=21,
                    min=1,
                    step=1,
                    tooltip="Total one-dimensional length being divided into tiles.",
                ),
                io.Int.Input(
                    "tile_size",
                    display_name="Tile Size",
                    default=13,
                    min=1,
                    step=1,
                    tooltip="Maximum length of each tile.",
                ),
                io.Int.Input(
                    "min_overlap",
                    display_name="Minimum Overlap",
                    default=5,
                    min=0,
                    step=1,
                    tooltip="Minimum shared length between neighboring tiles.",
                ),
                io.Int.Input(
                    "drop_first",
                    display_name="Drop First",
                    default=2,
                    min=0,
                    step=1,
                    tooltip="Leading overlap positions to zero in each non-first tile.",
                ),
            ],
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Tile Visualization",
                    tooltip=(
                        "An enlarged grayscale visualization with one horizontal row per tile."
                    ),
                )
            ],
        )

    @classmethod
    def execute(
        cls,
        length: int,
        tile_size: int,
        min_overlap: int,
        drop_first: int,
    ) -> io.NodeOutput:
        tiles = get_tiles(length, tile_size, min_overlap)
        image = torch.zeros(1, 3, len(tiles), length)
        for index, (start, end) in enumerate(tiles):
            image[:, :, index, start:end] = get_1d_mask(
                index, tiles, drop_first
            )
        image = F.interpolate(
            image, scale_factor=8, mode="nearest-exact"
        ).movedim(1, -1)
        return io.NodeOutput(image)

__all__ = ['ReaperVisualizeTiles']
