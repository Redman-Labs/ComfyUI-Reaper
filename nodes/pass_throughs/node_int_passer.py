"""Node implementation: Int Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

class ReaperIntPasser(_PassThrough):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperIntPasser", display_name=node_title('Int Passer', branded=False), category=CATEGORY,
            inputs=[io.Int.Input("input", default=0, min=-2147483648, max=2147483647, step=1, force_input=True)],
            outputs=[io.Int.Output(id="output")],
        )

__all__ = ['ReaperIntPasser']
