"""ComfyUI-Krea2Edit — in-context edit forward for the Krea2 model.

ComfyUI's native Krea2 `_forward` is text-to-image only: it builds the sequence
`[text | target]`. The krea2_edit LoRA (trained in ai-toolkit) needs the *appearance
path*: the VAE-encoded SOURCE latent prepended as a block of clean tokens, distinguished
from the (noisy) target purely by the 3-axis RoPE frame index (source=1, target=0, h/w
aligned). This node adds that by wrapping the model's DIFFUSION_MODEL forward and rebuilding
the sequence as `[text | source(frame=1) | target(frame=0)]`, keeping only the target tokens
out — mirroring ai-toolkit's `predict_velocity_edit` exactly, using the model's own submodules.

Wiring:  LoadImage -> VAEEncode(source) --\
                                            Krea2EditModelPatch(model, source_latent) -> KSampler
         UNETLoader -> LoraLoaderModelOnly -/
KSampler.latent_image <- EmptySD3LatentImage (noise). Text: NATIVE krea2 CLIP + CLIPTextEncode.
"""
import math

import torch
from comfy_api.latest import io

from ..global_configs import CATEGORIES
import torch.nn.functional as F
from einops import rearrange

import comfy.patcher_extension
import comfy.utils
import comfy.ldm.common_dit
from comfy.ldm.flux.layers import timestep_embedding
from comfy.ldm.flux.math import apply_rope
from comfy.ldm.modules.attention import optimized_attention_masked


def _imgids(bs, frame, h_, w_, device):
    ids = torch.zeros(h_, w_, 3, device=device, dtype=torch.float32)
    ids[..., 0] = frame
    ids[..., 1] = torch.arange(h_, device=device, dtype=torch.float32)[:, None]
    ids[..., 2] = torch.arange(w_, device=device, dtype=torch.float32)[None, :]
    return ids.reshape(1, h_ * w_, 3).repeat(bs, 1, 1)


def _imgids_offset(bs, frame, gh, gw, th, tw, device):
    """Stride-1 integer positions at a centered integer offset. For `fit` refs the
    pixels are already resampled to target grid density, so the position grid is
    stride-1 BY CONSTRUCTION — scaling it again only manufactures skip/collision
    artifacts. Requires gh<=th, gw<=tw (guaranteed by the floor+cap in fit)."""
    # fractional center (2026-07-28): integer floor placed odd-gap refs 8px off
    # their true center — RoPE is continuous, half-token positions are exact.
    off_h, off_w = max(0.0, (th - gh) / 2), max(0.0, (tw - gw) / 2)
    ids = torch.zeros(gh, gw, 3, device=device, dtype=torch.float32)
    ids[..., 0] = frame
    ids[..., 1] = (torch.arange(gh, device=device, dtype=torch.float32) + off_h)[:, None]
    ids[..., 2] = (torch.arange(gw, device=device, dtype=torch.float32) + off_w)[None, :]
    return ids.reshape(1, gh * gw, 3).repeat(bs, 1, 1)


def _to_4d(v):
    """(B,C,T,H,W) -> (B*T,C,H,W); pass 4D through. Images use T=1."""
    if v.ndim == 5:
        b, c, t, h, w = v.shape
        return v.reshape(b * t, c, h, w)
    return v


def _fit_src(src, H, W):
    """Fit a source latent to the target grid the way TRAINING did: center-crop to
    the target aspect ratio, then resize. A plain interpolate (the pre-fix behavior)
    STRETCHES mixed-AR sources — users saw stretched people whenever their input AR
    differed from the output resolution."""
    sh, sw = src.shape[-2:]
    if (sh, sw) == (H, W):
        return src
    s = max(H / sh, W / sw)
    ch, cw = min(sh, int(round(H / s))), min(sw, int(round(W / s)))
    y0, x0 = (sh - ch) // 2, (sw - cw) // 2
    src = src[..., y0:y0 + ch, x0:x0 + cw]
    return F.interpolate(src.float(), size=(H, W), mode="bilinear")


