"""Node implementation: Float Passer."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_pass_throughs._shared import *

CATEGORY = CATEGORIES['pass_throughs']
_CATEGORY = CATEGORY

class ReaperFloatPasser(_PassThrough):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperFloatPasser", display_name=node_title('Float Passer', branded=False), category=CATEGORY,
            inputs=[io.Float.Input("input", default=0.0, min=-3.4028235e38, max=3.4028235e38, step=0.01, force_input=True)],
            outputs=[io.Float.Output(id="output")],
        )

__all__ = ['ReaperFloatPasser']
