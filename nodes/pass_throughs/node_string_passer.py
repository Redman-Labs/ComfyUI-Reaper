"""Node implementation: String Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

class ReaperStringPasser(_PassThrough):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperStringPasser", display_name=node_title('String Passer', branded=False), category=CATEGORY,
            inputs=[io.String.Input("input", force_input=True)],
            outputs=[io.String.Output(id="output")],
        )

__all__ = ['ReaperStringPasser']
