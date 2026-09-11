# ComfyUI-Reaper

A collection of 86 modern ComfyUI V3 / Nodes 2.0 custom nodes for image, mask, model, latent, text, face, flow-control, Krea2, inpainting, and outpainting workflows.

Current release: **0.20.2**

All nodes are grouped beneath the `Reaper` menu. Stable internal node IDs are retained when nodes move between categories so existing workflows continue to load.

## Installation

Clone the repository into ComfyUI's `custom_nodes` directory:

```powershell
cd ComfyUI\custom_nodes
git clone https://github.com/Redman-Labs/ComfyUI-Reaper.git
```

Install Reaper's Python dependencies with the Python environment that launches ComfyUI. For the EZi/portable installation used by this project:

```powershell
D:\AI\ComfyUI\python_embeded\python.exe -m pip install -r D:\AI\ComfyUI\ComfyUI\custom_nodes\ComfyUI-Reaper\requirements.txt
```

Fully stop and restart ComfyUI after installing or updating the pack. Refreshing the browser alone does not reload Python nodes.

## Prompt Progress Bar

Reaper includes an rgthree-inspired Prompt Progress Bar that shows queued work, overall node progress, the currently executing node, and sampler-step progress. Click the bar while a prompt is running to center the active node in the workflow.

Configure it in **ComfyUI Settings → Reaper → Prompt Progress Bar**:

- **Enable Prompt Progress Bar** shows or hides the bar.
- **Position** places it at the top or bottom of the ComfyUI window.
- **Height** uses a slider with an integer box on its right and sets the height from 4 to 100 pixels.
- **Node Progress Bar Color** opens a color picker for overall workflow-node progress.
- **Step Progress Bar Color** opens a color picker for progress within the active node.

## Categories and nodes

The catalog below is generated from the currently registered node schemas.

### Reaper/Face Utils (8)

Face detection, alignment, filtering, and semantic masks.

- **BiSeNet Face Mask (Reaper)** — Creates semantic masks for selected facial and surrounding regions with the local BiSeNet face-parsing model. Requires models/bisenet/79999_iter.pth.
- **Crop Faces (Reaper)** — Aligns and crops every FACE entry into a square batch. It also creates a matching mask and returns the affine WARP metadata for compatible workflows.
- **Detect Face By Index (Reaper)** — Detects faces, orders them from left to right, and returns one face by its zero-based index. An optional visual-presentation classifier can be applied before or after index selection.
- **Detect Faces (Reaper)** — Detects faces with the FaceTools YOLO model, estimates rotation-aware landmarks, and returns FACE objects for the other Face Tools nodes.
- **Gender Face Filter (Reaper)** — Uses dima806/man_woman_face_image_detection to divide FACE objects by the selected model label. The model predicts visual presentation and may be inaccurate; do not treat it as identity data.
- **Jonathandinu Face Mask (Reaper)** — Creates detailed semantic face masks with jonathandinu/face-parsing from Hugging Face. The model downloads on first use and generally consumes more memory than BiSeNet.
- **Ordered Face Filter (Reaper)** — Sorts detected faces by pixel area, returns a selected range, and sends every other face to Rest.
- **Person Mask Generator (Reaper)** — Creates a combined mask from MediaPipe person segmentation classes and precise facial landmarks. Enabled regions are unioned.

### Reaper/Flow Control (8)

Lazy branches, execution gating, routing, and explicit dependencies.

- **Continue Flow (Reaper)** — Passes Value through when Continue is enabled; otherwise blocks every downstream branch.
- **Execution Order (Reaper)** — Chain the Order sockets to create an explicit dependency and optionally pass another node output through unchanged.
- **Flow Select (Reaper)** — Routes Value to either the True or False output and blocks the unselected output.
- **Force Calculation (Reaper)** — Passes Value through while forcing this dependency path to recalculate on every queued run.
- **If / Elif / Else (Reaper)** — Returns the first matching branch. Add equally numbered Condition and Value sockets for each elif branch.
- **If / Else (Reaper)** — Evaluates only the selected lazy branch and returns its value.
- **Is Connected (Reaper)** — Returns true when Input supplies a non-None value. ComfyUI does not distinguish an unconnected socket from a connected socket whose evaluated value is None.
- **Switch / Case (Reaper)** — Returns the numbered case selected by Index, or Default when that case does not exist.