def _fit_encode_image(image, vae, H, W, cache, key, fit_mode="crop"):
    """Pixel-space source prep (blur-proof path): center-crop the IMAGE to the
    target AR, resize to the exact target pixel grid, VAE-encode. Latent-space
    resizing (the old fallback) softens VAE latents — this path never resizes
    latents at all. Cached per target resolution (encode once, not per step)."""
    key = key + (fit_mode,)
    if key in cache:
        return cache[key]
    print(f"[krea2edit] _fit_encode_image: mode={fit_mode} in={tuple(image.shape)} target_latent={H}x{W}", flush=True)
    px_h, px_w = H * 8, W * 8
    img = image.movedim(-1, 1)  # B,H,W,C -> B,C,H,W
    ih, iw = img.shape[-2:]
    if fit_mode == "fit":
        # "bilinear" answer to scale mismatch: resample CONTENT (pixel space, bicubic)
        # to the target's grid density instead of moving positions. AR-preserving
        # fit-inside, no crop, no grey canvas — the forward places it at an integer
        # centered offset (scaled-pos with s=1 -> stride 1, no rounding artifacts).
        sc = min(px_h / ih, px_w / iw)
        # NEAR-MATCHED AR: fill the target grid EXACTLY via a minimal center-crop.
        # Fit-inside margins of 1-2 tokens are not harmless: target edge columns
        # with no ref correspondence get filled by repeating adjacent ref content
        # (2026-07-14 edge-duplication bug: ref (74,54) vs target (74,56)).
        # This also restores the design promise fit == crop at matched AR.
        CROP_TOL = 0.08
        if ih * sc >= px_h * (1 - CROP_TOL) and iw * sc >= px_w * (1 - CROP_TOL):
            s = max(px_h / ih, px_w / iw)
            ch, cw = min(ih, int(round(px_h / s))), min(iw, int(round(px_w / s)))
            y0, x0 = (ih - ch) // 2, (iw - cw) // 2
            img = img[..., y0:y0 + ch, x0:x0 + cw]
            nh, nw = px_h, px_w
        else:
            # genuine AR mismatch: MUST match the trainer's _fit_prep EXACTLY
            # (krea2_edit.py) — /16 floor snap capped at the target's /16 floor.
            # The model is trained on this geometry; a /8-round node grid would
            # produce a different ref latent size -> different centered offset ->
            # a visible margin-boundary seam even from a well-trained model
            # (train/infer geometry must be byte-identical). 2026-07-15 alignment.
            nh = min(max(16, int(ih * sc) // 16 * 16), max(16, px_h // 16 * 16))
            nw = min(max(16, int(iw * sc) // 16 * 16), max(16, px_w // 16 * 16))
            # CROP-TO-GRID (2026-07-28 seam-doubling RCA): resizing ih*sc -> floor16
            # SQUASHES content by up to 15px; the misregistration peaks exactly at
            # the ref band edges — the outpaint seam — and renders as a doubled
            # band (proven causal: 754px vs 753px input A/B, one pixel flips
            # clean<->worst). Center-crop the source so the fitted axis lands on
            # the /16 grid at scale sc EXACTLY: zero squash, stride-1 stays true.
            ch2, cw2 = min(ih, max(1, int(round(nh / sc)))), min(iw, max(1, int(round(nw / sc))))
            y0, x0 = (ih - ch2) // 2, (iw - cw2) // 2
            img = img[..., y0:y0 + ch2, x0:x0 + cw2]
        img = F.interpolate(img.float(), size=(nh, nw), mode="bicubic", antialias=True)
        lat = vae.encode(img.movedim(1, -1)[..., :3].clamp(0, 1))
        cache[key] = lat
        return lat
    # crop (default / "v1 legacy"): center-crop to the target AR, then resize.
    s = max(px_h / ih, px_w / iw)
    ch, cw = min(ih, int(round(px_h / s))), min(iw, int(round(px_w / s)))
    y0, x0 = (ih - ch) // 2, (iw - cw) // 2
    img = img[..., y0:y0 + ch, x0:x0 + cw]
    img = F.interpolate(img.float(), size=(px_h, px_w), mode="bicubic", antialias=True)
    lat = vae.encode(img.movedim(1, -1)[..., :3].clamp(0, 1))
    cache[key] = lat
    return lat


def _ref_attn_bias(boosts, boost_mask, txtlen, slens, tgtlen, mask_hw, device, dtype):
    """Additive attention-logit bias on the [text | refs... | target] sequence.

    boosts: per-ref factor on target->ref attention, aligned with the source blocks
    (last entry = last ref = the subject by workflow convention). Equivalent to
    multiplying those keys' post-softmax attention weight before renormalization.
    boost_mask (ComfyUI MASK, ref-image pixel space) restricts the LAST ref's boost
    to a region (e.g. the face).
    """
    nsrc = len(slens)
    offs = [txtlen]
    for sl in slens:
        offs.append(offs[-1] + sl)
    rows0 = offs[-1]
    L = rows0 + tgtlen
    bias = torch.zeros(1, 1, L, L, device=device, dtype=dtype)
    for i, b in enumerate(boosts):
        if b == 1.0:
            continue
        off, sl = offs[i], slens[i]
        if boost_mask is not None and i == nsrc - 1 and mask_hw is not None:
            mask = boost_mask[:1]
            if mask.ndim == 2:
                mask = mask[None]
            mask = F.interpolate(mask[None].float(), size=mask_hw[i], mode="area")[0, 0]
            cols = off + torch.nonzero(mask.reshape(-1) > 0.5, as_tuple=True)[0].to(device)
        else:
            cols = torch.arange(off, off + sl, device=device)
        bias[:, :, rows0:, cols] = math.log(max(b, 1e-4))
    return bias


def krea2_edit_forward(m, x, timesteps, context, src_latent, transformer_options,
                       ref_boost=1.0, ref_boost_a=1.0, ref_boost_mask=None,
                       ref_native=False, pos_mode="anchor"):
    """Krea2 SingleStreamDiT._forward, but with source block(s) prepended.

    m           : the SingleStreamDiT (LoRA-patched at sample time)
    x           : (B,C,H,W) or (B,C,T,H,W) noisy TARGET latent
    src_latent  : clean SOURCE latent (VAE-encoded), 4D/5D — or a LIST of them
                  (multi-ref: [scene, subject], frames 1..N, training-matched)
    context     : (B, seq, txtlayers*txtdim) — the 12-layer Qwen3-VL stack
    """
    patch = m.patch

    # Mirror ComfyUI _forward: latents may arrive 5D (B,C,T,H,W) for this model.
    temporal = x.ndim == 5
    if temporal:
        b5, c5, t5, h5, w5 = x.shape
    x = _to_4d(x)
    bs, c, H_orig, W_orig = x.shape

    x = comfy.ldm.common_dit.pad_to_patch_size(x, (patch, patch), padding_mode="replicate")
    H, W = x.shape[-2], x.shape[-1]
    h_, w_ = H // patch, W // patch

    # source(s) -> (bs, C, H, W): flatten temporal, match batch, fit to the target grid
    # (center-crop to target AR then resize — training-matched; never stretch).
    src_list = src_latent if isinstance(src_latent, (list, tuple)) else [src_latent]
    srcs = []
    for sl in src_list:
        src = _to_4d(sl).to(x.device, x.dtype)
        if src.shape[0] != bs:
            src = src[:1].expand(bs, *src.shape[1:])
        if not ref_native and src.shape[-2:] != (H, W):
            print(f"[krea2edit] LATENT-PATH fit_src (crop): src={tuple(src.shape[-2:])} -> {H}x{W}", flush=True)
            src = _fit_src(src, H, W).to(x.dtype)
        srcs.append(comfy.ldm.common_dit.pad_to_patch_size(src, (patch, patch), padding_mode="replicate"))
    src_grids = [(s_.shape[-2] // patch, s_.shape[-1] // patch) for s_ in srcs]

    context = m._unpack_context(context)                       # (B, seq, 12, 2560)

    tgt_img = m.first(rearrange(x, "b c (h ph) (w pw) -> b (h w) (c ph pw)", ph=patch, pw=patch))
    src_imgs = [m.first(rearrange(s_, "b c (h ph) (w pw) -> b (h w) (c ph pw)", ph=patch, pw=patch))
                for s_ in srcs]

    t = m.tmlp(timestep_embedding(timesteps, m.tdim).unsqueeze(1).to(tgt_img.dtype))
    tvec = m.tproj(t)

    context = m.txtfusion(context, mask=None, transformer_options=transformer_options)
    context = m.txtmlp(context)

    txtlen, tgtlen = context.shape[1], tgt_img.shape[1]
    srclen = sum(si.shape[1] for si in src_imgs)
    combined = torch.cat([context] + src_imgs + [tgt_img], dim=1)  # [text | refs... | target]

    device = combined.device
    if pos_mode == "stride1" and ref_native:
        print(f"[krea2edit] STRIDE1-POS fit: ref grids {src_grids} centered in ({h_},{w_})", flush=True)
        ref_ids = [_imgids_offset(bs, i + 1, gh, gw, h_, w_, device)
                   for i, (gh, gw) in enumerate(src_grids)]
    else:
        ref_ids = [_imgids(bs, i + 1, gh, gw, device) for i, (gh, gw) in enumerate(src_grids)]
    pos = torch.cat([
        torch.zeros(bs, txtlen, 3, device=device, dtype=torch.float32)]   # text @ 0
        + ref_ids
        + [_imgids(bs, 0, h_, w_, device)],                                    # target frame=0
        dim=1)
    freqs = m.pe_embedder(pos)

    attn_bias = None
    if ref_boost != 1.0 or ref_boost_a != 1.0:
        # last ref = subject (single-ref: the only ref); earlier refs (scene) get ref_boost_a
        boosts = [ref_boost_a] * (len(src_imgs) - 1) + [ref_boost]
        attn_bias = _ref_attn_bias(boosts, ref_boost_mask, txtlen,
                                   [si.shape[1] for si in src_imgs], tgtlen,
                                   src_grids, combined.device, combined.dtype)

    for block in m.blocks:
        combined = block(combined, tvec, freqs, attn_bias, transformer_options=transformer_options)

    final = m.last(combined, t)
    out = final[:, txtlen + srclen: txtlen + srclen + tgtlen, :]         # target tokens only
    out = rearrange(out, "b (h w) (c ph pw) -> b c (h ph) (w pw)",
                    h=h_, w=w_, ph=patch, pw=patch, c=m.channels)
    out = out[:, :, :H_orig, :W_orig]
    if temporal:
        out = out.reshape(b5, t5, m.channels, H_orig, W_orig).movedim(1, 2)
    return out


class ReaperKrea2EditModelPatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ReaperKrea2EditModelPatch",
            display_name="Krea2 Edit (source patch)",
            category=CATEGORIES["krea2_utilities"],
            description=(
                "Adds the krea2_edit in-context source-preservation path "
                "(source latent as frame=1 tokens) to a Krea2 model."
            ),
            inputs=[
                io.Model.Input("model", display_name="Model"),
                io.Latent.Input(
                    "source_latent",
                    display_name="Source Latent",
                    tooltip="Primary source-reference latent.",
                ),
                io.Latent.Input(
                    "source_latent_b",
                    display_name="Source Latent B",
                    optional=True,
                    tooltip=(
                        "Second reference (subject photo) for multi-reference "
                        "LoRAs; training order is scene first, subject second."
                    ),
                ),
                io.Float.Input(
                    "ref_boost",
                    display_name="Reference Boost",
                    optional=True,
                    default=1.0,
                    min=0.0,
                    max=1000.0,
                    step=0.01,
                    round=0.001,
                    tooltip=(
                        "Multiplies target-to-reference attention for the last "
                        "reference. 1.0 is neutral."
                    ),
                ),
                io.Float.Input(
                    "ref_boost_a",
                    display_name="Reference Boost A",
                    optional=True,
                    default=1.0,
                    min=0.0,
                    max=1000.0,
                    step=0.01,
                    round=0.001,
                    tooltip=(
                        "Reference boost for the first reference in a "
                        "two-reference workflow. 1.0 is neutral."
                    ),
                ),
                io.Combo.Input(
                    "fit_mode",
                    display_name="Fit Mode",
                    options=["fit", "crop (legacy)"],
                    optional=True,
                    default="fit",
                    tooltip=(
                        "Fit uses training-matched centered resampling; crop "
                        "(legacy) center-crops to the target aspect ratio."
                    ),
                ),
                io.Mask.Input(
                    "ref_boost_mask",
                    display_name="Reference Boost Mask",
                    optional=True,
                    tooltip="Optional boosted region on the last reference.",
                ),
                io.Vae.Input(
                    "vae",
                    display_name="VAE",
                    optional=True,
                    tooltip=(
                        "Recommended with Source Image for the pixel-space path."
                    ),
                ),
                io.Image.Input(
                    "source_image",
                    display_name="Source Image",
                    optional=True,
                    tooltip=(
                        "With VAE, overrides Source Latent using exact "
                        "pixel-space fitting."
                    ),
                ),
                io.Image.Input(
                    "source_image_b",
                    display_name="Source Image B",
                    optional=True,
                    tooltip="Second reference image used with VAE.",
                ),
                io.Latent.Input(
                    "target_latent",
                    display_name="Target Latent",
                    optional=True,
                    tooltip=(
                        "Connect the same latent sent to the sampler to "
                        "pre-encode references before sampling."
                    ),
                ),
            ],
            outputs=[
                io.Model.Output(
                    id="model",
                    display_name="Model",
                    tooltip="Krea2 model with the edit source path installed.",
                )
            ],
        )

    @classmethod
    def execute(
        cls,
        model,
        source_latent,
        source_latent_b=None,
        ref_boost: float = 1.0,
        ref_boost_a: float = 1.0,
        fit_mode: str = "fit",
        ref_boost_mask=None,
        vae=None,
        source_image=None,
        source_image_b=None,
        target_latent=None,
        **_future,
    ) -> io.NodeOutput:
        if _future:
            print(
                "[Krea2 Edit (source patch)] WARNING: workflow provides unknown "
                f"inputs ({', '.join(sorted(_future))}). Update ComfyUI-Reaper "
                "and restart ComfyUI. Continuing without them.",
                flush=True,
            )
        patched = model.clone()
        src_samples = model.model.process_latent_in(source_latent["samples"])
        if source_latent_b is not None:
            src_samples = [
                src_samples,
                model.model.process_latent_in(source_latent_b["samples"]),
            ]

        pixel_cache = {}
        model_core = model.model
        state = {"announced": False}

        if fit_mode == "fit" and (vae is None or source_image is None):
            print(
                "[Krea2 Edit (source patch)] WARNING: fit mode needs both VAE "
                "and Source Image; using the latent crop path.",
                flush=True,
            )

        primed = None
        if vae is not None and source_image is not None:
            if target_latent is not None:
                target_height = target_latent["samples"].shape[-2]
                target_width = target_latent["samples"].shape[-1]
                print(
                    "[Krea2 Edit (source patch)] pre-encoding sources at "
                    f"{target_height * 8}x{target_width * 8}px "
                    f"(fit mode={fit_mode})",
                    flush=True,
                )
                _fit_encode_image(
                    source_image,
                    vae,
                    target_height,
                    target_width,
                    pixel_cache,
                    ("a", target_height, target_width),
                    fit_mode,
                )
                if source_image_b is not None:
                    _fit_encode_image(
                        source_image_b,
                        vae,
                        target_height,
                        target_width,
                        pixel_cache,
                        ("b", target_height, target_width),
                        fit_mode,
                    )
                primed = (target_height, target_width)
            else:
                print(
                    "[Krea2 Edit (source patch)] NOTE: connect Target Latent "
                    "to pre-encode the source before sampling.",
                    flush=True,
                )

        def wrapper(executor, x, timesteps, context, *wrapper_args, **kwargs):
            transformer_options = kwargs.pop("transformer_options", None)
            if transformer_options is None:
                transformer_options = {}
                for argument in reversed(wrapper_args):
                    if isinstance(argument, dict):
                        transformer_options = argument
                        break

            diffusion_model = executor.class_obj
            source = src_samples
            if vae is not None and source_image is not None:
                target = _to_4d(x)
                target_height, target_width = target.shape[-2:]
                if not state["announced"]:
                    state["announced"] = True
                    print(
                        "[Krea2 Edit (source patch)] pixel path active "
                        f"(fit mode={fit_mode})",
                        flush=True,
                    )
                    if primed is not None and primed != (
                        target_height,
                        target_width,
                    ):
                        print(
                            "[Krea2 Edit (source patch)] WARNING: Target Latent "
                            "does not match the sampling resolution; the VAE "
                            "will run during sampling.",
                            flush=True,
                        )
                source = model_core.process_latent_in(
                    _fit_encode_image(
                        source_image,
                        vae,
                        target_height,
                        target_width,
                        pixel_cache,
                        ("a", target_height, target_width),
                        fit_mode,
                    )
                )
                if source_image_b is not None:
                    source = [
                        source,
                        model_core.process_latent_in(
                            _fit_encode_image(
                                source_image_b,
                                vae,
                                target_height,
                                target_width,
                                pixel_cache,
                                ("b", target_height, target_width),
                                fit_mode,
                            )
                        ),
                    ]

            return krea2_edit_forward(
                diffusion_model,
                x,
                timesteps,
                context,
                source,
                transformer_options,
                ref_boost=ref_boost,
                ref_boost_a=ref_boost_a,
                ref_boost_mask=ref_boost_mask,
                ref_native=(
                    fit_mode == "fit"
                    and vae is not None
                    and source_image is not None
                ),
                pos_mode="stride1" if fit_mode == "fit" else "anchor",
            )

        transformer_options = patched.model_options.setdefault(
            "transformer_options", {}
        )
        comfy.patcher_extension.add_wrapper_with_key(
            comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL,
            "reaper_krea2_edit",
            wrapper,
            transformer_options,
        )
        return io.NodeOutput(patched)


__all__ = ["ReaperKrea2EditModelPatch"]
