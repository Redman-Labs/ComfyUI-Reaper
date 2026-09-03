# ComfyUI Reaper Nodes

## Face Tools

The Face Tools category includes modern ComfyUI nodes for rotation-aware face
detection, aligned crops, ordered and model-label filtering, and semantic face
masks:

- Detect Faces (Reaper)
- Detect Face By Index (Reaper)
- Crop Faces (Reaper)
- Ordered Face Filter (Reaper)
- Gender Face Filter (Reaper)
- BiSeNet Face Mask (Reaper)
- Jonathandinu Face Mask (Reaper)

Detect Faces expects `face_yolov8m.pt` under `models/ultralytics/bbox` and
`fan2_68_landmark.onnx` under `models/landmarks`. BiSeNet Face Mask additionally
expects `79999_iter.pth` under `models/bisenet`. The Jonathandinu model is
downloaded from Hugging Face on first use. Warp Faces Back and Merge Warps are
not included in this port.

A collection of ComfyUI V3 custom nodes for mask and image workflows.

## Included nodes

### Load Image

Loads uploaded, pasted, dragged, or selected still and multi-frame images.
The complete compact Load Image Mini interface is included: inline preview,
upload/paste toolbar, file picker, input/output dimension cards, clipspace and
Mask Editor integration, per-node accent controls, and the floating gear
settings panel. Transparency is converted to ComfyUI's inverted mask
convention. The settings panel provides Off, Max Megapixels, Longest Side,
Scale By, Fit Inside, Crop to Fill, and Match Ratio modes with resampling,
dimension snapping, crop anchoring, and upscale controls. It outputs the image
plus a typed metadata bundle.

### Load Image Info

Unpacks the typed bundle from Load Image into image, alpha-derived mask, final
width, final height, and source filename outputs.

### Color Correction

Applies GPU-capable Torch color correction with gamma, contrast, exposure,
offset, hue, saturation, and value controls. Correction can be limited to an
optional mask, output values can be clamped, and CPU execution remains
available when GPU processing is disabled.

### Mask to Image

Converts a mask batch into RGB images using configurable foreground and
background colors. An optional invert control swaps which mask areas receive
the foreground color.

### A Person Mask Generator

Creates a single combined mask from MediaPipe person segmentation and precise
facial landmarks. Person controls include face, background, hair, body/skin,
and clothes. Landmark controls include left/right eyebrows, eyes, pupils, and
lips, with configurable confidence, multi-face detection, and optional refined
segmentation. All enabled regions are unioned into the output mask, which can
optionally be inverted.

### Reaper - Mask to Rectangle

Detects every disconnected mask region, creates a separate padded rectangle
for each region, returns the combined rectangle mask, and optionally draws
border boxes or translucent rectangles on the source image.

### Reaper - Crop Image to Mask

Crops an image and its mask to the union bounding box of all active mask
pixels. The node supports equal padding, expands the output dimensions to a
requested multiple when possible, and returns `CROP_INFO` metadata for a
future compatible uncrop/restoration node.

### Reaper - Resize Image to Pixels

Resizes an image or image batch to an approximate target megapixel count
while preserving its aspect ratio. The output width and height are rounded
to a requested multiple. Auto interpolation uses Lanczos when shrinking and
Bilinear when growing.

### Pause Image

Pauses an image workflow at an inline preview gate. Continue resumes from the
captured snapshot without rerunning upstream generation, Regenerate captures a
new image, and Pass runs the complete workflow normally. The frontend also
provides Copy, Save Disk, Save Output, and Open controls.

### Pause Text

Pauses a text workflow so generated text can be reviewed and edited before
downstream processing. Continue uses the approved text without rerunning its
upstream generator, Regenerate requests fresh text, Pass runs end to end, and
Keep reuses the current edit.

### Text With Comments

Provides a multiline text field that supports `//` line comments and
`/* block comments */`. Comments are removed from the text sent downstream,
while matching comment markers inside quoted strings are preserved.

### Find and Replace

Applies an ordered collection of literal or regular-expression replacements
to connected text. Its interactive interface supports draggable rules,
per-rule enable controls, case and whole-word matching, regex mode, automatic
text tidying, reset confirmation, and a persistent live before/after preview.

### Image Compare

Displays two optional images in an interactive viewer with single-image,
left/right, reversed, up/down, opacity-overlay, and difference modes. The
viewer includes copy and save controls and safely handles either input being
absent.

### Image Pass Through

Accepts an image or image batch and returns the exact same tensor unchanged.
It can be used to organize, reroute, or document image connections without
altering pixels, dimensions, batches, or metadata.

### Pause Image Compare

Combines the Pause Image approval gate with the full Image Compare viewer.
Image 1 is captured, approved, and passed downstream; Image 2 is an optional
comparison reference. The Pause Image Copy, Save Disk, Save Output, and Open
controls always operate on Image 1. Its complete frontend implementation is
self-contained under `js/pause_image_compare/` and does not depend on the
Pause Image or Image Compare feature folders.

### Flow Control

The Flow Control category contains modern V3 implementations of If / Else,
If / Elif / Else, Switch / Case, Continue Flow, Flow Select, Force
Calculation, Execution Order, and Is Connected. Conditional inputs use lazy
evaluation, so unselected branches are not calculated.

### Switches

The Switches category contains modern V3 implementations of Any Switch, VAE
Switch, CLIP Switch, Mask Switch, Image Switch, and Model Switch. Each node
selects between two optional inputs and evaluates only the selected connected
branch. The Any Switch accepts any ComfyUI data type; the other switches keep
strict socket types for safer workflow connections.

### Utilities

Updated V3 utilities includes two Krea2 model patches adapted from
ComfyUI-Krea2T-Enhancer:

