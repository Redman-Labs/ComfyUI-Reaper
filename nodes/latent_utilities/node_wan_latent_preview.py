"""Node implementation: Wan Latent Preview."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_latent_utilities._shared import *

CATEGORY = CATEGORIES['latent_utilities']
_CATEGORY = CATEGORY

class ReaperWanLatentPreview(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperWanLatentPreview",
            display_name=node_title('Wan Latent Preview', branded=True),
            category=CATEGORY,
            description=(
                "Creates a fast approximate RGB preview of Wan 2.1 latents "
                "with the bundled lightweight projector. This is for visual "
                "inspection and is not a replacement for full VAE decoding."
            ),
            search_aliases=[
                "Wan Latent Preview VAE Utils",
                "fast Wan preview",
                "Wan latent RGB",
            ],
            inputs=[
                io.Latent.Input(
                    "samples",
                    display_name="Samples",
                    tooltip=(
                        "Wan 2.1 LATENT data containing a five-dimensional "
                        "[batch, 16, frames, height, width] samples tensor."
                    ),
                )
            ],
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Preview",
                    tooltip=(
                        "Approximate RGB frames flattened into a ComfyUI image batch."
                    ),
                )
            ],
        )

    @classmethod
    def execute(cls, samples: dict[str, torch.Tensor]) -> io.NodeOutput:
        latents = samples["samples"]
        if latents.ndim != 5 or latents.shape[1] != 16:
            raise ValueError(
                "Wan latent preview expects [batch, 16, frames, height, width], "
                f"but received {tuple(latents.shape)}."
            )

        device = comfy.model_management.intermediate_device()
        projector = load_wan_latent_projector().to(device)
        try:
            with torch.inference_mode():
                pixels = projector(
                    latents.to(dtype=torch.float32, device=device)
                )
                pixels = pixels.mul(0.5).add(0.5)
                frames, height, width = pixels.shape[-3:]
                pixels = F.interpolate(
                    pixels,
                    size=(frames, max(1, height // 8), max(1, width // 8)),
                    mode="area",
                )
        finally:
            del projector

        pixels = torch.cat(
            [batch.movedim(0, -1) for batch in pixels], dim=0
        ).clamp(0.0, 1.0)
        return io.NodeOutput(pixels)

__all__ = ['ReaperWanLatentPreview']