### Reaper/Image Utils (16)

Image loading, saving, resizing, filtering, comparison, previews, and pause workflows.

- **Color Correction (Reaper)** — Adjusts gamma, contrast, exposure, offset, hue, saturation, and value using Torch, optionally limited by a mask.
- **Color Match** — Transfer color grading from a reference image onto a target image. CPU methods (color-matcher): mkl, hm, reinhard, mvgd, hm-mvgd-hm, hm-mkl-hm. GPU methods: reinhard_lab_gpu (Kornia), wavelet (Haar wavelet LAB transfer), scattersort (exact histogram matching). CPU inputs are normalized to finite RGB values for stable processing; invalid results fall back to the target image. Based on KJNodes ColorMatch.
- **Crop Image to Mask (Reaper)** — Crops an image and mask to the smallest shared bounding box containing all active mask pixels. Optional padding expands the crop, and the final width and height are expanded to the requested multiple whenever the source-image boundaries allow it. The Uncrop Info output stores the coordinates and original size needed by a future restoration or uncrop node.
- **Image Compare Advanced (Reaper)** — Displays two images in an interactive on-node viewer with single-image, left/right wipe, reversed wipe, up/down wipe, opacity overlay, and pixel-difference modes. Either input may be omitted without causing an execution error.
- **Image Compare Simple** — Compares two images with a hover slider or click mode. Connect Image 1 and Image 2 to compare, or connect a single batch to auto-split.
- **Image Filter Adjustment** — Apply brightness, contrast, saturation, sharpness, blur, white balance (temp/tint/hue), solarize, LUT, vignette, chromatic aberration, and film grain effects.
- **Image Preview** — Displays an image or image batch in a resizable DOM preview and passes the images through unchanged.
- **Image Upscale w/wo Model (Reaper)** — Load an upscale model and apply it to the image in one node. Optionally rescale the output to a target multiplier using a standard resampling filter (e.g. use a 4× model but produce 2× output).
- **Load Image (Reaper)** — Loads still or multi-frame images from ComfyUI's input folder, extracts transparency as a mask, optionally resizes both, and emits a compact metadata bundle.
- **Load Image Info (Reaper)** — Unpacks the typed metadata bundle from Load Image (Reaper).
- **Load Images from Folder (Reaper)** — Load many images from any folder on disk and feed them through your workflow one at a time - one finished result per image. Pick all, the first N, or hand-pick specific images in a thumbnail gallery. Same resize options as Load Image Reaper (max megapixels, longest side, scale by, fit inside, crop to fill, match aspect ratio). Outputs are a list: image, mask, width, height, filename, index, total.
- **Pause Image** — An inline image gate for inspecting a generated image before running expensive downstream work. Pause captures and previews the image, Continue reloads that exact snapshot while skipping upstream generation, Regenerate captures a new image, and Pass runs the full workflow normally. Snapshots live in ComfyUI's temporary folder and expire when that folder is cleared.
- **Pause Image Compare (Reaper)** — Combines the Pause Image workflow gate with the interactive Image Compare viewer. Image 1 is the gated image: Pause captures it, Continue reloads the approved snapshot while skipping its upstream generation, Regenerate captures a new version, and Pass runs normally. Image 2 is a comparison reference and is never used as the pause snapshot.
- **Resize Image & Mask (Reaper)** — Resizes an image and mask together using ComfyUI's built-in resize modes. The image determines the final dimensions and the mask is guaranteed to match them exactly.
- **Resize Image to Pixels (Reaper)** — Resizes an image to approximately the requested megapixel count while preserving its aspect ratio. The calculated width and height are rounded to valid multiples, making the output suitable for latent, model, and tiled image workflows.
- **Save Image (Reaper)** — Save Image Reaper - save images to any folder on your computer, not just ComfyUI's output folder. Type or paste a path, or click Browse to pick a folder with your system's own folder dialog; leave the field empty to use the output folder. The filename field supports tokens and shows a live 'Will save as' preview of the exact file that will be written. Tokens: %input% (the wired name input, e.g.

### Reaper/In-Outpainting Utils (4)

Crop/stitch workflows for inpainting and padding/recomposition workflows for outpainting.

- **Inpaint Crop (Reaper)** — Inpaint Crop Reaper - the easy way to set up an inpaint. Open the fullscreen editor and paint a mask over the area you want to fix (brush, erase, clear, invert, adjustable brush size). The node automatically finds the box around your mask, adds a context margin, and crops a model-friendly piece (sized to a multiple of 8, scaled toward your target so even a small masked area gets enough resolution).
- **Inpaint Stitch (Reaper)** — Inpaint Stitch Reaper - paste your inpainted crop back onto the original image at the exact spot it came from, blended so the seam disappears. Wire the crop_info output of Inpaint Crop Reaper into crop_info here, and wire your inpainted crop (after the model) into image. The node resizes the crop back to the region and blends only the painted area by default, so everything outside the mask stays pixel-perfect.
- **Outpaint (Reaper)** — Pads an image with a solid color so an outpainting model can fill the new area in, then optionally scales the result down to a megapixel limit and reports the final size. Mid grey is the default fill. Any color works, but a strongly colored fill can tint the whole generated image, because a model trained to replace it learns the color as well as the shape. Grey is neutral, so it has no hue to bleed.
- **Outpaint Stitch (Reaper)** — Puts the pristine original image back onto an outpaint result, keeping only the part the model newly generated. Use it after Outpaint Reaper when you had to scale a large image down for the model: the original half comes back at full quality instead of the softened, downscaled version that went through the model.

### Reaper/Krea2 Utils (5)

Krea2 prompt enhancement, weighted attention, and training-matched image editing. This category contains the Krea2T enhancer nodes moved from Model Utils, plus the weighted text encoder and Krea2 Edit ports.

- **Krea2 Edit (grounded encode)** — Encodes an edit instruction together with source imagery using Krea2's training-matched Qwen3-VL semantic path.
- **Krea2 Edit (source patch)** — Adds the krea2_edit in-context source-preservation path (source latent as frame=1 tokens) to a Krea2 model.
- **Krea2T Enhancer (Reaper)** — Patches Krea2's text-fusion path during diffusion sampling to strengthen prompt-detail adherence. The patch targets Krea2's 12 x 2560 text-conditioning layout and safely skips models that do not match it.
- **Krea2T Enhancer Advanced (Reaper)** — Applies the Krea2T prompt-adherence enhancement and adds a direct post-txtmlp Text Scale control for fused text-token strength. All temporary runtime method patches are restored after each model call.
- **Krea2T Text Encode - Weighted** — Encodes (phrase:weight) as ordinary Krea2 text, then applies the weight inside shared attention. Only image queries reading the phrase's text keys receive log(weight); conditioning rows and sequence length are unchanged.

### Reaper/Latent Utils (4)

Latent transforms, learned upscaling, and lightweight Wan previews.

- **Latent Upscale (Reaper)** — Upscales Wan 2.1 video latents by 2x spatially with the bundled compact neural latent upscaler while preserving all other keys in the LATENT dictionary.
- **Latent Upscale by Model** — Upscales image or video LATENT samples with a compact SesquiLSR neural super-resolution model. Choose the format that matches the latent producer, then select any spatial scale from 1x to 2x. The node preserves the LATENT dictionary and resizes its noise mask, if present. SDXL mode is not compatible with SD 1.5 latents.
- **Scale / Unscale Latents (Reaper)** — Applies or reverses the selected native ComfyUI latent format's scale and shift transformation while preserving the rest of the LATENT dictionary.
- **Wan Latent Preview (Reaper)** — Creates a fast approximate RGB preview of Wan 2.1 latents with the bundled lightweight projector. This is for visual inspection and is not a replacement for full VAE decoding.

### Reaper/Mask Utils (2)

Mask conversion and geometry.

- **Mask to Image (Reaper)** — Converts a mask to an RGB image using foreground and background colors.
- **Mask to Rectangle (Reaper)** — Detects every disconnected foreground region in a mask and converts each region into its own axis-aligned rectangle. Independent positive or negative padding can be applied to the top, bottom, left, and right edges. The node returns both a combined filled rectangle mask and a copy of the source image with separate border boxes or translucent filled rectangles.

### Reaper/Model Utils (3)

LoRA management and tiled diffusion-model execution.

- **LoRA Loader (Reaper)** — Stack multiple LoRAs with independent model and CLIP strengths. The info panel can read local metadata, manage trigger words and previews, and optionally query Civitai when requested.
- **Model Tile Patch (Reaper)** — Patches a diffusion model to evaluate its denoiser in overlapping temporal and spatial tiles, blend the results, and optionally base ComfyUI's memory estimate on one tile.
- **Model Visualize Tiles (Reaper)** — Draws each calculated one-dimensional tile and its blending mask as an image row, making overlap and dropped regions easy to inspect.

### Reaper/Pass Throughs (15)

Typed and wildcard passthrough nodes for organizing and controlling graphs.

- **Any Passer** — Passes a value of any ComfyUI datatype through unchanged.
- **Any Passer Purge** — Optionally unloads models and clears ComfyUI's cache, then passes any datatype through unchanged.
- **Audio Passer** — Passes audio data through unchanged.
- **Boolean Passer** — Passes a boolean through, or returns false when no input is connected.
- **Clip Passer** — Passes clip data through unchanged.
- **Conditioning Passer** — Passes conditioning data through unchanged.
- **ControlNet Passer** — Passes controlnet data through unchanged.
- **Float Passer** — Passes a floating-point value through unchanged.
- **Image Passer** — Passes image data through unchanged.
- **Int Passer** — Passes an integer value through unchanged.
- **Latent Passer** — Passes latent data through unchanged.
- **Mask Passer** — Passes mask data through unchanged.
- **Model Passer** — Passes model data through unchanged.
- **String Passer** — Passes a string value through unchanged.
- **VAE Passer** — Passes vae data through unchanged.

### Reaper/Prompt & Text (3)

Editable text gates, comments, and ordered find/replace processing.

- **Find and Replace (Reaper)** — Intercepts connected text, applies an ordered list of find-and-replace rules, and passes the edited text downstream. The interactive node UI supports adding, disabling, deleting, and dragging rules; case-sensitive, whole-word, regular-expression, and tidy modes; and a persistent live before-and-after preview. Rules run from top to bottom, so each rule sees the result produced by the preceding rule.
- **Pause Text (Reaper)** — Pauses a workflow so generated text can be reviewed and edited before downstream nodes run. Continue sends the edited text downstream while skipping its upstream generator. Regenerate requests fresh text, Pass runs end to end, and Keep reuses the current edited text on subsequent runs. The editor supports // line comments and /* block comments */;
- **Text With Comments (Reaper)** — Provides a multiline text field where // line comments and /* block comments */ can be used for notes. Comments are removed from the text sent to downstream nodes, while comment markers inside quoted strings are preserved.

### Reaper/Switches (8)

Lazy two-way selectors for common ComfyUI data types, plus a dynamic 32-input wildcard selector.

- **Any Switch Advanced (Reaper)** — An any-type switch adapted from Switch Pixaroma. Its custom Classic and Nodes 2.0 interface provides per-row enable toggles, editable input labels, and a trailing empty row that grows as inputs are connected. It supports up to 32 inputs and evaluates only the selected lazy branch.
- **Any Switch (Reaper)** — Selects one of two optional inputs of any ComfyUI data type. The two inputs may hold different types, and only the selected connected branch is evaluated before its value is passed through.
- **CLIP Switch (Reaper)** — Selects CLIP 1 or CLIP 2 and passes only the selected text encoder object to the output using lazy branch evaluation.
- **Image Switch (Reaper)** — Selects Image 1 or Image 2 and passes only the selected image or image batch to the output using lazy branch evaluation.
- **Latent Switch (Reaper)** — Selects Latent 1 or Latent 2 and passes only the selected LATENT value to the output. The inputs use lazy evaluation, so an unselected connected branch is not calculated. An optional purge can unload models and clear cached memory immediately before the selected latent is returned.
- **Mask Switch (Reaper)** — Selects Mask 1 or Mask 2 and passes only the selected mask tensor to the output using lazy branch evaluation.
- **Model Switch (Reaper)** — Selects Model 1 or Model 2 and passes only the selected diffusion model patcher to the output using lazy evaluation.
- **VAE Switch (Reaper)** — Selects VAE 1 or VAE 2 and passes only the selected native ComfyUI VAE object to the output using lazy branch evaluation.

### Reaper/Tools (7)

Graph-control and virtual Set/Get utilities.

- **Fast Bypasser (Reaper)** — Quickly bypass or enable connected nodes without executing itself.
- **Fast Muter (Reaper)** — Quickly mute or enable connected nodes without executing itself.
- **GetNode (Reaper)** — Reads the value from a named SetNode (Reaper) without drawing a cable across the workflow. Sets in parent graphs are visible inside nested subgraphs.
- **Mute / Bypass Repeater (Reaper)** — Repeats its Active, Muted, or Bypassed mode to connected nodes.
- **Node Collector (Reaper)** — Collects multiple graph-control connections into one output.
- **Reroute** — A frontend-only, type-aware reroute adapted from rgthree-comfy. Its single **Reroute Settings** menu opens a ComfyUI-styled panel for label visibility, resizing, exact dimensions, twelve connection layouts, rotations, horizontal or vertical flips, and cloning before or after the current reroute. Popup accents follow **Settings → Reaper → Default Style**.
- **SetNode (Reaper)** — Stores any connection under a name for one or more Get Reaper nodes. This is a virtual editor node, so its passthrough resolves directly to the original source.

### Reaper/VAE Utils (3)

VAE loading, offload control, and image/video latent decoding.

- **Disable VAE Offload (Reaper)** — Changes the offload policy of an already loaded VAE without modifying the VAE object used by other workflow branches.
- **Load VAE (Reaper)** — Loads a VAE using ComfyUI's current native loader, including Wan video/upscale VAE channel detection, approximate TAEs, metadata handling, and device reload support. It also lets you choose whether the VAE stays fully loaded during use.
- **VAE Decode (Reaper)** — Decodes image or video latents with optional spatial and temporal tiling, then automatically rearranges packed VAE output channels for upscale VAEs such as the Wan 2x VAE.

## Models and runtime data

Some nodes need model files in addition to Python packages:

- **Detect Faces** uses `ComfyUI/models/ultralytics/bbox/face_yolov8m.pt` and `ComfyUI/models/landmarks/fan2_68_landmark.onnx`.
- **BiSeNet Face Mask** uses `ComfyUI/models/bisenet/79999_iter.pth`.
- **Jonathandinu Face Mask** downloads its Hugging Face model on first use.
- **Person Mask Generator** downloads its MediaPipe models on first use under `ComfyUI/models/mediapipe/`.
- **Latent Upscale**, **Wan Latent Preview**, and **Latent Upscale by Model** use the weights bundled under this repository's `models/` directory.
- **Save Image** stores its Civitai model-hash cache in ComfyUI's user directory when available.

## Python dependencies

Reaper declares the following direct third-party dependencies in `requirements.txt`:

- color-matcher
- Kornia
- MediaPipe
- ONNX Runtime
- OpenCV contrib
- scikit-image
- SciPy
- Transformers
- Ultralytics
- psutil
- NVIDIA Management Library bindings
- pyspellchecker

PyTorch, TorchVision, NumPy, Pillow, safetensors, einops, aiohttp, and Spandrel are supplied by ComfyUI. `spandrel_extra_arches` is optional and is loaded only when installed.

## Project structure

```text
ComfyUI-Reaper/
├── __init__.py
├── routes.py
├── resource_monitor.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── LICENSE
├── nodes/
│   ├── __init__.py
│   ├── _discovery.py
│   ├── global_configs.py
│   ├── _helpers/
│   │   ├── face_tools/
│   │   ├── _inpaint_helpers.py
│   │   ├── _load_images_folder.py
│   │   ├── _lora_helpers.py
│   │   ├── _path_guard.py
│   │   ├── _rlabs_resize_helpers.py
│   │   ├── _save_helpers.py
│   │   ├── _types.py
│   │   └── _vae_utils_models.py
│   ├── face_utilities/                 # 8 node modules + shared helpers
│   ├── flow_utilities/                 # 8 node modules + shared helpers
│   ├── image_utilities/                # 16 node modules, Civitai metadata + shared helpers
│   ├── in_out_painting_utilities/      # 4 node modules + shared helpers
│   ├── krea2_utilities/
│   │   ├── node_krea2_edit_grounded_encode.py
│   │   ├── node_krea2_edit_source_patch.py
│   │   ├── node_krea2t_attention_weighted_phrase.py
│   │   ├── node_krea2t_enhancer.py
│   │   ├── node_krea2t_enhancer_advanced.py
│   │   └── shared_krea2_utilities/
│   ├── latent_utilities/               # 4 node modules + shared helpers
│   ├── mask_utilities/                 # 2 node modules + shared helpers
│   ├── model_utilities/                # 3 node modules + shared helpers
│   ├── pass_throughs/                  # 15 node modules + shared helpers
│   ├── prompt_text_utilities/          # 3 node modules + shared helpers
│   ├── switch_utilities/               # 8 node modules + shared helpers
│   ├── utilities/                      # 6 modules; SetNode/GetNode share one module
│   └── vae_utilities/                  # 3 node modules + shared helpers
├── js/
│   ├── advanced_any_switch/
│   ├── compare/ and compare_simple/
│   ├── find_replace/
│   ├── framework/
│   ├── image_info/, image_masks/, and image_preview/
│   ├── inpaint_crop/
│   ├── load_image/ and load_images_folder/
│   ├── lora_loader/
│   ├── outpaint/ and outpaint_stitch/
│   ├── pass_throughs/
│   ├── pause_image/, pause_image_compare/, and pause_text/
│   ├── prompt_progress_bar/
│   ├── resource_monitor/
│   ├── reroute/
│   ├── save_image/
│   ├── set_get/
│   ├── settings/
│   └── shared/
├── models/
│   ├── sesqui_lsr/
│   │   ├── upscaler_Flux.safetensors
│   │   ├── upscaler_Flux2.safetensors
│   │   ├── upscaler_SDXL.safetensors
│   │   └── upscaler_Wan21.safetensors
│   └── vae_utils/
│       ├── wan21_latent_projector.safetensors
│       └── wan21_latent_upscale_2x.safetensors
├── assets/
│   ├── icons/
│   └── reaper_logo files
└── licenses/                            # Third-party attribution files
```

Every category package auto-discovers files named `node_*.py`. Shared implementations stay in category-specific `shared_*_utilities` packages and are not registered as nodes.

## Attribution and licenses

ComfyUI-Reaper itself is distributed under the GNU General Public License v3. Third-party ports and bundled components retain their original attribution files under `licenses/`:

- `a-person-mask-generator-MIT.txt`
- `comfy-mtb-MIT.txt`
- `ComfyUI_Eclipse-Apache-2.0.txt`
- `comfyui_facetools_LICENSE`
- `comfyui_sunxAI_facetools_LICENSE`
- `ComfyUI-Crystools-MIT.txt`
- `comfyui-krea2edit-Apache-2.0.txt`
- `ComfyUI-Krea2T-Enhancer-MIT.txt`
- `ComfyUI-Pixaroma-Find-Replace-MIT.txt`
- `ComfyUI-Pixaroma-MIT.txt`
- `comfyui-rvtools-v2-Apache-2.0.txt`
- `ComfyUI-VAE-Utils-MIT.txt`
- `SesquiLSR-MIT.txt`
- `text-node-with-comments-MIT.txt`
- `rgthree-comfy-MIT.txt`

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Links

- [GitHub repository](https://github.com/Redman-Labs/ComfyUI-Reaper)
- [Issue tracker](https://github.com/Redman-Labs/ComfyUI-Reaper/issues)
- [Changelog](CHANGELOG.md)
