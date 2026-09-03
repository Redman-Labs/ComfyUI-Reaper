"""Node implementation: VAE Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperVAESwitch(_TwoInputSwitch):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperVAESwitch",
            display_name=node_title('VAE Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects VAE 1 or VAE 2 and passes only the selected native "
                "ComfyUI VAE object to the output using lazy branch evaluation."
            ),
            search_aliases=[
                "Vae Switch",
                "VAE Switch RvTools",
                "choose VAE",
                "select autoencoder",
            ],
            inputs=_typed_inputs(io.Vae, "VAE"),
            outputs=_typed_output(io.Vae, "VAE"),
        )

__all__ = ['ReaperVAESwitch']
