"""Node implementation: Latent Switch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_switch_utilities._shared import *

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

class ReaperLatentSwitch(io.ComfyNode):
    """Return one of two optional LATENT inputs."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperLatentSwitch",
            display_name=node_title('Latent Switch', branded=True),
            category=CATEGORY,
            description=(
                "Selects Latent 1 or Latent 2 and passes only the selected "
                "LATENT value to the output. The inputs use lazy evaluation, "
                "so an unselected connected branch is not calculated. An "
                "optional purge can unload models and clear cached memory "
                "immediately before the selected latent is returned."
            ),
            search_aliases=[
                "Latent Switch",
                "Latent Switch V2",
                "Latent Switch v2 RvTools",
                "choose latent",
                "select latent input",
                "Reaper latent switch",
            ],
            inputs=[
                io.Int.Input(
                    "select_input",
                    display_name="Select Input",
                    default=1,
                    min=1,
                    max=2,
                    step=1,
                    display_mode=io.NumberDisplay.number,
                    tooltip=(
                        "Choose which latent is passed to the output: 1 selects "
                        "Latent 1 and 2 selects Latent 2. Only the selected "
                        "connected branch is evaluated."
                    ),
                ),
                io.Boolean.Input(
                    "purge_vram",
                    display_name="Purge VRAM",
                    default=False,
                    label_on="True",
                    label_off="False",
                    tooltip=(
                        "When enabled, requests that ComfyUI unload all loaded "
                        "models, runs Python garbage collection, and clears "
                        "available CUDA caches before returning the selected "
                        "latent. This may free VRAM but makes later model use "
                        "slower because the models must be loaded again."
                    ),
                ),
                io.Latent.Input(
                    "latent_1",
                    display_name="Latent 1",
                    optional=True,
                    lazy=True,
                    tooltip=(
                        "The LATENT value returned when Select Input is 1. This "
                        "branch is evaluated lazily only when it is selected."
                    ),
                ),
                io.Latent.Input(
                    "latent_2",
                    display_name="Latent 2",
                    optional=True,
                    lazy=True,
                    tooltip=(
                        "The LATENT value returned when Select Input is 2. This "
                        "branch is evaluated lazily only when it is selected."
                    ),
                ),
            ],
            outputs=[
                io.Latent.Output(
                    id="latent",
                    display_name="Latent",
                    tooltip=(
                        "The selected LATENT value. If the selected input is "
                        "not connected, the output is empty."
                    ),
                )
            ],
        )

    @classmethod
    def check_lazy_status(
        cls,
        select_input: int,
        purge_vram: bool,
        latent_1: Any = None,
        latent_2: Any = None,
    ) -> list[str]:
        del purge_vram
        if select_input == 1:
            return ["latent_1"] if latent_1 is None else []
        return ["latent_2"] if latent_2 is None else []

    @staticmethod
    def _purge_vram() -> None:
        comfy.model_management.unload_all_models()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except (RuntimeError, AssertionError):
                # CUDA IPC may be unavailable when no sharing pool is active.
                pass
        comfy.model_management.soft_empty_cache()

    @classmethod
    def execute(
        cls,
        select_input: int,
        purge_vram: bool,
        latent_1: dict[str, Any] | None = None,
        latent_2: dict[str, Any] | None = None,
    ) -> io.NodeOutput:
        if purge_vram:
            cls._purge_vram()
        return io.NodeOutput(latent_1 if select_input == 1 else latent_2)

__all__ = ['ReaperLatentSwitch']
