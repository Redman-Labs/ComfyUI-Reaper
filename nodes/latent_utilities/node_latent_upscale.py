"""Node implementation: Latent Upscale."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_latent_utilities._shared import *

CATEGORY = CATEGORIES['latent_utilities']
_CATEGORY = CATEGORY

class ReaperLatentUpscale(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLatentUpscale",
            display_name=node_title('Latent Upscale', branded=True),
            category=CATEGORY,
            description=(
                "Upscales Wan 2.1 video latents by 2x spatially with the "
                "bundled compact neural latent upscaler while preserving all "
                "other keys in the LATENT dictionary."
            ),
            search_aliases=[
                "Latent Upscale VAE Utils",
                "Wan latent upscale",
                "Wan 2.1 latent 2x",
            ],
            inputs=[
                io.Latent.Input(
                    "samples",
                    display_name="Samples",
                    tooltip=(
                        "Wan 2.1 LATENT data containing a five-dimensional "
                        "[batch, 16, frames, height, width] samples tensor."
                    ),
                ),
                io.Combo.Input(
                    "model",
                    options=LATENT_UPSCALE_MODELS,
                    display_name="Model",
                    tooltip="Select the bundled neural latent upscaler.",
                ),
            ],
            outputs=[
                io.Latent.Output(
                    id="samples",
                    display_name="Upscaled Samples",
                    tooltip=(
                        "A copied LATENT dictionary whose spatial latent width "
                        "and height are doubled. Frame count is unchanged."
                    ),
                )
            ],
        )

    @classmethod
    def execute(
        cls, samples: dict[str, torch.Tensor], model: str
    ) -> io.NodeOutput:
        latents = samples["samples"]
        if latents.ndim != 5 or latents.shape[1] != 16:
            raise ValueError(
                "Wan latent upscale expects [batch, 16, frames, height, width], "
                f"but received {tuple(latents.shape)}."
            )

        device = comfy.model_management.get_torch_device()
        upscaler = load_latent_upscale_model(model).to(device)
        try:
            with torch.inference_mode():
                upscaled = upscaler(
                    latents.to(dtype=torch.float32, device=device)
                ).to(comfy.model_management.intermediate_device())
        finally:
            del upscaler

        result = copy.deepcopy(samples)
        result["samples"] = upscaled
        return io.NodeOutput(result)

__all__ = ['ReaperLatentUpscale']
