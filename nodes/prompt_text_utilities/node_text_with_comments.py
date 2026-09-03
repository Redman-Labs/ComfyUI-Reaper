"""Node implementation: Text With Comments."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_prompt_text_utilities._shared import *

CATEGORY = CATEGORIES['prompt_text_utilities']
_CATEGORY = CATEGORY

class ReaperTextWithComments(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperTextWithComments",
            display_name=node_title('Text With Comments', branded=True),
            category=CATEGORY,
            description=(
                "Provides a multiline text field where // line comments and "
                "/* block comments */ can be used for notes. Comments are "
                "removed from the text sent to downstream nodes, while "
                "comment markers inside quoted strings are preserved."
            ),
            search_aliases=[
                "text with comments",
                "commented prompt",
                "remove comments",
                "strip comments",
                "multiline text",
                "Reaper",
            ],
            inputs=[
                io.String.Input(
                    "text",
                    default="",
                    multiline=True,
                    tooltip=(
                        "Enter prompt or text content. Use // for a line "
                        "comment or /* ... */ for a block comment. Comment "
                        "markers inside single or double quotes remain part "
                        "of the output."
                    ),
                )
            ],
            outputs=[
                io.String.Output(
                    id="text",
                    display_name="Text",
                    tooltip=(
                        "The entered text with // line comments and /* ... */ "
                        "block comments removed."
                    ),
                )
            ],
        )

    @classmethod
    def execute(cls, text: str = "") -> io.NodeOutput:
        value = text if isinstance(text, str) else str(text)
        return io.NodeOutput(remove_comments(value))

__all__ = ['ReaperTextWithComments']
