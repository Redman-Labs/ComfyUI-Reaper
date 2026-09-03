"""V3 definition for the Reaper flexible reroute."""
from comfy_api.latest import io
from ..global_configs import CATEGORIES, node_title


class ReaperReroute(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperReroute",
            display_name=node_title("Reroute"),
            category=CATEGORIES["utilities"],
            description="A compact, type-aware reroute with configurable connection direction.",
            inputs=[io.AnyType.Input("value")],
            outputs=[io.AnyType.Output(id="value", display_name="VALUE")],
        )

    @classmethod
    def execute(cls, value):
        return io.NodeOutput(value)


__all__ = ["ReaperReroute"]
