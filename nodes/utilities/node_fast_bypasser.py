"""V3 definition for the frontend-driven Fast Bypasser graph tool."""
from comfy_api.latest import io
from ..global_configs import CATEGORIES, node_title


class ReaperFastBypasser(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperFastBypasser",
            display_name=node_title("Fast Bypasser"),
            category=CATEGORIES["utilities"],
            description="Quickly bypass or enable connected nodes without executing itself.",
            accept_all_inputs=True,
            inputs=[io.AnyType.Input("node", optional=True)],
            outputs=[io.AnyType.Output(id="control", display_name="CONTROL")],
        )

    @classmethod
    def execute(cls, node=None, **kwargs):
        return io.NodeOutput(node)


__all__ = ["ReaperFastBypasser"]
