"""V3 definition for the frontend-driven Mute / Bypass Repeater."""
from comfy_api.latest import io
from ..global_configs import CATEGORIES, node_title


class ReaperMuteBypassRepeater(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperMuteBypassRepeater",
            display_name=node_title("Mute / Bypass Repeater"),
            category=CATEGORIES["utilities"],
            description="Repeats its Active, Muted, or Bypassed mode to connected nodes.",
            accept_all_inputs=True,
            inputs=[io.AnyType.Input("node", optional=True)],
            outputs=[io.AnyType.Output(id="control", display_name="CONTROL")],
        )

    @classmethod
    def execute(cls, node=None, **kwargs):
        return io.NodeOutput(node)


__all__ = ["ReaperMuteBypassRepeater"]
