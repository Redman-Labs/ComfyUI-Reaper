"""Reaper multi-LoRA loader (ComfyUI V3 schema)."""
from __future__ import annotations

import os
import threading

import comfy.sd
import comfy.utils
import folder_paths
from comfy_api.latest import io

from .._helpers import _lora_helpers as H
from ..global_configs import CATEGORIES, node_title


_NO_LORAS = "(put LoRAs in models/loras)"


class ReaperLoraLoader(io.ComfyNode):
    """Stack enabled LoRAs and emit the trigger words selected in the UI."""

    DESCRIPTION = (
        "Stack multiple LoRAs with independent model and CLIP strengths. The info "
        "panel can read local metadata, manage trigger words and previews, and "
        "optionally query Civitai when requested."
    )
    _cache: dict[str, tuple[object, object]] = {}
    # V3 executes through a locked clone of this class. Its mutable containers
    # may be updated, but assigning a class attribute (cls._last_path = ...)
    # raises AttributeError. Keep the cross-run pointer inside a mutable holder.
    _cache_state: dict[str, str | None] = {"last_path": None}
    _cache_lock = threading.RLock()

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLoraLoader",
            display_name=node_title("LoRA Loader"),
            category=CATEGORIES["model_utilities"],
            description=cls.DESCRIPTION,
            inputs=[
                io.Model.Input(
                    "model",
                    tooltip="Diffusion model to which every enabled LoRA is applied.",
                ),
                io.Clip.Input(
                    "clip",
                    optional=True,
                    tooltip="Optional CLIP encoder to which enabled LoRAs are applied.",
                ),
                io.String.Input("LoraLoaderState", default="{}", optional=True),
            ],
            outputs=[
                io.Model.Output(display_name="MODEL"),
                io.Clip.Output(display_name="CLIP"),
                io.String.Output(display_name="triggers"),
            ],
        )

    @classmethod
    def _get_lora(cls, path: str):
        with cls._cache_lock:
            cached = cls._cache.get(path)
            if cached is not None:
                return cached
            try:
                loaded = comfy.utils.load_torch_file(
                    path, safe_load=True, return_metadata=True
                )
            except TypeError:
                loaded = (comfy.utils.load_torch_file(path, safe_load=True), None)
            cls._cache[path] = loaded
            return loaded

    @classmethod
    def execute(cls, model, clip=None, LoraLoaderState="{}"):
        state = H.parse_state(LoraLoaderState)
        cache_mode = state.get("cacheMode", "last")
        last_this_run = None
        resolved = []
        used_paths = set()
        applied = 0

        with cls._cache_lock:
            for entry in state["loras"]:
                if not entry.get("on"):
                    continue
                name = entry["name"]
                if name == _NO_LORAS:
                    continue
                try:
                    path = folder_paths.get_full_path("loras", name)
                except Exception:
                    path = None
                if not path or not os.path.isfile(path):
                    print(f"[LoRA Loader Reaper] skipped (not found): {name}")
                    continue

                sm = float(entry.get("sm", 0.0))
                sc = float(entry.get("sc", 0.0)) if clip is not None else 0.0
                if sm == 0 and sc == 0:
                    used_paths.add(path)
                    resolved.append(entry)
                    continue
                try:
                    lora, metadata = cls._get_lora(path)
                    try:
                        model, clip = comfy.sd.load_lora_for_models(
                            model, clip, lora, sm, sc, lora_metadata=metadata
                        )
                    except TypeError:
                        model, clip = comfy.sd.load_lora_for_models(
                            model, clip, lora, sm, sc
                        )
                    used_paths.add(path)
                    resolved.append(entry)
                    applied += 1
                    if cache_mode != "all":
                        if last_this_run is not None and last_this_run != path:
                            cls._cache.pop(last_this_run, None)
                        last_this_run = path
                except Exception as exc:
                    print(f"[LoRA Loader Reaper] failed to apply {name}: {exc}")

            triggers = H.collect_triggers(
                {"loras": resolved, "sep": state.get("sep", ", ")}
            )
            if cache_mode == "none":
                cls._cache.clear()
                cls._cache_state["last_path"] = None
            elif cache_mode == "all":
                for path in list(cls._cache):
                    if path not in used_paths:
                        del cls._cache[path]
            else:
                keep = last_this_run
                previous = cls._cache_state.get("last_path")
                if keep is None and previous in used_paths:
                    keep = previous
                for path in list(cls._cache):
                    if path != keep:
                        del cls._cache[path]
                cls._cache_state["last_path"] = keep

        print(f"[LoRA Loader Reaper] applied {applied} LoRA(s).")
        return io.NodeOutput(model, clip, triggers)


__all__ = ["ReaperLoraLoader"]
