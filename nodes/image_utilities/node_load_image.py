"""Node implementation: Load Image."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperLoadImage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLoadImage",
            display_name=node_title('Load Image', branded=True),
            category=_CATEGORY,
            description=(
                "Loads still or multi-frame images from ComfyUI's input folder, "
                "extracts transparency as a mask, optionally resizes both, and "
                "emits a compact metadata bundle."
            ),
            inputs=[
                io.Combo.Input(
                    "image",
                    options=_image_files(),
                    upload=io.UploadType.image,
                    image_folder=io.FolderType.input,
                    tooltip="Image to load. Upload, paste, drag-and-drop, or select a file from the input folder.",
                ),
                io.String.Input(
                    "LoadImageMiniState",
                    default="",
                    advanced=True,
                    socketless=True,
                    tooltip="Internal state used by the compact settings panel.",
                ),
            ],
            outputs=[
                io.Image.Output("image", display_name="Image", tooltip="Loaded image batch after resizing."),
                ReaperImageInfo.Output("image_info", display_name="Image Info", tooltip="Typed bundle for Load Image Info (Reaper)."),
            ],
            search_aliases=["Load Image Mini Pixaroma", "import image", "open image"],
        )

    @classmethod
    def execute(cls, image: str, LoadImageMiniState: str = "") -> io.NodeOutput:
        path = folder_paths.get_annotated_filepath(image)
        source = node_helpers.pillow(Image.open, path)
        frames, masks = [], []
        source_size = None
        state = _parse_mini_state(LoadImageMiniState)
        try:
            from comfy import model_management
            dtype = model_management.intermediate_dtype()
        except Exception:
            dtype = torch.float32

        for frame in ImageSequence.Iterator(source):
            frame = node_helpers.pillow(ImageOps.exif_transpose, frame)
            rgb = frame.convert("RGB")
            if source_size is None:
                source_size = rgb.size
            if rgb.size != source_size:
                continue
            if "A" in frame.getbands() or (frame.mode == "P" and "transparency" in frame.info):
                alpha = np.asarray(frame.convert("RGBA").getchannel("A"), dtype=np.float32) / 255.0
                mask = Image.fromarray(np.uint8((1.0 - alpha) * 255), mode="L")
            else:
                mask = Image.new("L", rgb.size, 0)
            rgb, mask, _width, _height = _resize_frame(
                rgb, mask, state, source_size[0], source_size[1]
            )
            frames.append(torch.from_numpy(np.asarray(rgb, dtype=np.float32) / 255.0).to(dtype))
            masks.append(torch.from_numpy(np.asarray(mask, dtype=np.float32) / 255.0).to(dtype))
            if source.format == "MPO":
                break
        if not frames:
            loaded = torch.zeros((1, 64, 64, 3), dtype=dtype)
            mask_tensor = torch.zeros((1, 64, 64), dtype=dtype)
        else:
            loaded = torch.stack(frames)
            mask_tensor = torch.stack(masks)
        original_name = _parse_original_name(LoadImageMiniState)
        is_clipspace = "clipspace" in image.replace("\\", "/").lower()
        reported_path = original_name if is_clipspace and original_name else path
        filename = os.path.splitext(os.path.basename(reported_path.replace("\\", "/")))[0]
        info = {"image": loaded, "mask": mask_tensor, "width": int(loaded.shape[2]),
                "height": int(loaded.shape[1]), "filename": filename}
        return io.NodeOutput(loaded, info)

    @classmethod
    def fingerprint_inputs(cls, image: str, LoadImageMiniState: str = ""):
        path = folder_paths.get_annotated_filepath(image)
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            digest.update(handle.read())
        digest.update(json.dumps(_parse_mini_state(LoadImageMiniState), sort_keys=True).encode("utf-8"))
        digest.update(_parse_original_name(LoadImageMiniState).encode("utf-8"))
        return digest.hexdigest()

    @classmethod
    def validate_inputs(cls, image: str, **_kwargs):
        return True if folder_paths.exists_annotated_filepath(image) else f"Invalid image file: {image}"

__all__ = ['ReaperLoadImage']
