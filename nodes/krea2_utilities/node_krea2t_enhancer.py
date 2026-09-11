"""Node implementation: Krea2T Enhancer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_krea2_utilities._shared import *

CATEGORY = CATEGORIES['krea2_utilities']
_CATEGORY = CATEGORY

class ReaperKrea2TEnhancer(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperKrea2TEnhancer",
            display_name=node_title('Krea2T Enhancer', branded=True),
            category=CATEGORY,
            description=(
                "Patches Krea2's text-fusion path during diffusion sampling to "
                "strengthen prompt-detail adherence. The patch targets Krea2's "
                "12 x 2560 text-conditioning layout and safely skips models "
                "that do not match it."
            ),
            search_aliases=[
                "Krea2T Enhancer",
                "ComfyUI-Krea2T-Enhancer",
                "Krea2 prompt adherence",
                "Krea2 utility",
                "Reaper",
            ],
            inputs=_enhancer_inputs(),
            outputs=_model_output(),
        )

    @classmethod
    def execute(
        cls,
        model,
        enabled: bool = True,
        strength: float = 1.0,
        debug: bool = False,
    ) -> io.NodeOutput:
        patched = model.clone()
        bounded_strength = _bounded_float(strength, 1.0, 0.0, 2.0)
        transformer_options = patched.model_options.setdefault(
            "transformer_options", {}
        )
        transformer_options[BASIC_CONFIG_KEY] = {
            "enabled": bool(enabled),
            "strength": bounded_strength,
            "debug": bool(debug),
            "max_debug_prints": 8,
        }
        _install_wrapper(patched, BASIC_WRAPPER_KEY, krea2t_enhancer_wrapper)
        if debug:
            print(
                "[ReaperKrea2TEnhancer] attached "
                f"enabled={bool(enabled)} strength={bounded_strength:.3f}"
            )
        return io.NodeOutput(patched)
__all__ = ['ReaperKrea2TEnhancer']
