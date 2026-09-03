"""Node implementation: Resize Image to Pixels."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperResizeImageToPixels(io.ComfyNode):
    """Resize an image to a target pixel count while preserving its aspect ratio."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="Reaper_ResizeImageToPixels",
            display_name=node_title('Resize Image to Pixels', branded=True),
            category=_CATEGORY,
            description=(
                "Resizes an image to approximately the requested megapixel "
                "count while preserving its aspect ratio. The calculated width "
                "and height are rounded to valid multiples, making the output "
                "suitable for latent, model, and tiled image workflows."
            ),
            search_aliases=[
                "image",
                "resize",
                "Resize Image to Pixels",
                "resize megapixels",
                "resize image MP",
                "target resolution",
                "image scale",
                "Reaper",
            ],
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Image",
                    tooltip=(
                        "The image or image batch to resize. Every image in the "
                        "batch uses the same source dimensions and is resized to "
                        "the same output dimensions. The batch size and number "
                        "of image channels are preserved."
                    ),
                ),
                io.Float.Input(
                    "target_megapixels",
                    display_name="Target Megapixels",
                    default=1.0,
                    min=0.01,
                    max=100.0,
                    step=0.01,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "The approximate total resolution of the resized image, "
                        "where 1.0 megapixel equals 1,048,576 pixels. For "
                        "example, 1.0 produces 1024×1024 for a square image "
                        "before Multiple Of rounding. The original aspect ratio "
                        "is preserved."
                    ),
                ),
                io.Combo.Input(
                    "method",
                    options=[
                        "Auto",
                        "Bicubic",
                        "Bilinear",
                        "Lanczos",
                        "Nearest-Exact",
                    ],
                    display_name="Method",
                    default="Auto",
                    tooltip=(
                        "The interpolation method used for resizing. Auto uses "
                        "Lanczos when reducing the total pixel count and "
                        "Bilinear when increasing it. Bicubic and Lanczos "
                        "usually produce smoother photographic results. "
                        "Nearest-Exact preserves hard pixel edges."
                    ),
                ),
                io.Int.Input(
                    "multiple_of",
                    display_name="Multiple Of",
                    default=8,
                    min=1,
                    max=512,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Rounds the calculated width and height to the nearest "
                        "positive multiple of this value. This can move the "
                        "final pixel count slightly above or below the target. "
                        "Use 8 for dimensions compatible with common ComfyUI "
                        "latent workflows, or 1 to disable multiple rounding."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    id="resized_image",
                    display_name="Resized Image",
                    tooltip=(
                        "The resized image or image batch. Aspect ratio is "
                        "preserved as closely as the Multiple Of constraint "
                        "allows. Batch size and channel count match the input."
                    ),
                ),
            ],
        )

    @staticmethod
    def _validate_image(image: torch.Tensor) -> None:
        if not isinstance(image, torch.Tensor):
            raise TypeError("image must be a torch.Tensor")

        if image.ndim != 4:
            raise ValueError(
                "Unsupported image shape. Expected [B,H,W,C], "
                f"but received {tuple(image.shape)}."
            )

        if image.shape[1] < 1 or image.shape[2] < 1:
            raise ValueError("The image width and height must be at least 1 pixel.")

        if image.shape[-1] < 1:
            raise ValueError("The image must contain at least one channel.")

    @staticmethod
    def _nearest_multiple(value: float, multiple_of: int) -> int:
        units = max(1, math.floor((value / multiple_of) + 0.5))
        return units * multiple_of

    @classmethod
    def _target_dimensions(
        cls,
        width: int,
        height: int,
        target_megapixels: float,
        multiple_of: int,
    ) -> tuple[int, int]:
        target_pixels = target_megapixels * PIXELS_PER_MEGAPIXEL
        aspect_ratio = width / height

        ideal_width = math.sqrt(target_pixels * aspect_ratio)
        ideal_height = math.sqrt(target_pixels / aspect_ratio)

        target_width = cls._nearest_multiple(ideal_width, multiple_of)
        target_height = cls._nearest_multiple(ideal_height, multiple_of)
        return target_width, target_height

    @classmethod
    def execute(
        cls,
        image: torch.Tensor,
        target_megapixels: float,
        method: str,
        multiple_of: int,
    ) -> io.NodeOutput:
        cls._validate_image(image)

        source_height = int(image.shape[1])
        source_width = int(image.shape[2])
        target_width, target_height = cls._target_dimensions(
            source_width,
            source_height,
            target_megapixels,
            multiple_of,
        )

        if target_width == source_width and target_height == source_height:
            return io.NodeOutput(image)

        if method == "Auto":
            source_pixels = source_width * source_height
            target_pixels = target_width * target_height
            upscale_method = (
                "lanczos" if target_pixels < source_pixels else "bilinear"
            )
        else:
            method_map = {
                "Bicubic": "bicubic",
                "Bilinear": "bilinear",
                "Lanczos": "lanczos",
                "Nearest-Exact": "nearest-exact",
            }
            try:
                upscale_method = method_map[method]
            except KeyError as error:
                raise ValueError(f"Unsupported resize method: {method}") from error

        samples = image.movedim(-1, 1)
        resized = comfy.utils.common_upscale(
            samples,
            target_width,
            target_height,
            upscale_method,
            "disabled",
        )
        resized_image = resized.movedim(1, -1).clamp(0.0, 1.0)

        return io.NodeOutput(resized_image)

__all__ = ['ReaperResizeImageToPixels']
