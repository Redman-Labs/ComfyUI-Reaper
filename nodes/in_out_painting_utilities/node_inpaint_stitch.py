import torch
from comfy_api.latest import io
from ..global_configs import CATEGORIES, node_title
from .._helpers._inpaint_helpers import stitch_back, resolve_seam, REAPER_CROP_INFO
from .shared_in_out_painting import REAPER_CROP_INFO as CropInfo, node_output


class ReaperInpaintStitch(io.ComfyNode):
    DESCRIPTION = (
        "Inpaint Stitch Reaper - paste your inpainted crop back onto the "
        "original image at the exact spot it came from, blended so the seam "
        "disappears.\n\n"
        "Wire the crop_info output of Inpaint Crop Reaper into crop_info here, "
        "and wire your inpainted crop (after the model) into image. The node "
        "resizes the crop back to the region and blends only the painted area by "
        "default, so everything outside the mask stays pixel-perfect.\n\n"
        "The seam softness and blend mode come from the Inpaint Crop node on the "
        "crop_info wire, but you can OVERRIDE them here (softness -1 = use the "
        "crop's). Because this node is after the sampler, changing softness, blend "
        "mode or color match re-runs only this node - the sampler stays cached on a "
        "fixed seed - so you can fine-tune the blend instantly without re-generating. "
        "color match corrects a color/tone shift the model introduced.\n\n"
        "Outputs the finished full image, plus the original uncropped image - wire "
        "both into Image Compare Reaper for an instant before / after."
    )

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ReaperInpaintStitch", display_name=node_title("Inpaint Stitch"),
            category=CATEGORIES["in_out_painting_utilities"], description=cls.DESCRIPTION,
            inputs=[io.Image.Input("image"), io.Mask.Input("mask", optional=True),
                    CropInfo.Input("crop_info", optional=True),
                    io.Int.Input("softness", optional=True, default=-1, min=-1, max=150),
                    io.Combo.Input("blend_mode", optional=True, options=["from crop", "mask", "whole crop"], default="from crop"),
                    io.Combo.Input("color_match", optional=True, options=["off", "subtle", "strong"], default="off")],
            outputs=[io.Image.Output(id="image", display_name="image"),
                     io.Image.Output(id="original", display_name="original")],
        )

    @classmethod
    def execute(cls, **kwargs):
        return node_output(cls().run(**kwargs))

    @classmethod
    def validate_inputs(cls, **kwargs):
        return True

    @classmethod
    def _legacy_INPUT_TYPES(cls):
        # Slot order image, mask, crop_info lines up under Inpaint Crop's
        # image / mask / crop_info outputs so the wires run straight across.
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": (
                        "Your inpainted crop (after the model). Resized back to the "
                        "original crop region automatically if its size differs."
                    ),
                }),
            },
            "optional": {
                "mask": ("MASK", {
                    "tooltip": (
                        "Optional. Limits the blend to this area (resized to the "
                        "crop region). If omitted, the painted mask carried in "
                        "crop_info is used for the mask-aware blend."
                    ),
                }),
                "crop_info": (REAPER_CROP_INFO, {
                    "tooltip": (
                        "Wire the crop_info output of Inpaint Crop Reaper here. "
                        "If left unwired, the image passes straight through."
                    ),
                }),
                "softness": ("INT", {
                    "default": -1, "min": -1, "max": 150, "step": 1,
                    "tooltip": (
                        "Seam feather, overriding the Inpaint Crop node's softness. "
                        "-1 = use the Crop node's value. Set 0-150 to tune the blend "
                        "HERE - because Stitch is after the sampler, only this node "
                        "re-runs (the sampler stays cached on a fixed seed), so it is "
                        "instant. Going bigger than the room the crop left may show a "
                        "slightly harder edge - raise the Crop node's softness for "
                        "more room."
                    ),
                }),
                "blend_mode": (["from crop", "mask", "whole crop"], {
                    "default": "from crop",
                    "tooltip": (
                        "Override the Crop node's blend mode. 'from crop' = use what "
                        "the Crop node set. 'mask' = replace only the painted area. "
                        "'whole crop' = replace the entire cropped box. Like softness, "
                        "changing it here re-runs only this node (no re-sample)."
                    ),
                }),
                "color_match": (["off", "subtle", "strong"], {
                    "default": "off",
                    "tooltip": (
                        "Correct a color/tone shift the model introduced, matching "
                        "the unchanged surroundings around your mask. Keep it Off "
                        "when you deliberately changed colors (it would pull them "
                        "back). No live preview - set it and re-run."
                    ),
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("image", "original")
    OUTPUT_TOOLTIPS = (
        "The original image with the inpainted crop blended back in place.",
        "The full original uncropped image (from crop_info) - wire it together "
        "with the result into Image Compare Reaper for a before / after.",
    )
    FUNCTION = "execute"
    CATEGORY = "👑 Reaper/✂️ Resize & Crop"

    def run(self, image, crop_info=None, mask=None, softness=-1,
            blend_mode="from crop", color_match="off"):
        # No valid crop_info -> nothing to paste back; pass the image through as
        # both outputs so downstream wiring still works. Require the geometry keys
        # too, so a malformed dict doesn't silently paste at (0,0) full-size.
        if (not isinstance(crop_info, dict)
                or not isinstance(crop_info.get("image"), torch.Tensor)
                or crop_info["image"].dim() != 4
                or any(k not in crop_info for k in ("x", "y", "w", "h"))):
            # malformed / missing crop_info (incl. a non-[B,H,W,C] image) -> pass the
            # image through as BOTH outputs so the graph still runs. Checking the rank
            # here keeps a bad image out of stitch_back (which would otherwise throw and
            # the except below would silently make `original` a copy of the result).
            print("[ReaperInpaintStitch] no valid crop_info wired - passing image through")
            return (image, image)

        # Seam blend + mode ride in on crop_info from the Crop node, but THIS node's
        # softness / blend_mode widgets override them when set (so the blend can be
        # tuned here without re-running the sampler). color_match is this node's own
        # knob (post-result tweak, no live preview).
        blend, blend_mode = resolve_seam(crop_info, softness, blend_mode)
        cm = str(color_match)
        color_match = cm if cm in ("off", "subtle", "strong") else "off"

        try:
            result, original = stitch_back(crop_info, image, mask, blend, blend_mode, color_match)
        except Exception as e:
            # A genuine fault inside stitch_back (e.g. CUDA OOM). Pass the inpainted
            # image through as the result, but keep `original` as the TRUE uncropped
            # original (crop_info["image"] already passed the dim==4 guard above), so a
            # downstream before/after compare shows the real original, not a patch copy.
            print(f"[ReaperInpaintStitch] stitch error: {e}")
            return (image, crop_info["image"])
        return (result, original)


NODE_CLASS_MAPPINGS = {
    "ReaperInpaintStitch": ReaperInpaintStitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ReaperInpaintStitch": "Inpaint Stitch Reaper",
}

__all__ = ["ReaperInpaintStitch"]
