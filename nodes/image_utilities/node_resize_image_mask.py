"""Node implementation: Resize Image & Mask."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperResizeImageMask(ResizeImageMaskNode):
    """Resize an image and its mask together to identical dimensions."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        # Reuse ComfyUI's current dynamic resize controls so every resize mode,
        # tooltip, and Nodes 2.0 behavior stays aligned with the installed
        # ComfyUI version. Only the paired inputs and outputs are customized.
        schema = super().define_schema()
        resize_type_input = schema.inputs[1]
        scale_method_input = schema.inputs[2]

        resize_type_input.display_name = "Resize Type"
        for option in resize_type_input.options:
            option_value = (
                option.key.value
                if isinstance(option.key, ResizeType)
                else str(option.key)
            )
            option.key = option_value.replace("_", " ").title()
            for setting in option.inputs:
                label = setting.id.replace("_", " ").title()
                # Nodes 2.0 currently renders nested DynamicCombo controls from
                # their IDs rather than display_name, so both must be friendly.
                setting.id = label
                setting.display_name = label
                if label == "Crop":
                    setting.options = ["Disabled", "Center"]
                    setting.default = "Center"

        scale_method_input.display_name = "Scale Method"
        scale_method_input.options = [
            "Auto",
            "Nearest-Exact",
            "Bilinear",
            "Area",
            "Bicubic",
            "Lanczos",
        ]
        scale_method_input.default = "Auto"
        scale_method_input.tooltip = (
            "Interpolation algorithm. Auto uses Lanczos when the image is "
            "upscaled and Area when it is downscaled or remains the same size."
        )

        return replace(
            schema,
            node_id="ReaperResizeImageMask",
            display_name=node_title('Resize Image & Mask', branded=True),
            category=_CATEGORY,
            description=(
                "Resizes an image and mask together using ComfyUI's built-in "
                "resize modes. The image determines the final dimensions and "
                "the mask is guaranteed to match them exactly."
            ),
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Image",
                    tooltip=(
                        "Image to resize. Its result determines the exact width "
                        "and height used by both outputs."
                    ),
                ),
                io.Mask.Input(
                    "mask",
                    display_name="Mask",
                    optional=True,
                    tooltip=(
                        "Optional mask associated with the image. When connected, "
                        "it receives the same resize operation and is aligned to "
                        "the resized image's final width and height."
                    ),
                ),
                *schema.inputs[1:],
                io.Boolean.Input(
                    "invert_mask",
                    display_name="Invert Mask",
                    default=False,
                    label_on="True",
                    label_off="False",
                    tooltip=(
                        "When True, inverts the final resized mask so values "
                        "of 0 become 1 and values of 1 become 0."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    id="Resize_Image",
                    display_name="Resized Image",
                    tooltip="Resized image using the selected settings.",
                ),
                io.Mask.Output(
                    id="Resize_Mask",
                    display_name="Resized Mask",
                    tooltip=(
                        "Resized mask with exactly the same width and height as "
                        "Resized Image, or no value when Mask is not connected."
                    ),
                ),
            ],
            search_aliases=[
                *schema.search_aliases,
                "Reaper",
                "Reaper resize image mask",
            ],
        )

    @staticmethod
    def _normalize_resize_settings(
        resize_type: ResizeImageMaskNode.ResizeTypedDict,
    ) -> ResizeImageMaskNode.ResizeTypedDict:
        """Accept friendly Nodes 2.0 labels and legacy snake_case keys."""
        normalized = {}
        for key, value in resize_type.items():
            internal_key = str(key).strip().replace(" ", "_").lower()
            if internal_key == "resize_type":
                if isinstance(value, ResizeType):
                    normalized[internal_key] = value
                else:
                    normalized[internal_key] = str(value).strip().lower()
            elif internal_key == "crop":
                normalized[internal_key] = str(value).strip().lower()
            else:
                normalized[internal_key] = value
        return normalized

    @staticmethod
    def _target_dimensions(
        image: io.Image.Type,
        resize_type: ResizeImageMaskNode.ResizeTypedDict,
    ) -> tuple[int, int]:
        """Calculate the built-in operation's image target as (width, height)."""
        source_height = int(image.shape[1])
        source_width = int(image.shape[2])
        selected = ResizeType(resize_type["resize_type"])

        if selected == ResizeType.SCALE_BY:
            multiplier = resize_type["multiplier"]
            return (
                round(source_width * multiplier),
                round(source_height * multiplier),
            )

        if selected == ResizeType.SCALE_DIMENSIONS:
            width = resize_type["width"]
            height = resize_type["height"]
            if width == 0 and height == 0:
                return source_width, source_height
            if width == 0:
                width = max(1, round(source_width * height / source_height))
            elif height == 0:
                height = max(1, round(source_height * width / source_width))
            return width, height

        if selected in (
            ResizeType.SCALE_LONGER_DIMENSION,
            ResizeType.SCALE_SHORTER_DIMENSION,
        ):
            size_key = (
                "longer_size"
                if selected == ResizeType.SCALE_LONGER_DIMENSION
                else "shorter_size"
            )
            target = resize_type[size_key]
            if source_height == source_width:
                return target, target
            scale = (
                target / max(source_width, source_height)
                if selected == ResizeType.SCALE_LONGER_DIMENSION
                else target / min(source_width, source_height)
            )
            return round(source_width * scale), round(source_height * scale)

        if selected == ResizeType.SCALE_WIDTH:
            width = resize_type["width"]
            if width == 0:
                return source_width, source_height
            height = max(1, round(source_height * width / source_width))
            return width, height

        if selected == ResizeType.SCALE_HEIGHT:
            height = resize_type["height"]
            if height == 0:
                return source_width, source_height
            width = max(1, round(source_width * height / source_height))
            return width, height

        if selected == ResizeType.SCALE_TOTAL_PIXELS:
            total = resize_type["megapixels"] * 1024 * 1024
            scale = math.sqrt(total / (source_width * source_height))
            return round(source_width * scale), round(source_height * scale)

        if selected == ResizeType.MATCH_SIZE:
            match = resize_type["match"]
            if len(match.shape) == 4:
                return int(match.shape[2]), int(match.shape[1])
            return int(match.shape[-1]), int(match.shape[-2])

        if selected == ResizeType.SCALE_TO_MULTIPLE:
            multiple = resize_type["multiple"]
            if multiple <= 1:
                return source_width, source_height
            width = (source_width // multiple) * multiple
            height = (source_height // multiple) * multiple
            if width == 0 or height == 0:
                return source_width, source_height
            return width, height

        raise ValueError(f"Unsupported resize type: {selected}")

    @classmethod
    def _resolve_scale_method(
        cls,
        image: io.Image.Type,
        resize_type: ResizeImageMaskNode.ResizeTypedDict,
        scale_method: io.Combo.Type,
    ) -> str:
        requested = str(scale_method)
        if requested.lower() != "auto":
            normalized = requested.lower()
            if normalized not in cls.scale_methods:
                raise ValueError(f"Unsupported scale method: {scale_method}")
            return normalized

        source_pixels = int(image.shape[1]) * int(image.shape[2])
        target_width, target_height = cls._target_dimensions(image, resize_type)
        target_pixels = target_width * target_height
        return "lanczos" if target_pixels > source_pixels else "area"

    @classmethod
    def execute(
        cls,
        image: io.Image.Type,
        resize_type: ResizeImageMaskNode.ResizeTypedDict,
        scale_method: io.Combo.Type,
        mask: io.Mask.Type | None = None,
        invert_mask: bool = False,
    ) -> io.NodeOutput:
        normalized_resize_type = cls._normalize_resize_settings(resize_type)
        resolved_method = cls._resolve_scale_method(
            image,
            normalized_resize_type,
            scale_method,
        )

        # Always resize the image. The optional mask is only touched when a mask
        # socket is connected.
        resized_image = super().execute(
            image,
            resolved_method,
            normalized_resize_type,
        )[0]

        if mask is None:
            return io.NodeOutput(resized_image, None)

        # Apply the selected built-in operation independently to a connected
        # mask. When both sources already match, this preserves identical crop
        # and aspect-ratio behavior for both tensors.
        resized_mask = super().execute(
            mask,
            resolved_method,
            normalized_resize_type,
        )[0]

        target_height = int(resized_image.shape[1])
        target_width = int(resized_image.shape[2])
        mask_height = int(resized_mask.shape[-2])
        mask_width = int(resized_mask.shape[-1])

        # Differently sized source tensors can produce different dimensions for
        # relative resize modes. Align the mask to the image result so the two
        # outputs are always safe to use together.
        if mask_width != target_width or mask_height != target_height:
            resized_mask = scale_dimensions(
                resized_mask,
                target_width,
                target_height,
                resolved_method,
                "disabled",
            )

        if invert_mask:
            resized_mask = (1.0 - resized_mask).clamp(0.0, 1.0)

        return io.NodeOutput(resized_image, resized_mask)

__all__ = ['ReaperResizeImageMask']
