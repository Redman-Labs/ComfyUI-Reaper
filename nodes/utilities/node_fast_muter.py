"""V3 definition for the frontend-driven Fast Muter graph tool."""
from comfy_api.latest import io
from ..global_configs import CATEGORIES, node_title


class ReaperFastMuter(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperFastMuter",
            display_name=node_title("Fast Muter"),
            category=CATEGORIES["utilities"],
            description="Quickly mute or enable connected nodes without executing itself.",
            accept_all_inputs=True,
            inputs=[io.AnyType.Input("node", optional=True)],
            outputs=[io.AnyType.Output(id="control", display_name="CONTROL")],
        )

    @classmethod
    def execute(cls, node=None, **kwargs):
        return io.NodeOutput(node)


__all__ = ["ReaperFastMuter"]
