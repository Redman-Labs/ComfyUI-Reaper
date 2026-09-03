"""Node implementation: Model Tile Patch."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_model_utilities._shared import *

CATEGORY = CATEGORIES['model_utilities']
_CATEGORY = CATEGORY

class ReaperTileModelPatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperTileModelPatch",
            display_name=node_title('Model Tile Patch', branded=True),
            category=CATEGORY,
            description=(
                "Patches a diffusion model to evaluate its denoiser in "
                "overlapping temporal and spatial tiles, blend the results, "
                "and optionally base ComfyUI's memory estimate on one tile."
            ),
            search_aliases=[
                "Tile Model Patch VAE Utils",
                "tiled diffusion model",
                "Wan model tiling",
                "reduce model VRAM",
            ],
            inputs=[
                io.Model.Input(
                    "model",
                    display_name="Model",
                    tooltip="The diffusion model to clone and patch for tiled evaluation.",
                ),
                io.Int.Input(
                    "tile_t",
                    display_name="Temporal Tile",
                    default=13,
                    min=3,
                    step=1,
                    tooltip="Number of latent frames evaluated per temporal tile for 5D video latents.",
                ),
                io.Int.Input(
                    "tile_h",
                    display_name="Height Tile",
                    default=78,
                    min=32,
                    step=2,
                    tooltip="Latent-space height evaluated per spatial tile.",
                ),
                io.Int.Input(
                    "tile_w",
                    display_name="Width Tile",
                    default=78,
                    min=32,
                    step=2,
                    tooltip="Latent-space width evaluated per spatial tile.",
                ),
                io.Int.Input(
                    "min_overlap_t",
                    display_name="Temporal Overlap",
                    default=5,
                    min=1,
                    step=1,
                    tooltip="Minimum latent-frame overlap used to blend neighboring temporal tiles.",
                ),
                io.Int.Input(
                    "min_overlap_h",
                    display_name="Height Overlap",
                    default=16,
                    min=0,
                    step=2,
                    tooltip="Minimum latent-row overlap used to blend neighboring height tiles.",
                ),
                io.Int.Input(
                    "min_overlap_w",
                    display_name="Width Overlap",
                    default=16,
                    min=0,
                    step=2,
                    tooltip="Minimum latent-column overlap used to blend neighboring width tiles.",
                ),
                io.Int.Input(
                    "drop_first_t",
                    display_name="Drop First Temporal",
                    default=2,
                    min=0,
                    step=1,
                    tooltip=(
                        "Zeroes this many leading frames in each non-first "
                        "temporal tile before the remaining overlap is blended."
                    ),
                ),
                io.Boolean.Input(
                    "patch_memory_estimate",
                    display_name="Patch Memory Estimate",
                    default=True,
                    tooltip=(
                        "When enabled, model memory estimation uses the tile "
                        "shape instead of the full latent shape."
                    ),
                ),
            ],
            outputs=[
                io.Model.Output(
                    id="model",
                    display_name="Model",
                    tooltip="A cloned model with tiled denoiser evaluation installed.",
                )
            ],
        )

    @classmethod
    def execute(
        cls,
        model: Any,
        tile_t: int,
        tile_h: int,
        tile_w: int,
        min_overlap_t: int,
        min_overlap_h: int,
        min_overlap_w: int,
        drop_first_t: int,
        patch_memory_estimate: bool,
    ) -> io.NodeOutput:
        if min_overlap_t >= tile_t:
            raise ValueError("Temporal Overlap must be smaller than Temporal Tile.")
        if min_overlap_h >= tile_h:
            raise ValueError("Height Overlap must be smaller than Height Tile.")
        if min_overlap_w >= tile_w:
            raise ValueError("Width Overlap must be smaller than Width Tile.")

        patched_model = model.clone()

        def model_function_tile_wrapper(apply_model, args):
            tensor = args["input"]
            timestep = args["timestep"]
            conditioning = args["c"]
            concatenated = conditioning.get("c_concat")
            vace_context = conditioning.get("vace_context")

            if concatenated is not None and concatenated.shape[2:] != tensor.shape[2:]:
                raise ValueError(
                    f"c_concat shape {concatenated.shape} does not match "
                    f"latent shape {tensor.shape}."
                )

            temporal_tiles = (
                get_tiles(tensor.shape[-3], tile_t, min_overlap_t)
                if tensor.ndim == 5
                else None
            )
            height_tiles = get_tiles(tensor.shape[-2], tile_h, min_overlap_h)
            width_tiles = get_tiles(tensor.shape[-1], tile_w, min_overlap_w)
            temporal_count = len(temporal_tiles) if temporal_tiles else 1
            progress = comfy.utils.ProgressBar(
                temporal_count * len(height_tiles) * len(width_tiles)
            )

            output = torch.zeros_like(tensor)
            alpha = torch.zeros_like(tensor)

            for width_index, (width_start, width_end) in enumerate(width_tiles):
                for height_index, (height_start, height_end) in enumerate(height_tiles):
                    if temporal_tiles is None:
                        tile = tensor[..., height_start:height_end, width_start:width_end]
                        tile_conditioning = conditioning.copy()
                        if concatenated is not None:
                            tile_conditioning["c_concat"] = concatenated[
                                ..., height_start:height_end, width_start:width_end
                            ]
                        tile_output = apply_model(tile, timestep, **tile_conditioning)
                        mask_h = get_1d_mask(height_index, height_tiles).view(1, 1, -1, 1)
                        mask_w = get_1d_mask(width_index, width_tiles).view(1, 1, 1, -1)
                        mask = torch.ones_like(tile_output)
                        mask *= mask_h.to(device=mask.device, dtype=mask.dtype)
                        mask *= mask_w.to(device=mask.device, dtype=mask.dtype)
                        output[..., height_start:height_end, width_start:width_end] += tile_output * mask
                        alpha[..., height_start:height_end, width_start:width_end] += mask
                        progress.update(1)
                        continue

                    for temporal_index, (temporal_start, temporal_end) in enumerate(temporal_tiles):
                        tile = tensor[
                            ...,
                            temporal_start:temporal_end,
                            height_start:height_end,
                            width_start:width_end,
                        ]
                        tile_conditioning = conditioning.copy()
                        if concatenated is not None:
                            tile_conditioning["c_concat"] = concatenated[
                                ...,
                                temporal_start:temporal_end,
                                height_start:height_end,
                                width_start:width_end,
                            ]
                        if vace_context is not None:
                            tile_conditioning["vace_context"] = vace_context[
                                ...,
                                temporal_start:temporal_end,
                                height_start:height_end,
                                width_start:width_end,
                            ]

                        tile_output = apply_model(tile, timestep, **tile_conditioning)
                        mask_t = get_1d_mask(
                            temporal_index,
                            temporal_tiles,
                            drop_first_t,
                        ).view(1, 1, -1, 1, 1)
                        mask_h = get_1d_mask(height_index, height_tiles).view(1, 1, 1, -1, 1)
                        mask_w = get_1d_mask(width_index, width_tiles).view(1, 1, 1, 1, -1)
                        mask = torch.ones_like(tile_output)
                        mask *= mask_t.to(device=mask.device, dtype=mask.dtype)
                        mask *= mask_h.to(device=mask.device, dtype=mask.dtype)
                        mask *= mask_w.to(device=mask.device, dtype=mask.dtype)

                        destination = (
                            Ellipsis,
                            slice(temporal_start, temporal_end),
                            slice(height_start, height_end),
                            slice(width_start, width_end),
                        )
                        output[destination] += tile_output * mask
                        alpha[destination] += mask
                        progress.update(1)

            if alpha.min().item() <= 0:
                raise RuntimeError("Tiled model patch left part of the latent uncovered.")
            return output / alpha

        patched_model.set_model_unet_function_wrapper(
            model_function_tile_wrapper
        )

        def tiled_shape(shape: list[int] | tuple[int, ...]) -> list[int]:
            shape = list(shape)
            if len(shape) == 5:
                return shape[:2] + [tile_t, tile_h, tile_w]
            if len(shape) == 4:
                return shape[:2] + [tile_h, tile_w]
            return shape

        if patch_memory_estimate:
            original_memory_required = patched_model.model.memory_required

            def memory_required_wrapper(input_shape, cond_shapes=None):
                adjusted_conditions = dict(cond_shapes or {})
                for condition_name in patched_model.model.memory_usage_factor_conds:
                    condition_shape = adjusted_conditions.get(condition_name)
                    if condition_shape is not None:
                        adjusted_conditions[condition_name] = tiled_shape(condition_shape)
                return original_memory_required(
                    tiled_shape(input_shape), adjusted_conditions
                )

            patched_model.model.memory_required = memory_required_wrapper

        return io.NodeOutput(patched_model)

__all__ = ['ReaperTileModelPatch']
