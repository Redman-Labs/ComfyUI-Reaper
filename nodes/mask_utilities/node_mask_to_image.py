"""Node implementation: Mask to Image."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_mask_utilities._shared import *

CATEGORY = CATEGORIES['mask_utilities']
_CATEGORY = CATEGORY

class ReaperMaskToImage(io.ComfyNode):
    """Render a mask as an RGB foreground/background color image."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperMaskToImage",
            display_name=node_title('Mask to Image', branded=True),
            category=_CATEGORY,
            description="Converts a mask to an RGB image using foreground and background colors.",
            inputs=[
                io.Mask.Input(
                    "mask",
                    display_name="Mask",
                    tooltip=(
                        "Mask batch used to blend the two colors. A value of 1 uses "
                        "the foreground color, 0 uses the background color, and "
                        "values between them create a smooth color blend."
                    ),
                ),
                io.Color.Input(
                    "color",
                    display_name="Foreground Color",
                    default="#ffffff",
                    tooltip=(
                        "RGB color placed where the mask is white (value 1). This "
                        "becomes the background-side color when Invert Mask is enabled."
                    ),
                ),
                io.Color.Input(
                    "background",
                    display_name="Background Color",
                    default="#000000",
                    tooltip=(
                        "RGB color placed where the mask is black (value 0). This "
                        "becomes the foreground-side color when Invert Mask is enabled."
                    ),
                ),
                io.Boolean.Input(
                    "invert",
                    display_name="Invert Mask",
                    default=False,
                    label_on="Enabled",
                    label_off="Disabled",
                    tooltip=(
                        "Enabled reverses the mask before coloring, swapping which "
                        "areas receive the foreground and background colors. Disabled "
                        "uses the mask as supplied."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    "image",
                    display_name="Image",
                    tooltip="RGB image batch rendered from the mask and selected colors.",
                )
            ],
            search_aliases=["Mask To Image", "MTB Mask To Image", "colorize mask"],
        )

    @classmethod
    def execute(
        cls,
        mask: torch.Tensor,
        color: str = "#ffffff",
        background: str = "#000000",
        invert: bool = False,
    ) -> io.NodeOutput:
        if mask.ndim != 3:
            raise ValueError("Mask to Image expects a [batch, height, width] mask.")
        alpha = mask.clamp(0.0, 1.0)
        if invert:
            alpha = 1.0 - alpha
        foreground = _color_tensor(color, device=mask.device, dtype=mask.dtype)
        backdrop = _color_tensor(background, device=mask.device, dtype=mask.dtype)
        image = backdrop + alpha.unsqueeze(-1) * (foreground - backdrop)
        return io.NodeOutput(image)

__all__ = ['ReaperMaskToImage']
