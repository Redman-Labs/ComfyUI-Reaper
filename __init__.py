from comfy_api.latest import ComfyExtension, io

from . import routes as _routes
from .nodes import ALL_REAPER_NODES


class ReaperExtension(ComfyExtension):
    """Registers every node included in the Reaper node collection."""

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return list(ALL_REAPER_NODES)


async def comfy_entrypoint() -> ReaperExtension:
    return ReaperExtension()
    

__all__ = [
    "ReaperExtension",
    "comfy_entrypoint",
    "WEB_DIRECTORY",
]


WEB_DIRECTORY = "./js"
