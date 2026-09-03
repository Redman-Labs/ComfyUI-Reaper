"""Node implementation: Pause Image."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperPauseImage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperPauseImage",
            display_name=node_title('Pause Image', branded=False),
            category=_CATEGORY,
            description=(
                "An inline image gate for inspecting a generated image before "
                "running expensive downstream work. Pause captures and previews "
                "the image, Continue reloads that exact snapshot while skipping "
                "upstream generation, Regenerate captures a new image, and Pass "
                "runs the full workflow normally. Snapshots live in ComfyUI's "
                "temporary folder and expire when that folder is cleared."
            ),
            search_aliases=[
                "pause image",
                "image gate",
                "continue workflow",
                "preview before upscale",
                "Reaper",
            ],
            is_output_node=True,
            not_idempotent=True,
            accept_all_inputs=True,
            hidden=[io.Hidden.unique_id],
            inputs=[
                io.Image.Input(
                    "image",
                    optional=True,
                    tooltip=(
                        "Image to inspect and gate. In Pause or Pass mode the "
                        "live image is captured and passed through unchanged. "
                        "In Continue mode the frontend disconnects this input "
                        "from the submitted prompt so upstream nodes are skipped."
                    ),
                )
            ],
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Image",
                    tooltip=(
                        "The live image in Pause or Pass mode, or the saved "
                        "snapshot reloaded in Continue mode."
                    ),
                )
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> float:
        return float("nan")

    @classmethod
    def execute(
        cls,
        image: torch.Tensor | None = None,
        PauseState: str = "",
        **kwargs,
    ) -> io.NodeOutput:
        try:
            state = json.loads(PauseState) if PauseState else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            state = {}

        mode = state.get("mode", "pause")
        snapshot_path = _snapshot_path(cls.hidden.unique_id)
        frame = [
            {
                "filename": os.path.basename(snapshot_path),
                "subfolder": "",
                "type": "temp",
            }
        ]

        if mode == "continue":
            if not os.path.isfile(snapshot_path):
                raise RuntimeError(
                    "Pause Image Reaper: the snapshot has expired. Press "
                    "Run to pause again, then Continue."
                )
            try:
                with Image.open(snapshot_path) as snapshot:
                    output = _pil_to_tensor(snapshot)
            except Exception as error:
                raise RuntimeError(
                    "Pause Image Reaper: the snapshot could not be read. "
                    "Press Run to pause again, then Continue."
                ) from error
            return io.NodeOutput(
                output,
                ui={"reaper_pause_frame": frame},
            )

        if image is None:
            raise RuntimeError(
                "Pause Image Reaper: no image is connected to the input."
            )

        saved = False
        try:
            _tensor_to_pil(image[0]).save(snapshot_path, "PNG")
            saved = True
        except OSError as error:
            print(f"[Pause Image Reaper] snapshot save failed: {error}")

        ui_payload = {}
        if saved:
            workflow = None
            if isinstance(cls.hidden.extra_pnginfo, dict):
                workflow = cls.hidden.extra_pnginfo.get("workflow")
            frame[0]["_reaper_meta"] = _json_safe(
                {
                    "prompt": cls.hidden.prompt,
                    "workflow": workflow,
                }
            )
            ui_payload["reaper_pause_frame"] = frame

        return io.NodeOutput(image, ui=ui_payload)

__all__ = ['ReaperPauseImage']
