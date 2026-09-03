"""V3 definition for the frontend-driven Node Collector."""
from comfy_api.latest import io
from ..global_configs import CATEGORIES, node_title


class ReaperNodeCollector(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperNodeCollector",
            display_name=node_title("Node Collector"),
            category=CATEGORIES["utilities"],
            description="Collects multiple graph-control connections into one output.",
            accept_all_inputs=True,
            inputs=[io.AnyType.Input("node", optional=True)],
            outputs=[io.AnyType.Output(id="output", display_name="Output")],
        )

    @classmethod
    def execute(cls, node=None, **kwargs):
        return io.NodeOutput(node)


__all__ = ["ReaperNodeCollector"]
