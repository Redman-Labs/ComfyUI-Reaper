"""Node implementation: Image Preview."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperImagePreview(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperImagePreview",
            display_name=node_title('Image Preview', branded=False),
            category=_CATEGORY,
            description=(
                "Displays an image or image batch in a resizable DOM preview "
                "and passes the images through unchanged."
            ),
            is_output_node=True,
            is_input_list=True,
            inputs=[
                io.Image.Input(
                    "images",
                    display_name="Images",
                    tooltip="Image or image batch to preview.",
                )
            ],
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Image",
                    is_output_list=True,
                    tooltip="The input images returned unchanged.",
                )
            ],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
        )

    @classmethod
    def execute(cls, images: Any) -> io.NodeOutput:
        flattened = _flatten_comparer_images(images)
        if not flattened:
            return io.NodeOutput([], ui={"images": []})

        first = flattened[0]
        height, width = int(first.shape[1]), int(first.shape[2])
        metadata = PngInfo()
        prompt = cls.hidden.prompt
        extra_pnginfo = cls.hidden.extra_pnginfo
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if isinstance(extra_pnginfo, dict):
            for key, value in extra_pnginfo.items():
                metadata.add_text(key, json.dumps(value))

        folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            "ReaperPreview" + _IMAGE_PREVIEW_PREFIX,
            _IMAGE_PREVIEW_OUTPUT_DIR,
            width,
            height,
        )
        results = []
        progress = comfy.utils.ProgressBar(len(flattened))
        for batch_number, image in enumerate(flattened):
            frame = image[0] if image.dim() == 4 and image.shape[0] == 1 else image
            array = np.clip(255.0 * frame.detach().cpu().numpy(), 0, 255).astype(np.uint8)
            preview = Image.fromarray(array)
            numbered = filename.replace("%batch_num%", str(batch_number))
            timestamp = int(time.time() * 1000) % 100000000
            output_name = f"{numbered}_{counter:05}_{timestamp}_.png"
            preview.save(
                os.path.join(folder, output_name),
                pnginfo=metadata,
                compress_level=1,
            )
            results.append(
                {"filename": output_name, "subfolder": subfolder, "type": "temp"}
            )
            counter += 1
            progress.update(1)

        return io.NodeOutput(flattened, ui={"images": results})

__all__ = ['ReaperImagePreview']
