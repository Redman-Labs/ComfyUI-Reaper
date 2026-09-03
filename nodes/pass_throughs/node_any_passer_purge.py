"""Node implementation: Any Passer Purge."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

class ReaperAnyPasserPurge(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("input", [io.AnyType])
        return io.Schema(
            node_id="ReaperAnyPasserPurge",
            display_name=node_title('Any Passer Purge', branded=False),
            category=CATEGORY,
            description="Optionally unloads models and clears ComfyUI's cache, then passes any datatype through unchanged.",
            search_aliases=["Any Passer Purge", "purge VRAM pass through", "Reaper"],
            is_input_list=True,
            inputs=[
                io.MatchType.Input("input", template=template),
                io.Boolean.Input(
                    "purge_vram",
                    display_name="Purge VRAM",
                    default=False,
                    tooltip="Unload all models and empty ComfyUI's cache before passing the value.",
                ),
            ],
            outputs=[io.MatchType.Output(template, id="output", is_output_list=True)],
        )

    @classmethod
    def execute(cls, input: Any, purge_vram: Any) -> io.NodeOutput:
        should_purge = purge_vram[0] if isinstance(purge_vram, list) and purge_vram else False
        if should_purge:
            comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()
        if input is None or not input or all(item is None for item in input):
            return io.NodeOutput([None])
        return io.NodeOutput(input)

__all__ = ['ReaperAnyPasserPurge']
