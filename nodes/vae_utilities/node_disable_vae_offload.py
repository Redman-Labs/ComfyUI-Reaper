"""Node implementation: Disable VAE Offload."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_vae_utilities._shared import *

CATEGORY = CATEGORIES['vae_utilities']
_CATEGORY = CATEGORY

class ReaperDisableVAEOffload(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperDisableVAEOffload",
            display_name=node_title('Disable VAE Offload', branded=True),
            category=CATEGORY,
            description=(
                "Changes the offload policy of an already loaded VAE without "
                "modifying the VAE object used by other workflow branches."
            ),
            search_aliases=[
                "Disable VAE Offload VAE Utils",
                "keep VAE in VRAM",
                "VAE device memory",
            ],
            inputs=[
                io.Vae.Input(
                    "vae",
                    display_name="VAE",
                    tooltip="The loaded VAE whose offload policy will be copied and changed.",
                ),
                io.Boolean.Input(
                    "disable_offload",
                    display_name="Disable Offload",
                    default=True,
                    label_on="Keep VAE loaded",
                    label_off="Allow offload",
                    tooltip=(
                        "Enable to request a full VAE load during operations. "
                        "Disable to let ComfyUI use its normal offloading policy."
                    ),
                ),
            ],
            outputs=[
                io.Vae.Output(
                    id="vae",
                    display_name="VAE",
                    tooltip="A shallow VAE copy with the requested offload policy.",
                )
            ],
        )

    @classmethod
    def execute(cls, vae: Any, disable_offload: bool) -> io.NodeOutput:
        result = copy.copy(vae)
        result.disable_offload = bool(disable_offload)
        return io.NodeOutput(result)

__all__ = ['ReaperDisableVAEOffload']
