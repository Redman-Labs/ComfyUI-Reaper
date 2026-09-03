"""Find and Replace node with a rich rule-editing frontend."""
from __future__ import annotations

import json

from comfy_api.latest import io

from ..global_configs import CATEGORIES, node_title
from .shared_prompt_text_utilities.find_replace import _PREVIEW_CAP, _apply_rules

CATEGORY = CATEGORIES["prompt_text_utilities"]


class ReaperFindReplace(io.ComfyNode):
    """Apply an ordered collection of literal or regular-expression edits."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperFindReplace",
            display_name=node_title("Find and Replace", branded=True),
            category=CATEGORY,
            description=(
                "Intercepts connected text, applies an ordered list of find-and-replace "
                "rules, and passes the edited text downstream. The interactive node UI "
                "supports adding, disabling, deleting, and dragging rules; case-sensitive, "
                "whole-word, regular-expression, and tidy modes; and a persistent live "
                "before-and-after preview. Rules run from top to bottom, so each rule sees "
                "the result produced by the preceding rule."
            ),
            search_aliases=[
                "Find and Replace Pixaroma",
                "search replace text",
                "regex replace",
                "prompt replacement",
            ],
            is_output_node=True,
            inputs=[
                io.String.Input(
                    "text",
                    display_name="Text",
                    force_input=True,
                    tooltip=(
                        "The source text to edit. Connect any STRING output here. The "
                        "original upstream value is not modified; only this node's output "
                        "contains the replacements."
                    ),
                ),
                io.String.Input(
                    "FindReplaceState",
                    display_name="Find and Replace State",
                    default="{}",
                    optional=True,
                    advanced=True,
                    tooltip=(
                        "Serialized rules and global matching options maintained by the "
                        "interactive editor. The frontend hides and updates this internal "
                        "field automatically; it is exposed in the schema for workflow and "
                        "API compatibility."
                    ),
                ),
            ],
            outputs=[
                io.String.Output(
                    id="text",
                    display_name="Text",
                    tooltip=(
                        "The complete edited text after every enabled rule has run in order "
                        "and optional whitespace/comma tidying has been applied."
                    ),
                )
            ],
        )

    @classmethod
    def execute(cls, text: str, FindReplaceState: str = "{}") -> io.NodeOutput:
        source = text if isinstance(text, str) else ("" if text is None else str(text))
        try:
            parsed = json.loads(FindReplaceState) if isinstance(FindReplaceState, str) else {}
            state = parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            state = {}

        result, warnings = _apply_rules(source, state)
        ui = {
            "pixaroma_find_replace": [
                {
                    "input": source[:_PREVIEW_CAP],
                    "output": result[:_PREVIEW_CAP],
                    "truncated": (
                        len(source) > _PREVIEW_CAP or len(result) > _PREVIEW_CAP
                    ),
                    "warnings": warnings,
                }
            ]
        }
        return io.NodeOutput(result, ui=ui)


__all__ = ["ReaperFindReplace"]
