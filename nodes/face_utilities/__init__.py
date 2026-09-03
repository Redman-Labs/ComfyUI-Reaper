"""Auto-discovered node modules for this category."""
from .._discovery import discover_nodes

NODE_CLASSES, _NODE_EXPORTS = discover_nodes(__name__, __path__)
globals().update(_NODE_EXPORTS)

__all__ = ["NODE_CLASSES", *_NODE_EXPORTS]
