"""Discover node implementations from independently removable node modules."""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path


def discover_nodes(package_name: str, package_paths) -> tuple[list[type], dict[str, type]]:
    nodes: list[type] = []
    exports: dict[str, type] = {}
    for module_info in sorted(
        pkgutil.iter_modules(package_paths),
        key=lambda item: item.name.casefold(),
    ):
        if not module_info.name.startswith("node_"):
            continue
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        for name in getattr(module, "__all__", ()):
            value = getattr(module, name)
            if isinstance(value, type) and callable(getattr(value, "define_schema", None)):
                nodes.append(value)
                exports[name] = value
    return nodes, exports


__all__ = ["discover_nodes"]
