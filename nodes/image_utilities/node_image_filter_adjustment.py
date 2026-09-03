"""Node implementation: Image Filter Adjustment."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperImageFilterAdjustment(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        # Register LUTs folder dynamically in folder_paths
        if "luts" not in folder_paths.folder_names_and_paths:
            luts_dir = os.path.join(folder_paths.models_dir, "luts")
            if not os.path.exists(luts_dir):
                os.makedirs(luts_dir, exist_ok=True)
            folder_paths.folder_names_and_paths["luts"] = ([luts_dir], {".cube"})

        try:
            luts = folder_paths.get_filename_list("luts")
            lut_list = ["none"] + sorted(luts)
        except Exception:
            lut_list = ["none"]

        return io.Schema(
            node_id="ReaperImageFilterAdjustment",
            display_name=node_title('Image Filter Adjustment', branded=False),
            category=_CATEGORY,
            description="Apply brightness, contrast, saturation, sharpness, blur, "
            "white balance (temp/tint/hue), solarize, LUT, vignette, "
            "chromatic aberration, and film grain effects.",
            is_input_list=True,
            inputs=[
                io.Image.Input("image"),
                io.Float.Input(
                    "brightness",
                    default=0.0,
                    min=-1.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Additive brightness offset. 0 = no change.",
                ),
                io.Float.Input(
                    "contrast",
                    default=1.0,
                    min=-1.0,
                    max=2.0,
                    step=0.01,
                    tooltip="Multiplicative contrast factor. 1 = no change.",
                ),
                io.Float.Input(
                    "saturation",
                    default=1.0,
                    min=0.0,
                    max=5.0,
                    step=0.01,
                    tooltip="Color saturation factor. 1 = no change.",
                ),
                io.Float.Input(
                    "sharpness",
                    default=1.0,
                    min=-5.0,
                    max=5.0,
                    step=0.01,
                    tooltip="Sharpness factor. 1 = no change.",
                ),
                io.Int.Input(
                    "blur",
                    default=0,
                    min=0,
                    max=16,
                    step=1,
                    tooltip="Number of box-blur passes.",
                ),
                io.Float.Input(
                    "gaussian_blur",
                    default=0.0,
                    min=0.0,
                    max=1024.0,
                    step=0.1,
                    tooltip="Gaussian blur radius. 0 = disabled.",
                ),
                io.Float.Input(
                    "edge_enhance",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Edge enhancement blend strength. 0 = disabled.",
                ),
                io.Boolean.Input(
                    "detail_enhance",
                    default=False,
                    tooltip="Apply PIL DETAIL filter.",
                ),
                io.Float.Input(
                    "hue_shift",
                    default=0.0,
                    min=-180.0,
                    max=180.0,
                    step=1.0,
                    tooltip="Shift image hue in degrees. 0 = no change. Suggested range: -10.0 to 10.0 for minor corrections.",
                ),
                io.Float.Input(
                    "color_temp",
                    default=0.0,
                    min=-1.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Color temperature warmth shift. Negative = cool (blue), Positive = warm (yellow). Suggested range: -0.2 to 0.2.",
                ),
                io.Float.Input(
                    "color_tint",
                    default=0.0,
                    min=-1.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Color tint shift. Negative = green, Positive = magenta. Suggested range: -0.1 to 0.1.",
                ),
                io.Float.Input(
                    "vignette_intensity",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Vignette edge darkening strength. 0 = disabled. Suggested values: 0.1 - 0.4.",
                ),
                io.Float.Input(
                    "vignette_center_x",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Vignette center X coordinate.",
                ),
                io.Float.Input(
                    "vignette_center_y",
                    default=0.5,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Vignette center Y coordinate.",
                ),
                io.Float.Input(
                    "grain_strength",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Film grain overlay strength. 0 = disabled. Suggested values: 0.02 - 0.05 for subtle grain, 0.10 for heavy grain.",
                ),
                io.Float.Input(
                    "grain_size",
                    default=1.0,
                    min=1.0,
                    max=10.0,
                    step=0.1,
                    tooltip="Film grain pixel clump size. Suggested values: 1.0 - 2.5.",
                ),
                io.Float.Input(
                    "grain_saturation",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Film grain color saturation. 0 = monochrome.",
                ),
                io.Float.Input(
                    "solarize_threshold",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Solarize color inversion threshold. 0 = disabled. Suggested values: 0.5 - 0.8.",
                ),
                io.Float.Input(
                    "chromatic_aberration",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="Chromatic aberration displacement strength. 0 = disabled. Suggested values: 0.01 - 0.05 for subtle realism, 0.1+ for strong styling.",
                ),
                io.Combo.Input(
                    "lut_name",
                    options=lut_list,
                    default="none",
                    tooltip="3D Look-Up Table (LUT) file (.cube) from models/luts/.",
                ),
                io.Float.Input(
                    "lut_strength",
                    default=1.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip="LUT blending opacity/strength.",
                ),
                io.Boolean.Input(
                    "per_frame",
                    default=True,
                    tooltip="Process PIL actions one frame at a time (safe for large batches, avoids OOM).",
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
        brightness,
        contrast,
        saturation,
        sharpness,
        blur,
        gaussian_blur,
        edge_enhance,
        detail_enhance,
        hue_shift,
        color_temp,
        color_tint,
        vignette_intensity,
        vignette_center_x,
        vignette_center_y,
        grain_strength,
        grain_size,
        grain_saturation,
        solarize_threshold,
        chromatic_aberration,
        lut_name,
        lut_strength,
        per_frame=True,
    ):
        brightness = _filter_unwrap_value(brightness, 0.0)
        contrast = _filter_unwrap_value(contrast, 1.0)
        saturation = _filter_unwrap_value(saturation, 1.0)
        sharpness = _filter_unwrap_value(sharpness, 1.0)
        blur = _filter_unwrap_value(blur, 0)
        gaussian_blur = _filter_unwrap_value(gaussian_blur, 0.0)
        edge_enhance = _filter_unwrap_value(edge_enhance, 0.0)
        detail_enhance = _filter_unwrap_value(detail_enhance, False)
        hue_shift = _filter_unwrap_value(hue_shift, 0.0)
        color_temp = _filter_unwrap_value(color_temp, 0.0)
        color_tint = _filter_unwrap_value(color_tint, 0.0)
        vignette_intensity = _filter_unwrap_value(vignette_intensity, 0.0)
        vignette_center_x = _filter_unwrap_value(vignette_center_x, 0.5)
        vignette_center_y = _filter_unwrap_value(vignette_center_y, 0.5)
        grain_strength = _filter_unwrap_value(grain_strength, 0.0)
        grain_size = _filter_unwrap_value(grain_size, 1.0)
        grain_saturation = _filter_unwrap_value(grain_saturation, 0.0)
        solarize_threshold = _filter_unwrap_value(solarize_threshold, 0.0)
        chromatic_aberration = _filter_unwrap_value(chromatic_aberration, 0.0)
        lut_name = _filter_unwrap_value(lut_name, "none")
        lut_strength = _filter_unwrap_value(lut_strength, 1.0)
        per_frame = _filter_unwrap_value(per_frame, True)

        flat_image = _flatten_comparer_images(image)
        if not flat_image:
            raise ValueError(
                "Filter Adjustments Advanced: No images provided in input."
            )

        was_batch = _filter_was_input_batch(image)

        # Determine if we need to do any PIL operations
        needs_pil = (
            saturation != 1.0
            or sharpness != 1.0
            or blur > 0
            or gaussian_blur > 0.0
            or edge_enhance > 0.0
            or detail_enhance
        )

        def process_pil_frame(frame):
            pil_image = _tensor_to_pil(frame)
            if saturation != 1.0:
                pil_image = ImageEnhance.Color(pil_image).enhance(saturation)
            if sharpness != 1.0:
                pil_image = ImageEnhance.Sharpness(pil_image).enhance(sharpness)
            if blur > 0:
                for _ in range(blur):
                    pil_image = pil_image.filter(ImageFilter.BLUR)
            if gaussian_blur > 0.0:
                pil_image = pil_image.filter(
                    ImageFilter.GaussianBlur(radius=gaussian_blur)
                )
            if edge_enhance > 0.0:
                enhanced = pil_image.filter(ImageFilter.EDGE_ENHANCE_MORE)
                mask = Image.new("L", pil_image.size, round(edge_enhance * 255))
                pil_image = Image.composite(enhanced, pil_image, mask)
            if detail_enhance:
                pil_image = pil_image.filter(ImageFilter.DETAIL)
            return _pil_to_tensor(pil_image)

        preprocessed = []
        for img in flat_image:
            img = img.float()
            if brightness != 0.0:
                img = (img + brightness).clamp_(0.0, 1.0)
            if contrast != 1.0:
                img = (img * contrast).clamp_(0.0, 1.0)
            preprocessed.append(img)

        # Step 2: PIL operations (if requested)
        if needs_pil:
            if per_frame or len(preprocessed) == 1:
                pil_results = [process_pil_frame(img[0]) for img in preprocessed]
            else:
                frames_to_process = [img[0] for img in preprocessed]
                with ThreadPoolExecutor() as executor:
                    pil_results = list(executor.map(process_pil_frame, frames_to_process))
            # Reconstruct the batch list
            preprocessed = pil_results

        # Step 3: Pure PyTorch effects
        # order: WB/Hue -> Solarize -> LUT -> Vignette -> CA -> Grain
        processed_list = []
        for img in preprocessed:
            img = adjust_temperature_and_tint(img, color_temp, color_tint)
            img = adjust_hue(img, hue_shift)
            img = apply_solarize(img, solarize_threshold)
            img = apply_lut(img, lut_name, lut_strength)
            img = apply_vignette(
                img, vignette_intensity, vignette_center_x, vignette_center_y
            )
            img = apply_chromatic_aberration(img, chromatic_aberration)
            img = apply_film_grain(img, grain_strength, grain_size, grain_saturation)
            processed_list.append(img)

        merged_tensor = torch.cat(processed_list, dim=0)
        result = _filter_prepare_output(merged_tensor, was_batch)
        return io.NodeOutput(result)

__all__ = ['ReaperImageFilterAdjustment']
