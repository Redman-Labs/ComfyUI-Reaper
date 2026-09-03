"""Node implementation: Crop Image to Mask."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperCropImageToMask(io.ComfyNode):
    """
    Crop an image and its mask to the shared bounding box of all active
    mask pixels, with optional padding and size-multiple expansion.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="Reaper_CropImageToMask",
            display_name=node_title('Crop Image to Mask', branded=True),
            category=_CATEGORY,
            description=(
                "Crops an image and mask to the smallest shared bounding box "
                "containing all active mask pixels. Optional padding expands "
                "the crop, and the final width and height are expanded to the "
                "requested multiple whenever the source-image boundaries allow it. "
                "The Uncrop Info output stores the coordinates and original size "
                "needed by a future restoration or uncrop node."
            ),
            search_aliases=[
                "Image",
                "Crop",
                "Mask",
                "Reaper",
                "Crop Image to Mask",
                "CropImageToMask",
                "mask crop",
                "crop by mask",
                "mask bounding box crop",
                "uncrop info",
            ],
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Original Image",
                    tooltip=(
                        "The source image to crop. ComfyUI images use the "
                        "[batch, height, width, channels] layout. The image and "
                        "mask must have matching width and height. A single image "
                        "can be broadcast across a mask batch."
                    ),
                ),
                io.Mask.Input(
                    "mask",
                    display_name="Original Mask",
                    tooltip=(
                        "The mask defining the crop region. Pixels greater than "
                        "0.5 are active. For batches, one shared crop box is built "
                        "around the union of all active pixels so every cropped "
                        "batch item keeps identical dimensions."
                    ),
                ),
                io.Int.Input(
                    "padding",
                    display_name="Padding",
                    default=0,
                    min=0,
                    max=4096,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Expands the detected crop box equally on the top, "
                        "bottom, left, and right by this many pixels. Expansion "
                        "is clipped to the source-image boundaries."
                    ),
                ),
                io.Int.Input(
                    "multiple_of",
                    display_name="Dimensions Multiple Of",
                    default=16,
                    min=1,
                    max=512,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Expands the crop width and height to the next multiple "
                        "of this value, centered around the detected region when "
                        "possible. This is useful for UNet and latent workflows. "
                        "If the source image is smaller or its edge prevents the "
                        "requested multiple, the largest valid in-bounds crop is used."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    id="cropped_image",
                    display_name="Cropped Image",
                    tooltip=(
                        "The cropped section of the original image. Batch size "
                        "and channel count are preserved."
                    ),
                ),
                io.Mask.Output(
                    id="cropped_mask",
                    display_name="Cropped Mask",
                    tooltip=(
                        "The section of the mask corresponding exactly to the "
                        "Cropped Image coordinates. Returned in standard "
                        "ComfyUI [batch, height, width] mask layout."
                    ),
                ),
                CropInfo.Output(
                    id="uncrop_info",
                    display_name="Uncrop Info",
                    tooltip=(
                        "Crop metadata using the CROP_INFO socket type. It "
                        "contains x, y, width, height, original image size, "
                        "batch information, and the cropped mask patch for use "
                        "by a compatible restoration or uncrop node."
                    ),
                ),
            ],
        )

    @staticmethod
    def _normalize_mask(mask: torch.Tensor) -> torch.Tensor:
        """Normalize supported mask layouts to standard [B, H, W]."""
        if not isinstance(mask, torch.Tensor):
            raise TypeError("mask must be a torch.Tensor")

        if mask.ndim == 2:
            return mask.unsqueeze(0)

        if mask.ndim == 3:
            return mask

        if mask.ndim == 4:
            # Collapse channel masks to one mask plane per batch item.
            return mask.amax(dim=1)

        raise ValueError(
            "Unsupported mask shape. Expected [H,W], [B,H,W], "
            f"or [B,C,H,W], but received {tuple(mask.shape)}."
        )

    @staticmethod
    def _validate_image(image: torch.Tensor) -> None:
        """Validate standard ComfyUI IMAGE layout [B, H, W, C]."""
        if not isinstance(image, torch.Tensor):
            raise TypeError("image must be a torch.Tensor")

        if image.ndim != 4:
            raise ValueError(
                "Unsupported image shape. Expected [B,H,W,C], "
                f"but received {tuple(image.shape)}."
            )

        if image.shape[-1] < 1:
            raise ValueError("The image must contain at least one channel.")

    @staticmethod
    def _match_batches(
        image: torch.Tensor,
        mask_bhw: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Match image and mask batch sizes.

        A singleton image or mask can be broadcast across the other batch.
        """
        image_batch = image.shape[0]
        mask_batch = mask_bhw.shape[0]

        if image_batch == mask_batch:
            return image, mask_bhw

        if image_batch == 1:
            return image.expand(mask_batch, -1, -1, -1), mask_bhw

        if mask_batch == 1:
            return image, mask_bhw.expand(image_batch, -1, -1)

        raise ValueError(
            "Image and mask batch sizes must match, or one batch must "
            f"contain one item. Received image batch {image_batch} and "
            f"mask batch {mask_batch}."
        )

    @staticmethod
    def _expand_axis_to_multiple(
        start: int,
        end: int,
        canvas_size: int,
        multiple_of: int,
    ) -> tuple[int, int]:
        """
        Expand one half-open interval to the next requested multiple.

        The expanded interval stays inside the canvas. If the canvas itself
        is smaller than the target or is not divisible by the requested
        multiple, the largest valid interval containing the original region
        is returned.
        """
        current_size = end - start

        if current_size <= 0:
            return 0, canvas_size

        target_size = (
            (current_size + multiple_of - 1) // multiple_of
        ) * multiple_of
        target_size = min(target_size, canvas_size)

        if target_size <= current_size:
            return start, end

        extra = target_size - current_size
        before = extra // 2
        after = extra - before

        new_start = start - before
        new_end = end + after

        if new_start < 0:
            new_end = min(canvas_size, new_end - new_start)
            new_start = 0

        if new_end > canvas_size:
            shift = new_end - canvas_size
            new_start = max(0, new_start - shift)
            new_end = canvas_size

        # Correct any rounding/boundary shortfall while preserving the region.
        actual_size = new_end - new_start
        missing = target_size - actual_size

        if missing > 0:
            grow_left = min(new_start, missing)
            new_start -= grow_left
            missing -= grow_left

        if missing > 0:
            new_end = min(canvas_size, new_end + missing)

        return int(new_start), int(new_end)

    @classmethod
    def execute(
        cls,
        image: torch.Tensor,
        mask: torch.Tensor,
        padding: int,
        multiple_of: int,
    ) -> io.NodeOutput:
        cls._validate_image(image)
        mask_bhw = cls._normalize_mask(mask)
        image, mask_bhw = cls._match_batches(image, mask_bhw)

        image_height = int(image.shape[1])
        image_width = int(image.shape[2])
        mask_height = int(mask_bhw.shape[1])
        mask_width = int(mask_bhw.shape[2])

        if image_height != mask_height or image_width != mask_width:
            raise ValueError(
                "The image and mask must have the same width and height. "
                f"Image: {image_width}x{image_height}; "
                f"mask: {mask_width}x{mask_height}."
            )

        # A shared union box keeps every item in the output batch stackable.
        active_union = (mask_bhw > 0.5).any(dim=0)
        non_zero = torch.nonzero(active_union, as_tuple=False)

        if non_zero.numel() == 0:
            crop_x = 0
            crop_y = 0
            crop_w = image_width
            crop_h = image_height
            cropped_image = image
            cropped_mask = mask_bhw
            was_empty = True
        else:
            min_y = int(non_zero[:, 0].min().item())
            max_y = int(non_zero[:, 0].max().item()) + 1
            min_x = int(non_zero[:, 1].min().item())
            max_x = int(non_zero[:, 1].max().item()) + 1

            # Apply equal padding on all four sides.
            min_x = max(0, min_x - padding)
            min_y = max(0, min_y - padding)
            max_x = min(image_width, max_x + padding)
            max_y = min(image_height, max_y + padding)

            # Expand dimensions to the requested multiple when possible.
            min_x, max_x = cls._expand_axis_to_multiple(
                min_x,
                max_x,
                image_width,
                multiple_of,
            )
            min_y, max_y = cls._expand_axis_to_multiple(
                min_y,
                max_y,
                image_height,
                multiple_of,
            )

            crop_x = min_x
            crop_y = min_y
            crop_w = max_x - min_x
            crop_h = max_y - min_y

            cropped_image = image[
                :,
                crop_y : crop_y + crop_h,
                crop_x : crop_x + crop_w,
                :,
            ]
            cropped_mask = mask_bhw[
                :,
                crop_y : crop_y + crop_h,
                crop_x : crop_x + crop_w,
            ]
            was_empty = False

        uncrop_info = {
            # Original keys retained from the uploaded implementation.
            "x": int(crop_x),
            "y": int(crop_y),
            "w": int(crop_w),
            "h": int(crop_h),
            "original_size": (image_height, image_width),
            "mask_patch": cropped_mask,

            # Additional explicit metadata for future restoration nodes.
            "crop_box": (
                int(crop_x),
                int(crop_y),
                int(crop_x + crop_w),
                int(crop_y + crop_h),
            ),
            "original_batch_size": int(image.shape[0]),
            "image_channels": int(image.shape[-1]),
            "padding": int(padding),
            "multiple_of": int(multiple_of),
            "was_empty": bool(was_empty),
        }

        return io.NodeOutput(cropped_image, cropped_mask, uncrop_info)

__all__ = ['ReaperCropImageToMask']
