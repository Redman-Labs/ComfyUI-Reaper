"""Small shared definitions for the Reaper in/outpainting category."""
from comfy_api.latest import io

REAPER_CROP_INFO = io.Custom("REAPER_CROP_INFO")
REAPER_OUTPAINT_INFO = io.Custom("REAPER_OUTPAINT_INFO")


def node_output(value):
    """Convert the legacy processing return shape to a V3 NodeOutput."""
    if isinstance(value, dict):
        return io.NodeOutput(*value.get("result", ()), ui=value.get("ui"))
    if isinstance(value, tuple):
        return io.NodeOutput(*value)
    return io.NodeOutput(value)
