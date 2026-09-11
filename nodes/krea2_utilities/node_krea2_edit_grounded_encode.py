"""Krea2 image-grounded instruction encoder for Reaper."""
from __future__ import annotations

import comfy.utils
from comfy_api.latest import io

from ..global_configs import CATEGORIES


class ReaperKrea2EditGroundedEncode(io.ComfyNode):
    """Training-matched semantic path for Krea2 image editing."""

    DEFAULT_SYSTEM = (
        "Describe the image by detailing the color, shape, size, "
        "texture, quantity, text, spatial relationships of the objects and background:"
    )

    @classmethod
    def _template(cls, image_count: int, system_prompt: str = "") -> str:
        selected_system = system_prompt.strip() or cls.DEFAULT_SYSTEM
        vision = (
            "<|vision_start|><|image_pad|><|vision_end|>" * image_count
        )
        return (
            "<|im_start|>system\n"
            + selected_system
            + "<|im_end|>\n<|im_start|>user\n"
            + vision
            + "{}<|im_end|>\n<|im_start|>assistant\n"
        )

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperKrea2EditGroundedEncode",
            display_name="Krea2 Edit (grounded encode)",
            category=CATEGORIES["krea2_utilities"],
            description=(
                "Encodes an edit instruction together with source imagery using "
                "Krea2's training-matched Qwen3-VL semantic path."
            ),
            inputs=[
                io.Clip.Input(
                    "clip",
                    display_name="CLIP",
                    tooltip="Krea2 text encoder containing the vision tower.",
                ),
                io.String.Input(
                    "prompt",
                    display_name="Prompt",
                    default="",
                    multiline=True,
                ),
                io.Image.Input(
                    "image",
                    display_name="Image",
                    optional=True,
                    tooltip=(
                        "Primary grounding image. If omitted, encoding is text-only."
                    ),
                ),
                io.Image.Input(
                    "image_b",
                    display_name="Image B",
                    optional=True,
                    tooltip=(
                        "Second subject reference for multi-reference LoRAs."
                    ),
                ),
                io.Int.Input(
                    "grounding_px",
                    display_name="Grounding Pixels",
                    optional=True,
                    default=768,
                    min=0,
                    max=4096,
                    step=64,
                    tooltip=(
                        "Caps the longest side sent to Qwen3-VL; 0 keeps native size."
                    ),
                ),
                io.String.Input(
                    "system_prompt",
                    display_name="System Prompt",
                    optional=True,
                    default="",
                    multiline=True,
                    tooltip=(
                        "Optional grounding-system override. Empty uses the "
                        "training default."
                    ),
                ),
            ],
            outputs=[
                io.Conditioning.Output(
                    id="conditioning",
                    display_name="Conditioning",
                    tooltip="Krea2 conditioning grounded on the source image(s).",
                )
            ],
        )

    @staticmethod
    def _prepare_image(image, grounding_px: int):
        samples = image.movedim(-1, 1)
        height, width = samples.shape[2], samples.shape[3]
        if grounding_px and max(height, width) > grounding_px:
            scale = grounding_px / max(height, width)
            samples = comfy.utils.common_upscale(
                samples,
                round(width * scale),
                round(height * scale),
                "area",
                "disabled",
            )
        return samples.movedim(1, -1)[..., :3]

    @classmethod
    def execute(
        cls,
        clip,
        prompt: str,
        image=None,
        image_b=None,
        grounding_px: int = 768,
        system_prompt: str = "",
        **_future,
    ) -> io.NodeOutput:
        if _future:
            print(
                "[Krea2 Edit (grounded encode)] WARNING: workflow provides "
                f"unknown inputs ({', '.join(sorted(_future))}). Update "
                "ComfyUI-Reaper and restart ComfyUI. Continuing without them.",
                flush=True,
            )
        if image is None:
            tokens = clip.tokenize(prompt)
            return io.NodeOutput(
                clip.encode_from_tokens_scheduled(tokens)
            )

        images = [cls._prepare_image(image, grounding_px)]
        if image_b is not None:
            images.append(cls._prepare_image(image_b, grounding_px))
        tokens = clip.tokenize(
            prompt,
            images=images,
            llama_template=cls._template(len(images), system_prompt),
        )
        return io.NodeOutput(clip.encode_from_tokens_scheduled(tokens))


__all__ = ["ReaperKrea2EditGroundedEncode"]
