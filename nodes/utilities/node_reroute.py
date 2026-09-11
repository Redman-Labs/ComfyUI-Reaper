"""V3 metadata definition for the frontend-only Reaper reroute."""
from comfy_api.latest import io

from ..global_configs import CATEGORIES, node_title


class ReaperReroute(io.ComfyNode):
    """Expose the node to ComfyUI; JavaScript supplies its virtual behavior."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperReroute",
            display_name=node_title("Reroute", branded=False),
            category=CATEGORIES["utilities"],
            description=(
                "A frontend-only, type-aware reroute with configurable size, "
                "connection layout, label, rotation, and flipping."
            ),
            search_aliases=["Reaper Reroute", "rgthree reroute"],
            inputs=[io.AnyType.Input("value", optional=True)],
            outputs=[io.AnyType.Output(id="value", display_name="Value")],
        )

    @classmethod
    def execute(cls, value=None) -> io.NodeOutput:
        # The frontend marks this node virtual, so normal workflows bypass this
        # method. Keeping a passthrough makes API-only workflows fail safely.
        return io.NodeOutput(value)


__all__ = ["ReaperReroute"]
