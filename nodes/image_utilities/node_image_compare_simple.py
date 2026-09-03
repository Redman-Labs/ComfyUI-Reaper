"""Node implementation: Image Compare Simple."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperCompareSimple(io.ComfyNode):

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperCompareSimple",
            display_name=node_title('Image Compare Simple', branded=False),
            description="Compares two images with a hover slider or click mode. Connect Image 1 and Image 2 to compare, or connect a single batch to auto-split.",
            category=_CATEGORY,
            is_output_node=True,
            is_input_list=True,
            inputs=[
                io.Image.Input(
                    "image_a",
                    display_name="Image 1",
                    optional=True,
                    tooltip="First image (left side). If only this is provided with a batch, the first two images are compared.",
                ),
                io.Image.Input(
                    "image_b",
                    display_name="Image 2",
                    optional=True,
                    tooltip="Second image (right side).",
                ),
            ],
            outputs=[
                io.Image.Output(
                    "image",
                    display_name="Image",
                    is_output_list=True,
                    tooltip="Returns the side selected as default (right-click → 'Default output: A/B'). Defaults to image_b (the new/result image), falling back to image_a if empty.",
                ),
            ],
            hidden=[io.Hidden.unique_id, io.Hidden.prompt, io.Hidden.extra_pnginfo],
        )

    @classmethod
    def execute(cls, image_a=None, image_b=None):
        # Since is_input_list=True, inputs arrive as lists of inputs.
        list_a = _flatten_comparer_images(image_a)
        list_b = _flatten_comparer_images(image_b)

        prompt = cls.hidden.prompt
        extra_pnginfo = cls.hidden.extra_pnginfo
        unique_id = cls.hidden.unique_id
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))

        ui_data = {"a_images": [], "b_images": []}

        if list_a:
            ui_data["a_images"] = _save_images_to_temp(list_a, "A", metadata)

        if list_b:
            ui_data["b_images"] = _save_images_to_temp(list_b, "B", metadata)

        # Default output side ("a" or "b") — read from node properties set via right-click menu.
        # Convention: image_b is typically the new/result image, image_a the original.
        # Defaults to "b" so downstream nodes receive the latest result. User can flip via right-click.
        default_side = "b"
        try:
            workflow = (
                (extra_pnginfo or {}).get("workflow")
                if isinstance(extra_pnginfo, dict)
                else None
            )
            if workflow:
                uid_str = unique_id
                for n in workflow.get("nodes", []):
                    if str(n.get("id")) == uid_str:
                        prop = (n.get("properties") or {}).get("default_output")
                        if prop in ("a", "b"):
                            default_side = prop
                        break
        except Exception:
            pass

        # Select output side based on default side setting
        # Use original tensors to preserve their exact shape and dimensions (3D vs 4D)
        def _extract_original_tensors(val):
            tensors = []
            if isinstance(val, (list, tuple)):
                for item in val:
                    tensors.extend(_extract_original_tensors(item))
            elif isinstance(val, torch.Tensor):
                tensors.append(val)
            return tensors

        orig_list_a = _extract_original_tensors(image_a) if image_a is not None else []
        orig_list_b = _extract_original_tensors(image_b) if image_b is not None else []

        a_ok = len(orig_list_a) > 0
        b_ok = len(orig_list_b) > 0
        if default_side == "a":
            output_list = orig_list_a if a_ok else orig_list_b
        else:
            output_list = orig_list_b if b_ok else orig_list_a

        if not output_list:
            empty_batch = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
            return io.NodeOutput([empty_batch], ui=ui_data)

        return io.NodeOutput(output_list, ui=ui_data)

__all__ = ['ReaperCompareSimple']
