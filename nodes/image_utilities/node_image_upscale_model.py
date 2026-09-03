"""Node implementation: Image Upscale w/wo Model."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperImageUpscale(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperImageUpscale",
            display_name=node_title('Image Upscale w/wo Model', branded=True),
            category=_CATEGORY,
            description="Load an upscale model and apply it to the image in one node. "
            "Optionally rescale the output to a target multiplier using a standard "
            "resampling filter (e.g. use a 4× model but produce 2× output).",
            is_input_list=True,
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input(
                    "model_name",
                    options=["None"] + folder_paths.get_filename_list("upscale_models"),
                    default="None",
                    tooltip="Upscale model from models/upscale_models/. "
                    "Models run at their native scale (e.g. 4× for RealESRGAN x4).",
                ),
                io.Float.Input(
                    "upscale_by",
                    default=0.0,
                    min=0.0,
                    max=16.0,
                    step=0.25,
                    tooltip="Target output multiplier relative to the original input size. "
                    "0.0 = keep the model's native output (e.g. 4× for a 4× model). "
                    "Any other value rescales the model output to the exact target dimensions.",
                ),
                io.Combo.Input(
                    "resampling",
                    options=_RESAMPLE_OPTIONS,
                    default="lanczos",
                    tooltip="Resampling filter used for the optional post-model rescale step. "
                    "Only applied when upscale_by > 0 and target size differs from model output.",
                ),
                io.Int.Input(
                    "resolution_steps",
                    default=8,
                    min=1,
                    max=256,
                    step=1,
                    tooltip="Round target width and height to the nearest multiple of this value. "
                    "VAE compatibility requires multiples of 8; some models/architectures require 64.",
                ),
                io.Boolean.Input(
                    "sharpen_enabled",
                    default=False,
                    tooltip="Enable post-upscale Smart Sharpen filter (using bilateral filtering and contrast sharpness).",
                ),
                io.Float.Input(
                    "sharpen_amount",
                    default=5.0,
                    min=0.0,
                    max=25.0,
                    step=0.5,
                    tooltip="Amount of sharpness enhancement to apply.",
                ),
                io.Float.Input(
                    "sharpen_ratio",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.1,
                    tooltip="Blending ratio between the sharpened image and bilateral-blurred image (1.0 = purely sharpened, 0.0 = purely blurred).",
                ),
                io.Int.Input(
                    "noise_radius",
                    default=7,
                    min=1,
                    max=25,
                    step=1,
                    tooltip="Bilateral filter noise reduction radius. Set to 1 to disable noise reduction blur.",
                ),
                io.Float.Input(
                    "preserve_edges",
                    default=0.75,
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    tooltip="Edge preservation threshold (higher = keep more sharp edges during noise reduction).",
                ),
            ],
            outputs=[
                io.Image.Output("image", is_output_list=True),
            ],
        )

    @classmethod
    def execute(
        cls,
        image,
        model_name,
        upscale_by,
        resampling,
        resolution_steps=8,
        sharpen_enabled=False,
        sharpen_amount=5.0,
        sharpen_ratio=0.5,
        noise_radius=7,
        preserve_edges=0.75,
    ) -> io.NodeOutput:
        model_name = _filter_unwrap_value(model_name)
        upscale_by = _filter_unwrap_value(upscale_by, 0.0)
        resampling = _filter_unwrap_value(resampling, "lanczos")
        resolution_steps = _filter_unwrap_value(resolution_steps, 8)
        sharpen_enabled = _filter_unwrap_value(sharpen_enabled, False)
        sharpen_amount = _filter_unwrap_value(sharpen_amount, 5.0)
        sharpen_ratio = _filter_unwrap_value(sharpen_ratio, 0.5)
        noise_radius = _filter_unwrap_value(noise_radius, 7)
        preserve_edges = _filter_unwrap_value(preserve_edges, 0.75)

        resolution_steps = max(1, resolution_steps)

        flat_image = _flatten_comparer_images(image)
        if not flat_image:
            raise ValueError("Upscale model v2: No images provided in input.")

        was_batch = _filter_was_input_batch(image)
        upscaled_list = []

        if model_name in (None, "None", ""):
            # We do the upscale without the model with the given values.
            for img in flat_image:
                if upscale_by > 0.0:
                    H_in, W_in = img.shape[1], img.shape[2]
                    target_w = max(
                        1,
                        round(W_in * upscale_by / resolution_steps) * resolution_steps,
                    )
                    target_h = max(
                        1,
                        round(H_in * upscale_by / resolution_steps) * resolution_steps,
                    )
                    if target_w != W_in or target_h != H_in:
                        s = comfy.utils.common_upscale(
                            img.movedim(-1, 1),
                            target_w,
                            target_h,
                            resampling,
                            "disabled",
                        ).movedim(1, -1)
                    else:
                        s = img
                else:
                    s = img

                s = _apply_sharpen(
                    s,
                    sharpen_enabled,
                    sharpen_amount,
                    sharpen_ratio,
                    noise_radius,
                    preserve_edges,
                )
                upscaled_list.append(s)
        else:
            # --- Load model ---
            model_path = folder_paths.get_full_path_or_raise(
                "upscale_models", model_name
            )
            sd = comfy.utils.load_torch_file(model_path, safe_load=True)
            if "module.layers.0.residual_group.blocks.0.norm1.weight" in sd:
                sd = comfy.utils.state_dict_prefix_replace(sd, {"module.": ""})
            upscale_model = ModelLoader().load_from_state_dict(sd).eval()
            if not isinstance(upscale_model, ImageModelDescriptor):
                raise ValueError(
                    "Upscale model must be a single-image model (ImageModelDescriptor)."
                )

            device = model_management.get_torch_device()
            upscale_model.to(device)

            try:
                for img in flat_image:
                    # --- Run tiled model inference ---
                    memory_required = model_management.module_size(
                        upscale_model.model
                    )
                    memory_required += (
                        (512 * 512 * 3)
                        * img.element_size()
                        * max(upscale_model.scale, 1.0)
                        * 384.0
                    )
                    memory_required += img.nelement() * img.element_size()
                    model_management.free_memory(memory_required, device)

                    in_img = img.movedim(-1, -3).to(
                        device
                    )  # [1, H, W, C] → [1, C, H, W]

                    tile = 512
                    overlap = 32
                    output_device = model_management.intermediate_device()
                    oom = True
                    s = None
                    while oom:
                        try:
                            steps = in_img.shape[0] * comfy.utils.get_tiled_scale_steps(
                                in_img.shape[3],
                                in_img.shape[2],
                                tile_x=tile,
                                tile_y=tile,
                                overlap=overlap,
                            )
                            pbar = comfy.utils.ProgressBar(steps)
                            s = comfy.utils.tiled_scale(
                                in_img,
                                lambda a: upscale_model(a.float()),
                                tile_x=tile,
                                tile_y=tile,
                                overlap=overlap,
                                upscale_amount=upscale_model.scale,
                                pbar=pbar,
                                output_device=output_device,
                            )
                            oom = False
                        except Exception as e:
                            model_management.raise_non_oom(e)
                            tile //= 2
                            if tile < 128:
                                raise e

                    if s is None:
                        raise RuntimeError(
                            "Upscaling failed: output tensor is uninitialized."
                        )

                    # s is [1, C, H, W] → convert to [1, H, W, C]
                    s = torch.clamp(s.movedim(-3, -1), min=0, max=1.0).to(
                        model_management.intermediate_dtype()
                    )

                    # --- Optional post-model rescale ---
                    if upscale_by > 0.0:
                        H_in, W_in = img.shape[1], img.shape[2]
                        target_w = max(
                            1,
                            round(W_in * upscale_by / resolution_steps)
                            * resolution_steps,
                        )
                        target_h = max(
                            1,
                            round(H_in * upscale_by / resolution_steps)
                            * resolution_steps,
                        )
                        out_H, out_W = s.shape[1], s.shape[2]
                        if out_W != target_w or out_H != target_h:
                            s = comfy.utils.common_upscale(
                                s.movedim(-1, 1),
                                target_w,
                                target_h,
                                resampling,
                                "disabled",
                            ).movedim(
                                1, -1
                            )  # back to [1, H, W, C]

                    s = _apply_sharpen(
                        s,
                        sharpen_enabled,
                        sharpen_amount,
                        sharpen_ratio,
                        noise_radius,
                        preserve_edges,
                    )
                    upscaled_list.append(s)
            finally:
                upscale_model.to("cpu")

        merged_tensor = torch.cat(upscaled_list, dim=0)
        result = _filter_prepare_output(merged_tensor, was_batch)
        return io.NodeOutput(result)

__all__ = ['ReaperImageUpscale']
