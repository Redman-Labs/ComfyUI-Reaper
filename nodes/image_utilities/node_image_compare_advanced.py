"""Node implementation: Image Compare Advanced."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperCompare(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperCompareAdvanced",
            display_name=node_title('Image Compare Advanced', branded=True),
            category=_CATEGORY,
            description=(
                "Displays two images in an interactive on-node viewer with "
                "single-image, left/right wipe, reversed wipe, up/down wipe, "
                "opacity overlay, and pixel-difference modes. Either input may "
                "be omitted without causing an execution error."
            ),
            search_aliases=[
                "image",
                "compare",
                "image compare",
                "before after",
                "difference viewer",
                "image slider",
                "Reaper",
            ],
            is_output_node=True,
            not_idempotent=True,
            inputs=[
                io.Image.Input(
                    "image1",
                    display_name="Image 1",
                    optional=True,
                    tooltip=(
                        "First comparison image, typically the original or "
                        "before image. If only this input is connected, the "
                        "viewer displays it by itself."
                    ),
                ),
                io.Image.Input(
                    "image2",
                    display_name="Image 2",
                    optional=True,
                    tooltip=(
                        "Second comparison image, typically the processed or "
                        "after image. If only this input is connected, the "
                        "viewer displays it by itself."
                    ),
                ),
            ],
            outputs=[],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> float:
        return float("nan")

    @classmethod
    def execute(cls, image1=None, image2=None) -> io.NodeOutput:
        present = [
            (slot, tensor)
            for slot, tensor in ((1, image1), (2, image2))
            if tensor is not None
        ]
        results = []

        if present:
            first = present[0][1]
            prefix = f"reaper_compare_{uuid.uuid4().hex[:8]}"
            output_directory = folder_paths.get_temp_directory()
            folder, filename, counter, subfolder, _ = (
                folder_paths.get_save_image_path(
                    prefix,
                    output_directory,
                    first[0].shape[1],
                    first[0].shape[0],
                )
            )
            os.makedirs(folder, exist_ok=True)

            for slot, tensor in present:
                array = 255.0 * tensor[0].detach().cpu().numpy()
                image = Image.fromarray(
                    np.clip(array, 0, 255).astype(np.uint8)
                )
                saved_name = f"{filename}_{counter:05}_.png"
                image.save(
                    os.path.join(folder, saved_name),
                    compress_level=4,
                )
                results.append(
                    {
                        "filename": saved_name,
                        "subfolder": subfolder,
                        "type": "temp",
                        "slot": slot,
                    }
                )
                counter += 1

        return io.NodeOutput(ui={"images": results})

__all__ = ['ReaperCompare']
