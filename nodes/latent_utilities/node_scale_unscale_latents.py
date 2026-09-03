"""Node implementation: Scale / Unscale Latents."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_latent_utilities._shared import *

CATEGORY = CATEGORIES['latent_utilities']
_CATEGORY = CATEGORY

class ReaperScaleLatents(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperScaleLatents",
            display_name=node_title('Scale / Unscale Latents', branded=True),
            category=CATEGORY,
            description=(
                "Applies or reverses the selected native ComfyUI latent "
                "format's scale and shift transformation while preserving the "
                "rest of the LATENT dictionary."
            ),
            search_aliases=[
                "Scale Unscale Latents VAE Utils",
                "latent normalization",
                "WanVideoWrapper latent rescale",
                "process in process out latent",
            ],
            inputs=[
                io.Latent.Input(
                    "latents",
                    display_name="Latents",
                    tooltip="The LATENT dictionary whose samples tensor will be transformed.",
                ),
                io.Combo.Input(
                    "direction",
                    options=["scale", "unscale"],
                    display_name="Direction",
                    default="scale",
                    tooltip=(
                        "Scale applies the format's process_in transformation; "
                        "Unscale applies process_out to reverse it."
                    ),
                ),
                io.Combo.Input(
                    "latent_type",
                    options=sorted(LATENT_FORMATS),
                    display_name="Latent Type",
                    tooltip=(
                        "Choose the native ComfyUI latent format whose scale "
                        "and shift constants should be used."
                    ),
                ),
            ],
            outputs=[
                io.Latent.Output(
                    id="latents",
                    display_name="Latents",
                    tooltip="A copied LATENT dictionary containing the transformed samples.",
                )
            ],
        )

    @classmethod
    def execute(
        cls,
        latents: dict[str, torch.Tensor],
        direction: str,
        latent_type: str,
    ) -> io.NodeOutput:
        result = copy.deepcopy(latents)
        try:
            latent_format = LATENT_FORMATS[latent_type]()
        except KeyError as error:
            raise ValueError(f"Unknown latent type: {latent_type}") from error

        if direction == "scale":
            result["samples"] = latent_format.process_in(result["samples"])
        elif direction == "unscale":
            result["samples"] = latent_format.process_out(result["samples"])
        else:
            raise ValueError(f"Unknown scale direction: {direction}")
        return io.NodeOutput(result)

__all__ = ['ReaperScaleLatents']
