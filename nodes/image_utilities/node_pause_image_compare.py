"""Node implementation: Pause Image Compare."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperPauseImageCompare(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperPauseImageCompare",
            display_name=node_title('Pause Image Compare', branded=True),
            category=_CATEGORY,
            description=(
                "Combines the Pause Image workflow gate with the interactive "
                "Image Compare viewer. Image 1 is the gated image: Pause "
                "captures it, Continue reloads the approved snapshot while "
                "skipping its upstream generation, Regenerate captures a new "
                "version, and Pass runs normally. Image 2 is a comparison "
                "reference and is never used as the pause snapshot. The Pause "
                "Image Copy, Save Disk, Save Output, and Open controls always "
                "operate on Image 1."
            ),
            search_aliases=[
                "image",
                "compare",
                "pause image compare",
                "before after approval",
                "image gate comparison",
                "compare before continue",
                "Reaper",
            ],
            is_output_node=True,
            not_idempotent=True,
            accept_all_inputs=True,
            hidden=[io.Hidden.unique_id],
            inputs=[
                io.Image.Input(
                    "image1",
                    display_name="Image 1",
                    optional=True,
                    tooltip=(
                        "Primary image controlled by the pause gate. Pause "
                        "captures and previews this image; Continue reloads its "
                        "snapshot and skips the upstream nodes that produced it. "
                        "All Pause Image copy, save, and open actions target "
                        "Image 1 exclusively."
                    ),
                ),
                io.Image.Input(
                    "image2",
                    display_name="Image 2",
                    optional=True,
                    tooltip=(
                        "Optional reference image shown as the second side of "
                        "the comparison viewer. It is not captured as the pause "
                        "snapshot and is not affected by Image 1 utility buttons."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Image 1",
                    tooltip=(
                        "The live Image 1 in Pause or Pass mode, or its approved "
                        "snapshot reloaded in Continue mode."
                    ),
                )
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> float:
        return float("nan")

    @staticmethod
    def _comparison_frames(
        image1: torch.Tensor | None,
        image2: torch.Tensor | None,
    ) -> list[dict]:
        present = [
            (slot, tensor)
            for slot, tensor in ((1, image1), (2, image2))
            if tensor is not None
        ]
        if not present:
            return []

        first = present[0][1]
        prefix = f"reaper_pause_compare_{uuid.uuid4().hex[:8]}"
        temp_directory = folder_paths.get_temp_directory()
        folder, filename, counter, subfolder, _ = (
            folder_paths.get_save_image_path(
                prefix,
                temp_directory,
                first[0].shape[1],
                first[0].shape[0],
            )
        )
        os.makedirs(folder, exist_ok=True)
        results = []

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

        return results

    @classmethod
    def execute(
        cls,
        image1: torch.Tensor | None = None,
        image2: torch.Tensor | None = None,
        PauseState: str = "",
        **kwargs,
    ) -> io.NodeOutput:
        try:
            state = json.loads(PauseState) if PauseState else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            state = {}
        if not isinstance(state, dict):
            state = {}

        mode = state.get("mode", "pause")
        snapshot_path = _snapshot_path(cls.hidden.unique_id)
        pause_frame = [
            {
                "filename": os.path.basename(snapshot_path),
                "subfolder": "",
                "type": "temp",
            }
        ]

        if mode == "continue":
            if not os.path.isfile(snapshot_path):
                raise RuntimeError(
                    "Pause Image Compare Reaper: the Image 1 snapshot has "
                    "expired. Press Run to pause again, then Continue."
                )
            try:
                with Image.open(snapshot_path) as snapshot:
                    output_image = _pil_to_tensor(snapshot)
            except Exception as error:
                raise RuntimeError(
                    "Pause Image Compare Reaper: the Image 1 snapshot "
                    "could not be read. Press Run to pause again."
                ) from error

            return io.NodeOutput(
                output_image,
                ui={
                    "reaper_pause_frame": pause_frame,
                    "images": cls._comparison_frames(output_image, image2),
                },
            )

        if image1 is None:
            raise RuntimeError(
                "Pause Image Compare Reaper: Image 1 is not connected."
            )

        saved = False
        try:
            _tensor_to_pil(image1[0]).save(snapshot_path, "PNG")
            saved = True
        except OSError as error:
            print(
                "[Pause Image Compare Reaper] Image 1 snapshot save "
                f"failed: {error}"
            )

        ui_payload = {
            "images": cls._comparison_frames(image1, image2),
        }
        if saved:
            workflow = None
            if isinstance(cls.hidden.extra_pnginfo, dict):
                workflow = cls.hidden.extra_pnginfo.get("workflow")
            pause_frame[0]["_reaper_meta"] = _json_safe(
                {
                    "prompt": cls.hidden.prompt,
                    "workflow": workflow,
                }
            )
            ui_payload["reaper_pause_frame"] = pause_frame

        return io.NodeOutput(image1, ui=ui_payload)

__all__ = ['ReaperPauseImageCompare']
