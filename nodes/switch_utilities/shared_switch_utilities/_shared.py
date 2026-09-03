"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['switch_utilities']
_CATEGORY = CATEGORY

"""ComfyUI V3 switch nodes for the Reaper extension.

Adapted from comfyui-rvtools_v2 and consolidated into one node module.
"""

from typing import Any

from comfy_api.latest import io

import gc

import torch

import comfy.model_management

class _TwoInputSwitch(io.ComfyNode):
    """Shared lazy selection behavior for every typed switch."""

    @classmethod
    def check_lazy_status(
        cls,
        select_input: int,
        input_1: Any = None,
        input_2: Any = None,
    ) -> list[str]:
        if select_input == 1:
            return ["input_1"] if input_1 is None else []
        return ["input_2"] if input_2 is None else []

    @classmethod
    def execute(
        cls,
        select_input: int,
        input_1: Any = None,
        input_2: Any = None,
    ) -> io.NodeOutput:
        return io.NodeOutput(input_1 if select_input == 1 else input_2)

def _selector_input(noun: str) -> io.Int.Input:
    return io.Int.Input(
        "select_input",
        display_name="Select Input",
        default=1,
        min=1,
        max=2,
        step=1,
        display_mode=io.NumberDisplay.number,
        tooltip=(
            f"Choose which {noun.lower()} is passed to the output: 1 selects "
            f"{noun} 1 and 2 selects {noun} 2. Only the selected connected "
            "branch is evaluated."
        ),
    )

def _typed_inputs(data_type: type, noun: str) -> list[io.Input]:
    return [
        _selector_input(noun),
        data_type.Input(
            "input_1",
            display_name=f"{noun} 1",
            optional=True,
            lazy=True,
            tooltip=(
                f"The {noun.lower()} returned when Select Input is 1. This "
                "branch is evaluated lazily only when selected."
            ),
        ),
        data_type.Input(
            "input_2",
            display_name=f"{noun} 2",
            optional=True,
            lazy=True,
            tooltip=(
                f"The {noun.lower()} returned when Select Input is 2. This "
                "branch is evaluated lazily only when selected."
            ),
        ),
    ]

def _typed_output(data_type: type, noun: str) -> list[io.Output]:
    return [
        data_type.Output(
            id="output",
            display_name=noun,
            tooltip=(
                f"The selected {noun.lower()}. If the selected input is not "
                "connected, the output is empty."
            ),
        )
    ]

__all__ = [name for name in globals() if not name.startswith("__")]
