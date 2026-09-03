"""Node implementation: Color Match."""
from __future__ import annotations

from ..global_configs import CATEGORIES, node_title
from .shared_image_utilities._shared import *

CATEGORY = CATEGORIES['image_utilities']
_CATEGORY = CATEGORY

class ReaperColorMatch(io.ComfyNode):
    @staticmethod
    def _sanitize_output(output):
        # Keep invalid pixels from propagating to preview or downstream image nodes.
        return torch.nan_to_num(output, nan=0.0, posinf=1.0, neginf=0.0).clamp_(0, 1)

    @staticmethod
    def _cpu_matcher_input(tensor, method, frame_index, input_name):
        # Build a finite, range-safe CPU copy without changing valid black pixels.
        image_np = tensor.detach().cpu().numpy().copy()
        finite = np.isfinite(image_np)
        out_of_range = finite & ((image_np < 0.0) | (image_np > 1.0))
        if not finite.all() or out_of_range.any():
            finite_values = image_np[finite]
            value_range = (
                f"{finite_values.min():.6g} to {finite_values.max():.6g}"
                if finite_values.size
                else "no finite values"
            )
            _COLOR_MATCH_LOGGER.warning(
                f"Frame {frame_index} {input_name} for {method} contains non-finite or "
                f"out-of-range RGB values ({value_range}); normalizing to [0, 1].",
            )
        np.nan_to_num(image_np, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        np.clip(image_np, 0.0, 1.0, out=image_np)
        return image_np

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperColorMatch",
            display_name=node_title('Color Match', branded=False),
            category=_CATEGORY,
            description=(
                "Transfer color grading from a reference image onto a target image. "
                "CPU methods (color-matcher): mkl, hm, reinhard, mvgd, hm-mvgd-hm, hm-mkl-hm. "
                "GPU methods: reinhard_lab_gpu (Kornia), wavelet (Haar wavelet LAB transfer), "
                "scattersort (exact histogram matching). CPU inputs are normalized to finite RGB "
                "values for stable processing; invalid results fall back to the target image. "
                "Based on KJNodes ColorMatch."
            ),
            is_input_list=True,
            inputs=[
                io.Image.Input(
                    "image",
                    tooltip="Target image to apply color grading to. Passes through on bypass.",
                ),
                io.Image.Input(
                    "image_ref",
                    tooltip="Reference image whose colors will be transferred.",
                ),
                io.Combo.Input(
                    "method",
                    options=[
                        "mkl",
                        "hm",
                        "reinhard",
                        "mvgd",
                        "hm-mvgd-hm",
                        "hm-mkl-hm",
                        "reinhard_lab_gpu",
                        "wavelet",
                        "scattersort",
                    ],
                    default="mkl",
                    tooltip=(
                        "Color transfer algorithm. wavelet = Haar wavelet LAB transfer (preserves detail). "
                        "scattersort = exact histogram matching per channel. CPU methods normalize "
                        "non-finite or out-of-range RGB inputs for numerical stability."
                    ),
                ),
                io.Float.Input(
                    "strength",
                    default=1.0,
                    min=0.0,
                    max=10.0,
                    step=0.01,
                    tooltip="Blend strength. 0 = no change, 1 = full transfer.",
                ),
                io.Boolean.Input(
                    "multithread",
                    default=True,
                    tooltip="Use multithreading for batch processing.",
                ),
                io.Boolean.Input(
                    "per_frame",
                    default=False,
                    tooltip="Process each frame independently instead of the whole batch at once. "
                    "Caps VRAM usage to one frame at a time for GPU methods; slightly slower "
                    "but avoids out-of-memory errors on large batches.",
                ),
            ],
            outputs=[
                io.Image.Output("image", is_output_list=True),
            ],
        )

    @classmethod
    def execute(
        cls, image, image_ref, method, strength=1.0, multithread=True, per_frame=False
    ):
        method = _filter_unwrap_value(method, "mkl")
        strength = _filter_unwrap_value(strength, 1.0)
        multithread = _filter_unwrap_value(multithread, True)
        per_frame = _filter_unwrap_value(per_frame, False)

        if strength == 0:
            return io.NodeOutput(image)

        flat_image = _flatten_comparer_images(image)
        flat_ref = _flatten_comparer_images(image_ref)

        if not flat_image or not flat_ref:
            raise ValueError("Color Match: No images provided in input/reference.")

        was_batch = _filter_was_input_batch(image)

        processed_list = []
        for i, img in enumerate(flat_image):
            ref_img = flat_ref[min(i, len(flat_ref) - 1)] if per_frame else flat_ref[0]
            out = cls._process_batch(img, ref_img, method, strength, multithread)
            processed_list.append(out)

        merged_tensor = torch.cat(processed_list, dim=0)
        result = _filter_prepare_output(merged_tensor, was_batch)
        return io.NodeOutput(result)

    @classmethod
    def _process_batch(cls, image, image_ref, method, strength, multithread):
        # GPU path — Kornia reinhard in Lab space
        if method == "reinhard_lab_gpu":
            import kornia  # type: ignore

            device = model_management.get_torch_device()

            B, H, W, C = image.shape

            src_bchw = image.to(device).permute(0, 3, 1, 2).contiguous()
            ref_bchw = image_ref.to(device).permute(0, 3, 1, 2).contiguous()

            src_lab = kornia.color.rgb_to_lab(src_bchw)
            ref_lab = kornia.color.rgb_to_lab(ref_bchw)

            src_lab_flat = src_lab.view(B, C, -1)
            ref_lab_flat = ref_lab.view(ref_lab.shape[0], C, -1)

            src_std, src_mean = torch.std_mean(
                src_lab_flat, dim=-1, keepdim=True, unbiased=False
            )
            ref_std, ref_mean = torch.std_mean(
                ref_lab_flat, dim=-1, keepdim=True, unbiased=False
            )
            src_std = src_std.clamp_min_(1e-6)

            if ref_lab.shape[0] == 1 and B > 1:
                ref_mean = ref_mean.expand(B, -1, -1)
                ref_std = ref_std.expand(B, -1, -1)

            corrected_lab_flat = (src_lab_flat - src_mean) * (
                ref_std / src_std
            ) + ref_mean
            corrected_lab = corrected_lab_flat.view(B, C, H, W)

            corrected_rgb = kornia.color.lab_to_rgb(corrected_lab)
            out = (1.0 - strength) * src_bchw + strength * corrected_rgb
            out = out.permute(0, 2, 3, 1).contiguous()

            return cls._sanitize_output(out.cpu().float())

        # GPU path — Haar wavelet color transfer in LAB space
        if method == "wavelet":
            device = model_management.get_torch_device()
            src_bchw = image.to(device).permute(0, 3, 1, 2).contiguous()
            ref_bchw = image_ref.to(device).permute(0, 3, 1, 2).contiguous()
            out = _wavelet_color_transfer(src_bchw, ref_bchw, strength)
            out = out.permute(0, 2, 3, 1).contiguous()
            return cls._sanitize_output(out.cpu().float())

        # GPU path — scattersort exact histogram matching
        if method == "scattersort":
            device = model_management.get_torch_device()
            src_bchw = image.to(device).permute(0, 3, 1, 2).contiguous()
            ref_bchw = image_ref.to(device).permute(0, 3, 1, 2).contiguous()
            out = _scattersort_transfer(src_bchw, ref_bchw, strength)
            out = out.permute(0, 2, 3, 1).contiguous()
            return cls._sanitize_output(out.cpu().float())

        # CPU path — color-matcher library
        try:
            from color_matcher import ColorMatcher  # type: ignore
        except ImportError:
            raise ImportError(
                "color-matcher is not installed. Install with: pip install color-matcher"
            )

        batch_size = image.size(0)
        ref_batch_size = image_ref.size(0)

        def process(i):  # noqa: E306
            cm = ColorMatcher()
            target_base = cls._cpu_matcher_input(image[i], method, i, "target")
            # color-matcher mutates its source, so keep the blend/fallback baseline separate.
            target_np = target_base.copy()
            ref_np = cls._cpu_matcher_input(
                image_ref[min(i, ref_batch_size - 1)], method, i, "reference"
            )
            if method == "reinhard":
                # Reinhard takes log10 of LMS values; floor only the matcher inputs.
                np.maximum(target_np, 1.0 / 255.0, out=target_np)
                np.maximum(ref_np, 1.0 / 255.0, out=ref_np)
            try:
                result = cm.transfer(src=target_np, ref=ref_np, method=method)
                if result.shape != target_np.shape or not np.isfinite(result).all():
                    _COLOR_MATCH_LOGGER.warning(
                        f"Frame {i} {method} returned an invalid result; using the target image.",
                    )
                    return torch.from_numpy(target_base)
                if strength != 1:
                    result = target_base + strength * (result - target_base)
                return torch.from_numpy(result)
            except Exception as e:
                _COLOR_MATCH_LOGGER.error( f"Frame {i} {method} error: {e}")
                return torch.from_numpy(target_base)

        if multithread and batch_size > 1:
            max_threads = min(os.cpu_count() or 1, batch_size)
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                out = list(executor.map(process, range(batch_size)))
        else:
            out = [process(i) for i in range(batch_size)]

        out = torch.stack(out, dim=0).to(torch.float32)
        return cls._sanitize_output(out)

__all__ = ['ReaperColorMatch']