- **Krea2T Enhancer** patches Krea2's text-fusion path during sampling to
  strengthen prompt-detail adherence.
- **Krea2T Enhancer Advanced** adds direct post-`txtmlp` text-token scaling to
  the same enhancement path.

Both nodes safely skip diffusion models that do not match Krea2's expected
`12 x 2560` text-conditioning layout and require no additional packages.

### VAE & Latent Utilities

Eight modern V3 nodes adapted from ComfyUI-VAE-Utils:

- **Load VAE** uses ComfyUI's current native VAE loader and adds an offload
  policy control.
- **Disable VAE Offload** changes that policy on a copied VAE object.
- **VAE Decode** supports optional spatial/temporal tiling and packed-channel
  pixel shuffle for upscale VAEs.
- **Latent Upscale** provides the bundled Wan 2.1 neural 2x latent upscaler.
- **Latent Upscale by Model** provides SesquiLSR neural latent upscaling from
  1x to 2x for SDXL, Flux, Flux2, Ideogram 4, and Wan-family latents.
- **Wan Latent Preview** creates a fast approximate RGB preview.
- **Tile Model Patch** evaluates diffusion models in blended spatial and
  temporal tiles.
- **Visualize Tiles** displays the calculated tile blending masks.
- **Scale / Unscale Latents** applies native ComfyUI latent-format transforms.

The category also includes **Latent Switch**, adapted from Latent Switch V2
in comfyui-rvtools_v2. It selects between two optional latent inputs, evaluates
only the selected branch, and can optionally unload models and clear cached
VRAM before returning the selected latent.

These nodes use the current ComfyUI VAE implementation instead of embedding
the source project's older VAE fork. This preserves current format detection,
metadata handling, device reload behavior, and compatibility with ComfyUI
0.29.2 and frontend 1.47.10.

## Installation

1. Remove older copies of `ComfyUI-Reaper`.
2. Extract the folder named `ComfyUI-Reaper` into:

   `ComfyUI/custom_nodes/`

3. Restart ComfyUI.
4. Search for `Reaper`.

## Project structure

```text
ComfyUI-Reaper/
├── __init__.py
├── nodes/
│   ├── __init__.py
│   ├── types.py
│   ├── node_control_flow.py
│   ├── node_crop_image_to_mask.py
│   ├── node_image_compare.py
│   ├── node_krea2t_enhancer.py
│   ├── node_latent_switch.py
│   ├── node_mask_to_rectangle.py
│   ├── node_pause_image.py
│   ├── node_pause_text.py
│   ├── node_resize_image_to_pixels.py
│   ├── node_switches.py
│   ├── node_text_with_comments.py
│   ├── node_vae_utils.py
│   └── vae_utils_models.py
├── models/
│   └── vae_utils/
├── licenses/
│   └── ComfyUI-VAE-Utils-MIT.txt
├── routes.py
├── README.md
├── CHANGELOG.md
├── requirements.txt
└── pyproject.toml.example
```

The root `__init__.py` provides the single V3 `comfy_entrypoint` for the
project. Individual node modules contain node classes only.

## Crop Image to Mask behavior

The mask threshold is fixed at `> 0.5`, matching the uploaded implementation.

For a batch, the node calculates one shared crop box around the union of all
active mask pixels. This keeps all output images and masks the same size so
they can remain in a ComfyUI batch.

If the mask is empty, the full image and mask are returned. `Uncrop Info`
contains the original keys `x`, `y`, `w`, `h`, `original_size`, and
`mask_patch`, plus additional crop and batch metadata.

The `Dimensions Multiple Of` setting expands the crop when possible. When the
source-image boundary makes the requested multiple impossible, the largest
valid in-bounds crop is returned.

## Dependencies

The person mask node requires MediaPipe, declared in `requirements.txt`. Its
official segmentation and face-landmarker models are downloaded on first use
to `ComfyUI/models/mediapipe/`. The remaining nodes use PyTorch, NumPy, Pillow,
and safetensors support supplied by ComfyUI. The two compact Wan utility
weights are bundled under `models/vae_utils/`.

Text With Comments was adapted from `text-node-with-comments` by Jan Schwalbe
under the MIT License. Its attribution is preserved in
`licenses/text-node-with-comments-MIT.txt`.

A Person Mask Generator was adapted from `a-person-mask-generator` by David B.
under the MIT License. Its attribution is preserved in
`licenses/a-person-mask-generator-MIT.txt`.

Color Correction and Mask to Image were adapted from `comfy_mtb` by Mel
Massadian under the MIT License. Its attribution is preserved in
`licenses/comfy-mtb-MIT.txt`.

Load Image and Load Image Info were adapted from the corresponding Pixaroma
nodes under the MIT License. Attribution is preserved in
`licenses/ComfyUI-Pixaroma-MIT.txt`.

Find and Replace and its complete interactive frontend were adapted from
[ComfyUI-Pixaroma](https://github.com/pixaroma/ComfyUI-Pixaroma) under the MIT
License. Attribution is preserved in
`licenses/ComfyUI-Pixaroma-Find-Replace-MIT.txt`.

The Krea2T Enhancer nodes were adapted from ComfyUI-Krea2T-Enhancer by
capitan01R under the MIT License. Its attribution is preserved in
`licenses/ComfyUI-Krea2T-Enhancer-MIT.txt`.

The VAE utility logic and bundled models were adapted from
ComfyUI-VAE-Utils by spacepxl under the MIT License. Its required attribution
is preserved in `licenses/ComfyUI-VAE-Utils-MIT.txt`.

Latent Upscale by Model and its bundled model weights were adapted from
[SesquiLSR](https://github.com/LoganBooker/SesquiLSR) by Logan Booker under
the MIT License. Its attribution is preserved in
`licenses/SesquiLSR-MIT.txt`.

## Registry metadata
