"""Node implementation: Krea2T Enhancer Advanced."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_model_utilities._shared import *

CATEGORY = CATEGORIES['model_utilities']
_CATEGORY = CATEGORY

class ReaperKrea2TEnhancerAdvanced(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperKrea2TEnhancerAdvanced",
            display_name=node_title('Krea2T Enhancer Advanced', branded=True),
            category=CATEGORY,
            description=(
                "Applies the Krea2T prompt-adherence enhancement and adds a "
                "direct post-txtmlp Text Scale control for fused text-token "
                "strength. All temporary runtime method patches are restored "
                "after each model call."
            ),
            search_aliases=[
                "Krea2T Enhancer Advanced",
                "Krea2 text scale",
                "Krea2 prompt adherence advanced",
                "Krea2 utility",
                "Reaper",
            ],
            inputs=_enhancer_inputs(include_text_scale=True),
            outputs=_model_output(),
        )

    @classmethod
    def execute(
        cls,
        model,
        enabled: bool = True,
        strength: float = 1.0,
        text_scale: float = 1.0,
        debug: bool = False,
    ) -> io.NodeOutput:
        patched = model.clone()
        bounded_strength = _bounded_float(strength, 1.0, 0.0, 2.0)
        bounded_text_scale = _bounded_float(text_scale, 1.0, 0.25, 4.0)
        transformer_options = patched.model_options.setdefault(
            "transformer_options", {}
        )
        transformer_options[ADVANCED_CONFIG_KEY] = {
            "enabled": bool(enabled),
            "strength": bounded_strength,
            "text_scale": bounded_text_scale,
            "debug": bool(debug),
        }
        _install_wrapper(
            patched,
            ADVANCED_WRAPPER_KEY,
            krea2t_enhancer_advanced_wrapper,
        )
        if debug:
            print(
                "[ReaperKrea2TEnhancerAdvanced] attached "
                f"enabled={bool(enabled)} strength={bounded_strength:.3f} "
                f"text_scale={bounded_text_scale:.3f}"
            )
        return io.NodeOutput(patched)

__all__ = ['ReaperKrea2TEnhancerAdvanced']
