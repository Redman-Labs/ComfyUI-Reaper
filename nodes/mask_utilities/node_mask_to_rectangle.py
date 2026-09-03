"""Node implementation: Mask to Rectangle."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_mask_utilities._shared import *

CATEGORY = CATEGORIES['mask_utilities']
_CATEGORY = CATEGORY

class ReaperMaskToRectangle(io.ComfyNode):
    """
    Convert each disconnected mask region to its own axis-aligned
    rectangle and visualize every rectangle over the source image.
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            # Preserved for compatibility with existing saved workflows.
            node_id="MaskToRectangle",
            display_name=node_title('Mask to Rectangle', branded=True),
            category=_CATEGORY,
            description=(
                "Detects every disconnected foreground region in a mask and "
                "converts each region into its own axis-aligned rectangle. "
                "Independent positive or negative padding can be applied to "
                "the top, bottom, left, and right edges. The node returns both "
                "a combined filled rectangle mask and a copy of the source "
                "image with separate border boxes or translucent filled "
                "rectangles."
            ),
            search_aliases=[
                "Reaper",
                "mask rectangle",
                "mask to bbox",
                "bounding box",
                "border box",
                "multiple mask boxes",
            ],
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Original Image",
                    tooltip=(
                        "The original source image associated with the mask. "
                        "The image is copied to the image output, then every "
                        "detected rectangle is drawn over that copy. The image "
                        "and mask must have the same width and height. A single "
                        "image can be reused across a batch of masks."
                    ),
                ),
                io.Mask.Input(
                    "mask",
                    display_name="Original Mask",
                    tooltip=(
                        "The source mask containing one or more foreground "
                        "regions. Pixels above Mask Threshold are active. Every "
                        "disconnected 8-connected region that passes Minimum "
                        "Component Area receives its own rectangle."
                    ),
                ),
                io.Float.Input(
                    "threshold",
                    display_name="Mask Threshold",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Controls which mask pixels are considered active. "
                        "Only values strictly greater than this threshold are "
                        "used. Raise it to ignore faint or soft mask edges; "
                        "lower it to include more partially masked pixels."
                    ),
                ),
                io.Int.Input(
                    "minimum_mask_area",
                    display_name="Minimum Mask Area",
                    default=32,
                    min=1,
                    max=16777216,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "The minimum number of active pixels required for a "
                        "disconnected mask region to create a rectangle. Smaller "
                        "regions are treated as noise and ignored. Use 1 to keep "
                        "every region, including single-pixel specks. This is "
                        "measured before padding is applied."
                    ),
                ),
                io.Int.Input(
                    "padding_up",
                    display_name="Padding Up",
                    default=0,
                    min=-8192,
                    max=8192,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Moves the top edge of every detected rectangle. A "
                        "positive value expands the rectangle upward by that "
                        "many pixels. A negative value contracts it by moving "
                        "the top edge downward. The result is clipped to the "
                        "image boundary."
                    ),
                ),
                io.Int.Input(
                    "padding_down",
                    display_name="Padding Down",
                    default=0,
                    min=-8192,
                    max=8192,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Moves the bottom edge of every detected rectangle. A "
                        "positive value expands the rectangle downward by that "
                        "many pixels. A negative value contracts it by moving "
                        "the bottom edge upward. The result is clipped to the "
                        "image boundary."
                    ),
                ),
                io.Int.Input(
                    "padding_left",
                    display_name="Padding Left",
                    default=0,
                    min=-8192,
                    max=8192,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Moves the left edge of every detected rectangle. A "
                        "positive value expands the rectangle left by that many "
                        "pixels. A negative value contracts it by moving the "
                        "left edge right. The result is clipped to the image "
                        "boundary."
                    ),
                ),
                io.Int.Input(
                    "padding_right",
                    display_name="Padding Right",
                    default=0,
                    min=-8192,
                    max=8192,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Moves the right edge of every detected rectangle. A "
                        "positive value expands the rectangle right by that many "
                        "pixels. A negative value contracts it by moving the "
                        "right edge left. The result is clipped to the image "
                        "boundary."
                    ),
                ),
                io.Combo.Input(
                    "overlay_style",
                    options=["border_box", "filled_rectangle"],
                    display_name="Overlay Style",
                    default="border_box",
                    tooltip=(
                        "Selects how rectangles are displayed on the image "
                        "output. border_box draws a separate red outline for "
                        "every detected region, including overlapping boxes. "
                        "filled_rectangle applies a translucent red fill to the "
                        "combined rectangle area."
                    ),
                ),
                io.Int.Input(
                    "line_width",
                    display_name="Border Line Width",
                    default=4,
                    min=1,
                    max=512,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Thickness of each border-box line in pixels. This "
                        "setting affects only the border_box overlay style; it "
                        "does not change rectangle size or the filled mask "
                        "output. Very large values may fill a small box."
                    ),
                ),
                io.Float.Input(
                    "fill_value",
                    display_name="Mask Fill Value",
                    default=1.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "The pixel value written inside every rectangle in the "
                        "Rectangle Mask output. Use 1.0 for a solid white mask. "
                        "Lower values produce gray or partially weighted mask "
                        "rectangles. This does not control image-overlay opacity "
                        "or color."
                    ),
                ),
                io.Combo.Input(
                    "empty_mask",
                    options=["keep_empty", "full_frame"],
                    display_name="Empty Mask Behavior",
                    default="keep_empty",
                    tooltip=(
                        "Controls the result when no component survives the Mask "
                        "Threshold and Minimum Component Area settings. "
                        "keep_empty returns an empty rectangle mask and leaves "
                        "the image unchanged. full_frame creates one rectangle "
                        "covering the entire image and draws that rectangle."
                    ),
                ),
            ],
            outputs=[
                io.Mask.Output(
                    id="rectangle_mask",
                    display_name="Rectangle Mask",
                    tooltip=(
                        "A mask containing one filled axis-aligned rectangle for "
                        "every disconnected input-mask component that passes the "
                        "threshold and minimum-area filters. Padding is applied "
                        "independently to each rectangle. Overlapping rectangles "
                        "are combined into one mask area."
                    ),
                ),
                io.Image.Output(
                    id="image_with_rectangles",
                    display_name="Image With Rectangles",
                    tooltip=(
                        "A copy of the original image with every adjusted "
                        "rectangle drawn over it. border_box produces separate "
                        "red outlines, even when boxes overlap. filled_rectangle "
                        "produces a translucent red overlay. Image dimensions, "
                        "batch ordering, and alpha channels are preserved."
                    ),
                ),
            ],
        )

    @staticmethod
    def _normalize_to_bhw(mask: torch.Tensor):
        """Normalize supported mask layouts to [B, H, W]."""
        if not isinstance(mask, torch.Tensor):
            raise TypeError("mask must be a torch.Tensor")

        if mask.ndim == 2:
            return mask.unsqueeze(0), "HW", None

        if mask.ndim == 3:
            return mask, "BHW", None

        if mask.ndim == 4:
            channels = mask.shape[1]
            return mask.amax(dim=1), "BCHW", channels

        raise ValueError(
            "Unsupported mask shape. Expected [H,W], [B,H,W], "
            f"or [B,C,H,W], but received {tuple(mask.shape)}."
        )

    @staticmethod
    def _restore_layout(mask_bhw: torch.Tensor, layout: str, channels):
        if layout == "HW":
            return mask_bhw[0]

        if layout == "BHW":
            return mask_bhw

        if layout == "BCHW":
            return (
                mask_bhw.unsqueeze(1)
                .expand(-1, channels, -1, -1)
                .clone()
            )

        raise RuntimeError(f"Unknown mask layout: {layout}")

    @staticmethod
    def _validate_image(image: torch.Tensor):
        """Validate standard ComfyUI IMAGE layout: [B, H, W, C]."""
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
    def _match_batches(mask_bhw: torch.Tensor, image: torch.Tensor):
        """
        Match mask and image batches.

        A single mask can be used for every image in a batch, and a
        single image can be used for every mask in a batch.
        """
        mask_batch = mask_bhw.shape[0]
        image_batch = image.shape[0]

        if mask_batch == image_batch:
            return mask_bhw, image

        if mask_batch == 1:
            return mask_bhw.expand(image_batch, -1, -1), image

        if image_batch == 1:
            return mask_bhw, image.expand(mask_batch, -1, -1, -1)

        raise ValueError(
            "Mask and image batch sizes must match, or one batch must "
            f"contain exactly one item. Received mask batch {mask_batch} "
            f"and image batch {image_batch}."
        )

    @staticmethod
    def _find_component_boxes(
        mask: torch.Tensor,
        threshold: float,
        minimum_mask_area: int,
    ):
        """
        Return one bounding box for each qualifying 8-connected component.

        The implementation uses row runs plus union-find rather than
        visiting every active pixel in Python. This keeps large, smooth
        masks practical without requiring OpenCV or SciPy.

        A pixel is active only when its mask value is strictly greater
        than threshold. Components containing fewer than
        minimum_mask_area active pixels are excluded.

        Boxes use half-open coordinates:
            (top, bottom, left, right)
        """
        if mask.ndim != 2:
            raise ValueError(
                "Component detection requires one [H,W] mask plane, "
                f"but received {tuple(mask.shape)}."
            )

        threshold = float(threshold)
        minimum_mask_area = int(minimum_mask_area)

        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "Mask Threshold must be between 0.0 and 1.0, "
                f"but received {threshold}."
            )

        if minimum_mask_area < 1:
            raise ValueError(
                "Minimum Mask Area must be at least 1, "
                f"but received {minimum_mask_area}."
            )

        binary = (
            (mask.detach() > threshold)
            .to(device="cpu", dtype=torch.bool)
            .contiguous()
            .numpy()
        )
        height, width = binary.shape

        parent = []
        rank = []
        runs = []
        previous_row_runs = []

        def make_set():
            index = len(parent)
            parent.append(index)
            rank.append(0)
            return index

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(first, second):
            root_first = find(first)
            root_second = find(second)

            if root_first == root_second:
                return

            if rank[root_first] < rank[root_second]:
                root_first, root_second = root_second, root_first

            parent[root_second] = root_first

            if rank[root_first] == rank[root_second]:
                rank[root_first] += 1

        for y in range(height):
            row = binary[y]

            if not row.any():
                previous_row_runs = []
                continue

            padded = np.empty(width + 2, dtype=np.bool_)
            padded[0] = False
            padded[-1] = False
            padded[1:-1] = row

            transitions = np.flatnonzero(
                padded[1:] != padded[:-1]
            )
            starts = transitions[0::2]
            ends = transitions[1::2]

            current_row_runs = []

            for start, end in zip(starts.tolist(), ends.tolist()):
                run_id = make_set()
                runs.append((run_id, y, start, end))
                current_row_runs.append((run_id, start, end))

            # Connect runs that overlap or touch diagonally on
            # adjacent rows. This is standard 8-connectivity.
            previous_index = 0

            for current_id, current_start, current_end in current_row_runs:
                while (
                    previous_index < len(previous_row_runs)
                    and previous_row_runs[previous_index][2] < current_start
                ):
                    previous_index += 1

                candidate_index = previous_index

                while candidate_index < len(previous_row_runs):
                    previous_id, previous_start, previous_end = (
                        previous_row_runs[candidate_index]
                    )

                    if previous_start > current_end:
                        break

                    # Half-open runs diagonally touch when an endpoint
                    # differs by exactly one pixel, so <= is intentional.
                    if (
                        current_start <= previous_end
                        and previous_start <= current_end
                    ):
                        union(current_id, previous_id)

                    candidate_index += 1

            previous_row_runs = current_row_runs

        if not runs:
            return []

        component_stats = {}

        for run_id, y, start, end in runs:
            root = find(run_id)
            run_area = end - start

            if root not in component_stats:
                component_stats[root] = [
                    y,
                    y + 1,
                    start,
                    end,
                    run_area,
                ]
                continue

            stats = component_stats[root]
            stats[0] = min(stats[0], y)
            stats[1] = max(stats[1], y + 1)
            stats[2] = min(stats[2], start)
            stats[3] = max(stats[3], end)
            stats[4] += run_area

        boxes = []

        for top, bottom, left, right, area in component_stats.values():
            if area >= minimum_mask_area:
                boxes.append((top, bottom, left, right))

        # Stable top-to-bottom, then left-to-right ordering.
        boxes.sort(key=lambda box: (box[0], box[2], box[1], box[3]))
        return boxes

    @staticmethod
    def _apply_padding(
        rectangle,
        height: int,
        width: int,
        padding_up: int,
        padding_down: int,
        padding_left: int,
        padding_right: int,
    ):
        top, bottom, left, right = rectangle

        top -= padding_up
        bottom += padding_down
        left -= padding_left
        right += padding_right

        top = max(0, min(top, height))
        bottom = max(0, min(bottom, height))
        left = max(0, min(left, width))
        right = max(0, min(right, width))

        if top >= bottom or left >= right:
            return None

        return (top, bottom, left, right)

    @staticmethod
    def _overlay_color(image: torch.Tensor):
        """
        Return a visible drawing color compatible with image channels.

        RGB/RGBA images use red. Single-channel images use white.
        Channels beyond RGB, including alpha, remain unchanged.
        """
        channels = image.shape[-1]

        if channels == 1:
            return image.new_tensor([1.0])

        color = image.new_zeros(min(channels, 3))
        color[0] = 1.0
        return color

    @staticmethod
    def _draw_border_box(
        output_image: torch.Tensor,
        index: int,
        rectangle,
        line_width: int,
        color: torch.Tensor,
    ):
        top, bottom, left, right = rectangle
        box_height = bottom - top
        box_width = right - left

        horizontal_width = min(line_width, box_height)
        vertical_width = min(line_width, box_width)
        color_channels = color.numel()

        output_image[
            index,
            top : top + horizontal_width,
            left:right,
            :color_channels,
        ] = color
        output_image[
            index,
            bottom - horizontal_width : bottom,
            left:right,
            :color_channels,
        ] = color
        output_image[
            index,
            top:bottom,
            left : left + vertical_width,
            :color_channels,
        ] = color
        output_image[
            index,
            top:bottom,
            right - vertical_width : right,
            :color_channels,
        ] = color

    @staticmethod
    def _draw_filled_rectangles(
        output_image: torch.Tensor,
        index: int,
        rectangles,
        color: torch.Tensor,
    ):
        """
        Blend the union of all filled rectangles once.

        Overlapping filled rectangles therefore keep a consistent
        opacity rather than becoming darker where they overlap.
        """
        if not rectangles:
            return

        height = output_image.shape[1]
        width = output_image.shape[2]
        union_mask = torch.zeros(
            (height, width),
            dtype=torch.bool,
            device=output_image.device,
        )

        for top, bottom, left, right in rectangles:
            union_mask[top:bottom, left:right] = True

        color_channels = color.numel()
        opacity = 0.35
        region = output_image[index, :, :, :color_channels]

        output_image[index, :, :, :color_channels] = torch.where(
            union_mask.unsqueeze(-1),
            region * (1.0 - opacity) + color * opacity,
            region,
        )

    @classmethod
    def execute(
        cls,
        image: torch.Tensor,
        mask: torch.Tensor,
        threshold: float,
        minimum_mask_area: int,
        padding_up: int,
        padding_down: int,
        padding_left: int,
        padding_right: int,
        overlay_style: str,
        line_width: int,
        fill_value: float,
        empty_mask: str,
    ):
        cls._validate_image(image)
        mask_bhw, layout, channels = cls._normalize_to_bhw(mask)
        mask_bhw, matched_image = cls._match_batches(mask_bhw, image)

        batch, mask_height, mask_width = mask_bhw.shape
        image_height = matched_image.shape[1]
        image_width = matched_image.shape[2]

        if mask_height != image_height or mask_width != image_width:
            raise ValueError(
                "The image and mask must have the same width and height. "
                f"Mask: {mask_width}x{mask_height}; "
                f"image: {image_width}x{image_height}."
            )

        rectangle_mask_bhw = torch.zeros_like(mask_bhw)
        output_image = matched_image.clone()
        rectangles_per_image = []

        for index in range(batch):
            component_boxes = cls._find_component_boxes(
                mask_bhw[index],
                threshold,
                minimum_mask_area,
            )

            if not component_boxes:
                if empty_mask == "full_frame":
                    full_frame = (
                        0,
                        mask_height,
                        0,
                        mask_width,
                    )
                    rectangle_mask_bhw[index].fill_(fill_value)
                    rectangles_per_image.append([full_frame])
                else:
                    rectangles_per_image.append([])
                continue

            padded_rectangles = []

            for component_box in component_boxes:
                padded_rectangle = cls._apply_padding(
                    component_box,
                    mask_height,
                    mask_width,
                    padding_up,
                    padding_down,
                    padding_left,
                    padding_right,
                )

                if padded_rectangle is None:
                    continue

                padded_rectangles.append(padded_rectangle)
                top, bottom, left, right = padded_rectangle
                rectangle_mask_bhw[
                    index,
                    top:bottom,
                    left:right,
                ] = fill_value

            rectangles_per_image.append(padded_rectangles)

        color = cls._overlay_color(output_image)

        for index, rectangles in enumerate(rectangles_per_image):
            if overlay_style == "border_box":
                # Draw each box separately. Even when padded boxes
                # overlap, all of their individual edges are retained.
                for rectangle in rectangles:
                    cls._draw_border_box(
                        output_image,
                        index,
                        rectangle,
                        line_width,
                        color,
                    )
            elif overlay_style == "filled_rectangle":
                cls._draw_filled_rectangles(
                    output_image,
                    index,
                    rectangles,
                    color,
                )
            else:
                raise ValueError(
                    f"Unsupported overlay style: {overlay_style}"
                )

        output_image = output_image.clamp(0.0, 1.0)

        # Preserve the incoming layout when possible. When a singleton
        # mask was broadcast to an image batch, return standard [B,H,W].
        if rectangle_mask_bhw.shape[0] == 1:
            rectangle_mask = cls._restore_layout(
                rectangle_mask_bhw,
                layout,
                channels,
            )
        elif layout == "BCHW":
            rectangle_mask = cls._restore_layout(
                rectangle_mask_bhw,
                layout,
                channels,
            )
        else:
            rectangle_mask = rectangle_mask_bhw

        return io.NodeOutput(rectangle_mask, output_image)

__all__ = ['ReaperMaskToRectangle']
