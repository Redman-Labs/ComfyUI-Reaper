"""Node implementation: Load VAE."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_vae_utilities._shared import *

CATEGORY = CATEGORIES['vae_utilities']
_CATEGORY = CATEGORY

class ReaperLoadVAE(io.ComfyNode):
    """Load a VAE through the current ComfyUI loader and set offload policy."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLoadVAE",
            display_name=node_title('Load VAE', branded=True),
            category=CATEGORY,
            description=(
                "Loads a VAE using ComfyUI's current native loader, including "
                "Wan video/upscale VAE channel detection, approximate TAEs, "
                "metadata handling, and device reload support. It also lets "
                "you choose whether the VAE stays fully loaded during use."
            ),
            search_aliases=[
                "VAE Utils Custom VAE Loader",
                "Load VAE VAE Utils",
                "Wan VAE loader",
                "Reaper VAE",
            ],
            inputs=[
                io.Combo.Input(
                    "vae_name",
                    options=_vae_names(),
                    display_name="VAE Name",
                    tooltip=(
                        "Select a VAE from ComfyUI's VAE folders or one of the "
                        "available approximate TAEs. The list is supplied by "
                        "the installed ComfyUI version so new native formats "
                        "remain available to this node."
                    ),
                ),
                io.Boolean.Input(
                    "disable_offload",
                    display_name="Disable Offload",
                    default=True,
                    label_on="Keep VAE loaded",
                    label_off="Allow offload",
                    tooltip=(
                        "When enabled, ComfyUI fully loads the VAE for encode "
                        "and decode operations instead of moving portions to "
                        "the offload device. This can improve consistency or "
                        "speed but may use substantially more VRAM."
                    ),
                ),
            ],
            outputs=[
                io.Vae.Output(
                    id="vae",
                    display_name="VAE",
                    tooltip=(
                        "The loaded native ComfyUI VAE with the selected "
                        "offload policy."
                    ),
                )
            ],
        )

    @classmethod
    def execute(cls, vae_name: str, disable_offload: bool) -> io.NodeOutput:
        vae = VAELoader().load_vae(vae_name)[0]
        vae.disable_offload = bool(disable_offload)
        return io.NodeOutput(vae)

__all__ = ['ReaperLoadVAE']
