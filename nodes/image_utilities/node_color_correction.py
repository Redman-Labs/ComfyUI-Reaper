"""Node implementation: Color Correction."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperColorCorrection(io.ComfyNode):
    """GPU-capable Torch color correction with optional mask compositing."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperColorCorrection",
            display_name=node_title('Color Correction', branded=True),
            category=_CATEGORY,
            description=(
                "Adjusts gamma, contrast, exposure, offset, hue, saturation, "
                "and value using Torch, optionally limited by a mask."
            ),
            inputs=[
                io.Image.Input(
                    "image",
                    display_name="Image",
                    tooltip=(
                        "RGB or RGBA image batch to correct. RGBA alpha channels "
                        "are preserved unchanged."
                    ),
                ),
                io.Boolean.Input(
                    "force_gpu",
                    display_name="Use GPU",
                    default=True,
                    label_on="Enabled",
                    label_off="Disabled",
                    tooltip=(
                        "Enabled processes the image on ComfyUI's active GPU or "
                        "accelerator for better performance. Disabled performs "
                        "the correction on the CPU."
                    ),
                ),
                io.Boolean.Input(
                    "clamp",
                    display_name="Clamp Output",
                    default=True,
                    label_on="Enabled",
                    label_off="Disabled",
                    tooltip=(
                        "Enabled limits final RGB values to ComfyUI's normal 0–1 "
                        "image range. Disabled preserves values outside that range "
                        "for later high-dynamic-range processing."
                    ),
                ),
                io.Float.Input(
                    "gamma",
                    display_name="Gamma",
                    default=1.0,
                    min=0.0,
                    max=5.0,
                    step=0.01,
                    tooltip=(
                        "Nonlinear brightness adjustment. 1.0 leaves gamma "
                        "unchanged, values above 1.0 brighten midtones, and values "
                        "below 1.0 darken midtones."
                    ),
                ),
                io.Float.Input(
                    "contrast",
                    display_name="Contrast",
                    default=1.0,
                    min=0.0,
                    max=5.0,
                    step=0.01,
                    tooltip=(
                        "Multiplies RGB intensity after gamma and exposure. 1.0 is "
                        "unchanged, higher values strengthen differences, and lower "
                        "values flatten the image."
                    ),
                ),
                io.Float.Input(
                    "exposure",
                    display_name="Exposure",
                    default=0.0,
                    min=-5.0,
                    max=5.0,
                    step=0.01,
                    tooltip=(
                        "Adjusts brightness in photographic stops. 0 is unchanged; "
                        "+1 doubles RGB intensity and -1 halves it."
                    ),
                ),
                io.Float.Input(
                    "offset",
                    display_name="Offset",
                    default=0.0,
                    min=-5.0,
                    max=5.0,
                    step=0.01,
                    tooltip=(
                        "Adds a constant to every RGB channel after gamma, exposure, "
                        "and contrast. Positive values lift the image; negative "
                        "values lower it."
                    ),
                ),
                io.Float.Input(
                    "hue",
                    display_name="Hue",
                    default=0.0,
                    min=-0.5,
                    max=0.5,
                    step=0.01,
                    tooltip=(
                        "Rotates all colors around the hue wheel. 0 is unchanged; "
                        "+0.5 and -0.5 each produce a 180-degree rotation."
                    ),
                ),
                io.Float.Input(
                    "saturation",
                    display_name="Saturation",
                    default=1.0,
                    min=0.0,
                    max=5.0,
                    step=0.01,
                    tooltip=(
                        "Controls color intensity. 1.0 is unchanged, 0.0 produces "
                        "grayscale, and values above 1.0 make colors more vivid."
                    ),
                ),
                io.Float.Input(
                    "value",
                    display_name="Value",
                    default=1.0,
                    min=0.0,
                    max=5.0,
                    step=0.01,
                    tooltip=(
                        "Multiplies the HSV brightness component. 1.0 is unchanged, "
                        "0.0 produces black, and values above 1.0 brighten the image."
                    ),
                ),
                io.Mask.Input(
                    "mask",
                    display_name="Mask",
                    optional=True,
                    tooltip=(
                        "Optional binary selection mask. Pixels above 0 receive all "
                        "color corrections; pixels equal to 0 retain the original "
                        "image. A single mask is repeated across an image batch."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    "image",
                    display_name="Image",
                    tooltip="The corrected RGB or RGBA image batch.",
                )
            ],
            search_aliases=["Color Correction GPU", "Color Correct GPU", "MTB Color Correct"],
        )

    @classmethod
    def execute(
        cls,
        image: torch.Tensor,
        force_gpu: bool,
        clamp: bool,
        gamma: float,
        contrast: float,
        exposure: float,
        offset: float,
        hue: float,
        saturation: float,
        value: float,
        mask: torch.Tensor | None = None,
    ) -> io.NodeOutput:
        if image.shape[-1] < 3:
            raise ValueError("Color Correction requires an RGB or RGBA image.")
        device = model_management.get_torch_device() if force_gpu else torch.device("cpu")
        source = image.to(device)
        rgb = source[..., :3]
        model_management.throw_exception_if_processing_interrupted()
        safe_gamma = max(float(gamma), 1e-6)
        adjusted = rgb.clamp_min(0).pow(1.0 / safe_gamma)
        adjusted = adjusted * (2.0 ** exposure) * contrast + offset

        model_management.throw_exception_if_processing_interrupted()
        hsv = _rgb_to_hsv(adjusted)
        hsv = torch.stack(
            (
                (hsv[..., 0] + hue).remainder(1.0),
                hsv[..., 1] * saturation,
                hsv[..., 2] * value,
            ),
            dim=-1,
        )
        adjusted = _hsv_to_rgb(hsv)
        if clamp:
            adjusted = adjusted.clamp(0.0, 1.0)

        if mask is not None:
            if mask.ndim != 3 or mask.shape[1:3] != source.shape[1:3]:
                raise ValueError("Mask height and width must match the image.")
            if mask.shape[0] == 1 and source.shape[0] > 1:
                mask = mask.expand(source.shape[0], -1, -1)
            elif mask.shape[0] != source.shape[0]:
                raise ValueError("Mask batch must be 1 or match the image batch.")
            selector = mask.to(device=device).unsqueeze(-1) > 0
            adjusted = torch.where(selector, adjusted, rgb)

        result = adjusted if source.shape[-1] == 3 else torch.cat((adjusted, source[..., 3:]), dim=-1)
        return io.NodeOutput(result)

__all__ = ['ReaperColorCorrection']
