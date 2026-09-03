"""Node implementation: Pause Text."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_prompt_text_utilities._shared import *

CATEGORY = CATEGORIES['prompt_text_utilities']
_CATEGORY = CATEGORY

class ReaperPauseText(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperPauseText",
            display_name=node_title('Pause Text', branded=True),
            category=CATEGORY,
            description=(
                "Pauses a workflow so generated text can be reviewed and edited "
                "before downstream nodes run. Continue sends the edited text "
                "downstream while skipping its upstream generator. Regenerate "
                "requests fresh text, Pass runs end to end, and Keep reuses the "
                "current edited text on subsequent runs. The editor supports "
                "// line comments and /* block comments */; comments are removed "
                "from downstream output while markers inside quoted strings are "
                "preserved."
            ),
            search_aliases=[
                "pause text",
                "text gate",
                "edit generated prompt",
                "continue workflow",
                "Reaper",
            ],
            is_output_node=True,
            not_idempotent=True,
            accept_all_inputs=True,
            inputs=[
                io.String.Input(
                    "text",
                    optional=True,
                    force_input=True,
                    tooltip=(
                        "Text to review and gate. Connect an LLM, prompt "
                        "generator, or other STRING output. In Continue and Keep "
                        "modes the submitted prompt detaches this connection so "
                        "the upstream generator is skipped. Use // for line "
                        "comments and /* ... */ for block comments."
                    ),
                )
            ],
            outputs=[
                io.String.Output(
                    id="text",
                    display_name="Text",
                    tooltip=(
                        "Fresh upstream text in Pause or Pass mode, or the "
                        "reviewed and edited text in Continue or Keep mode. "
                        "Comments are removed, except comment markers contained "
                        "inside single- or double-quoted strings."
                    ),
                )
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> float:
        return float("nan")

    @staticmethod
    def _as_text(value: Any) -> str:
        if value is None:
            return ""
        return value if isinstance(value, str) else str(value)

    @classmethod
    def execute(
        cls,
        text: Any = None,
        PauseState: str = "",
        **kwargs,
    ) -> io.NodeOutput:
        try:
            state = json.loads(PauseState) if PauseState else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            state = {}
        if not isinstance(state, dict):
            state = {}

        mode = state.get("mode", "pause")
        edited_text = cls._as_text(state.get("text", ""))

        if mode in {"continue", "keep"}:
            return io.NodeOutput(remove_comments(edited_text))

        if text is not None:
            output = cls._as_text(text)
            return io.NodeOutput(
                remove_comments(output),
                ui={"reaper_pause_text": [output]},
            )

        return io.NodeOutput(remove_comments(edited_text))

__all__ = ['ReaperPauseText']
