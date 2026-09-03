"""Node implementation: VAE Decode."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_vae_utilities._shared import *

CATEGORY = CATEGORIES['vae_utilities']
_CATEGORY = CATEGORY

class ReaperVAEDecode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperVAEDecode",
            display_name=node_title('VAE Decode', branded=True),
            category=CATEGORY,
            description=(
                "Decodes image or video latents with optional spatial and "
                "temporal tiling, then automatically rearranges packed VAE "
                "output channels for upscale VAEs such as the Wan 2x VAE."
            ),
            search_aliases=[
                "VAE Decode VAE Utils",
                "tiled VAE decode",
                "Wan upscale VAE decode",
                "latent to image",
            ],
            inputs=[
                io.Latent.Input(
                    "samples",
                    display_name="Samples",
                    tooltip=(
                        "Latent samples to decode. Image and video latent "
                        "tensors are supported when the connected VAE supports them."
                    ),
                ),
                io.Vae.Input(
                    "vae",
                    display_name="VAE",
                    tooltip="The VAE used to convert the latent samples into pixels.",
                ),
                io.Int.Input(
                    "upscale",
                    display_name="Post Upscale Factor",
                    default=-1,
                    min=-1,
                    max=16,
                    step=1,
                    tooltip=(
                        "Rearranges packed output channels with pixel shuffle. "
                        "Use -1 to detect the factor from the decoded channel "
                        "count, 1 for no rearrangement, or set a factor manually."
                    ),
                ),
                io.Boolean.Input(
                    "tile",
                    display_name="Use Tiled Decode",
                    default=False,
                    tooltip=(
                        "Decode in overlapping spatial and temporal tiles to "
                        "reduce peak VRAM use. Tiling is slower but useful for "
                        "large images or long videos."
                    ),
                ),
                io.Int.Input(
                    "tile_size",
                    display_name="Tile Size",
                    default=512,
                    min=64,
                    max=4096,
                    step=32,
                    advanced=True,
                    tooltip=(
                        "Spatial tile size in decoded pixels. It is converted "
                        "to latent units using the connected VAE's spatial compression."
                    ),
                ),
                io.Int.Input(
                    "overlap",
                    display_name="Tile Overlap",
                    default=64,
                    min=0,
                    max=4096,
                    step=32,
                    advanced=True,
                    tooltip=(
                        "Spatial overlap in decoded pixels. Overlap blends tile "
                        "edges; values above one quarter of Tile Size are safely reduced."
                    ),
                ),
                io.Int.Input(
                    "temporal_size",
                    display_name="Temporal Size",
                    default=4096,
                    min=8,
                    max=4096,
                    step=4,
                    advanced=True,
                    tooltip=(
                        "For video VAEs, the approximate number of decoded "
                        "frames handled at once. It is converted through the "
                        "VAE's temporal compression ratio."
                    ),
                ),
                io.Int.Input(
                    "temporal_overlap",
                    display_name="Temporal Overlap",
                    default=64,
                    min=4,
                    max=4096,
                    step=4,
                    advanced=True,
                    tooltip=(
                        "For video VAEs, the decoded-frame overlap between "
                        "temporal tiles. It is ignored by image-only VAEs."
                    ),
                ),
            ],
            outputs=[
                io.Image.Output(
                    id="image",
                    display_name="Image",
                    tooltip=(
                        "Decoded images in ComfyUI's [batch, height, width, "
                        "channels] layout. Video frames are flattened into the batch."
                    ),
                )
            ],
        )

    @staticmethod
    def _post_upscale(images: torch.Tensor, upscale: int) -> torch.Tensor:
        channels = int(images.shape[-1])
        if upscale < 1:
            if channels == 3:
                upscale = 1
            elif channels % 3 == 0:
                factor = math.isqrt(channels // 3)
                if factor * factor * 3 != channels:
                    raise ValueError(
                        "Could not infer a pixel-shuffle factor from "
                        f"{channels} decoded channels. Set Post Upscale Factor manually."
                    )
                upscale = factor
            else:
                raise ValueError(
                    "Could not infer a pixel-shuffle factor from "
                    f"{channels} decoded channels. Set Post Upscale Factor manually."
                )

        if upscale > 1:
            expected_multiple = 3 * upscale * upscale
            if channels % (upscale * upscale) != 0:
                raise ValueError(
                    f"Post Upscale Factor {upscale} is incompatible with "
                    f"{channels} decoded channels; expected a multiple of "
                    f"{expected_multiple} for RGB output."
                )
            images = F.pixel_shuffle(
                images.movedim(-1, 1), upscale_factor=upscale
            ).movedim(1, -1)
        return images

    @staticmethod
    def _decoded_channel_count(vae: Any) -> int:
        """Return the decoder's real channel count for packed-output VAEs."""
        return int(
            getattr(
                vae,
                "conv_out_channels",
                getattr(
                    vae,
                    "real_output_channels",
                    vae.output_channels,
                ),
            )
        )

    @classmethod
    def _decode_tiled_packed_channels(
        cls,
        vae: Any,
        latent: torch.Tensor,
        tile_x: int,
        tile_y: int,
        overlap: int,
        tile_t: int | None,
        overlap_t: int | None,
    ) -> torch.Tensor:
        """Decode a 3D VAE whose tiled output has more packed channels.

        ComfyUI 0.29.0's VAE.decode_tiled_3d allocates its accumulation
        buffer with ``output_channels``. Wan 2x VAEs intentionally report
        three image channels there while their decoder produces twelve packed
        channels for a later 2x pixel shuffle. Use ``conv_out_channels`` (or
        the older ``real_output_channels`` name) for that one tiled operation.
        """
        vae.throw_exception_if_invalid()
        memory_used = vae.memory_used_decode(latent.shape, vae.vae_dtype)
        comfy.model_management.load_models_gpu(
            [vae.patcher],
            memory_required=memory_used,
            force_full_load=vae.disable_offload,
        )

        temporal_tile = max(2, tile_t) if tile_t is not None else 999
        temporal_overlap = (
            max(1, overlap_t) if overlap_t is not None else 1
        )
        decoded_channels = cls._decoded_channel_count(vae)

        def decode_tile(tile: torch.Tensor) -> torch.Tensor:
            return vae.first_stage_model.decode(
                tile.to(device=vae.device, dtype=vae.vae_dtype)
            ).to(dtype=vae.vae_output_dtype())

        with (
            comfy.model_management.cuda_device_context(vae.device),
            torch.inference_mode(),
        ):
            output = comfy.utils.tiled_scale_multidim(
                latent,
                decode_tile,
                tile=(temporal_tile, tile_x, tile_y),
                overlap=(temporal_overlap, overlap, overlap),
                upscale_amount=vae.upscale_ratio,
                out_channels=decoded_channels,
                index_formulas=vae.upscale_index_formula,
                output_device=vae.output_device,
            )
            output = vae.process_output(output)
        return output.movedim(1, -1)

    @classmethod
    def execute(
        cls,
        samples: dict[str, torch.Tensor],
        vae: Any,
        upscale: int,
        tile: bool,
        tile_size: int,
        overlap: int,
        temporal_size: int,
        temporal_overlap: int,
    ) -> io.NodeOutput:
        latent = samples["samples"]
        if getattr(latent, "is_nested", False):
            latent = latent.unbind()[0]

        if tile_size < overlap * 4:
            overlap = tile_size // 4
        if temporal_size < temporal_overlap * 2:
            temporal_overlap = temporal_size // 2

        temporal_compression = vae.temporal_compression_decode()
        if temporal_compression is not None:
            temporal_size = max(2, temporal_size // temporal_compression)
            temporal_overlap = max(
                1,
                min(
                    temporal_size // 2,
                    temporal_overlap // temporal_compression,
                ),
            )
        else:
            temporal_size = None
            temporal_overlap = None

        if tile:
            compression = vae.spacial_compression_decode()
            tile_x = max(1, tile_size // compression)
            tile_y = max(1, tile_size // compression)
            latent_overlap = max(0, overlap // compression)
            decoded_channels = cls._decoded_channel_count(vae)
            if (
                latent.ndim == 5
                and not getattr(vae, "handles_tiling", False)
                and decoded_channels != int(vae.output_channels)
            ):
                images = cls._decode_tiled_packed_channels(
                    vae,
                    latent,
                    tile_x=tile_x,
                    tile_y=tile_y,
                    overlap=latent_overlap,
                    tile_t=temporal_size,
                    overlap_t=temporal_overlap,
                )
            else:
                images = vae.decode_tiled(
                    latent,
                    tile_x=tile_x,
                    tile_y=tile_y,
                    overlap=latent_overlap,
                    tile_t=temporal_size,
                    overlap_t=temporal_overlap,
                )
        else:
            images = vae.decode(latent)

        if images.ndim == 5:
            images = images.reshape(
                -1,
                images.shape[-3],
                images.shape[-2],
                images.shape[-1],
            )

        # Compatibility guard for VAE implementations that return raw [-1, 1]
        # pixels rather than applying process_output themselves.
        if images.numel() and images.min().item() < -0.1:
            images = ((images.float() + 1.0) / 2.0).clamp(0.0, 1.0)

        return io.NodeOutput(cls._post_upscale(images, int(upscale)))

__all__ = ['ReaperVAEDecode']
