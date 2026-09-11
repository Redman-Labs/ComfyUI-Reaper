# Changelog

## Unreleased

## 0.20.0 - 2026-09-10

- Added V3 ports of `Krea2 Edit (source patch)` and `Krea2 Edit (grounded
  encode)` under `Reaper/Krea2 Utils`, preserving their original display titles and
  Apache 2.0 attribution.
- Added the V3 `Krea2T Text Encode - Weighted` node under `Reaper/Krea2 Utils`,
  adapted from ComfyUI-Krea2T-Enhancer's attention-weighted phrase encoder.
- Moved both Krea2T Enhancer nodes and their shared implementation into a
  dedicated `Reaper/Krea2 Utils` category and `nodes/krea2_utilities` package.
- Renamed the Krea2 category to `Reaper/Krea2 Utils` while preserving stable
  internal node IDs for existing workflows.
- Made the mask input on `Resize Image & Mask (Reaper)` optional. When no mask
  is connected, the node resizes the image without requiring or processing one.
- Added Civitai metadata extraction support for `Save Image (Reaper)`, including
  graph traversal, metadata helpers, and model-hash caching.
- Updated package metadata, repository URLs, dependency declarations, and the
  README's complete 85-node catalog and current project structure.
- Added a live Resource Monitor to the ComfyUI menu for CPU, RAM, NVIDIA GPU,
  VRAM, GPU temperature, and output-disk usage. Each metric and the polling
  interval can be configured under Reaper settings.
- Added optional-safe NVML monitoring, multi-GPU display support, and Crystools
  attribution under its MIT license.
- Fixed duplicate Resource Monitor groups caused by repeated frontend module
  evaluation, prevented stale requests from repainting the menu, and exposed
  explicit CPU, RAM, GPU, VRAM, and TEMP visibility switches.
- Registered Resource Monitor controls through ComfyUI's live settings manager,
  added Pixel Width and Pixel Height controls, and removed Disk monitoring.
- Added live NVIDIA GPU board-power monitoring in watts, scaled against the
  active power limit, with a dedicated visibility setting.
- Added a translated, modern ComfyUI V3 port of Detect Face By Index from
  comfyui_sunxAI_facetools. It supports left-to-right indexing, optional
  presentation filtering, filter/index priority, exclusion masks, and a
  `has_face` result, with detailed descriptions and tooltips.
- Fixed Convex Hull masking in Crop Faces on MediaPipe 0.10.35 by replacing
  the removed legacy `mp.solutions.face_mesh` API with the supported Tasks
  `FaceLandmarker` API.
- Added modern ComfyUI V3 ports of Detect Faces, Crop Faces, Ordered Face
  Filter, Gender Face Filter, BiSeNet Face Mask, and Jonathandinu Face Mask
  under `Reaper/Face Tools`, with detailed node and input tooltips.
- Included the FaceTools detection, landmark, and parsing support code under its
  MIT license. Warp Faces Back and Merge Warps are intentionally excluded.

## 0.19.2

- Fixed UTF-8 corruption in the Load Image frontend that replaced arrow,
  multiplication, and close glyphs with garbled text.
- Isolated the copied Pixaroma frontend helpers with the loader under
  `js/load_image/` so they do not overwrite Reaper' shared UI modules.
- Restored the Reaper `Default Style` setting and connected the loader's
  global accent option to that existing setting.
- Made the internal `LoadImageMiniState` field socketless as well as hidden so
  it cannot occupy a visible input row.

## 0.19.1

- Replaced the initial schema-only Load Image port with the complete Load Image
  Mini Pixaroma JavaScript interface adapted for `Load Image (Reaper)`.
- Ported the compact toolbar, upload/paste/drop handling, native preview,
  input/output dimension cards, Mask Editor and clipspace integration, canvas
  resizing, per-node accent controls, and floating resize settings panel.
- Restored the source node's hidden JSON state contract and exact shared resize
  engine while retaining current V3 registration and typed image-info output.
- Namespaced prompt, graph-loading, execution, and accent hooks so the
  Reaper and Pixaroma versions can coexist safely.

## 0.19.0

- Added current ComfyUI V3 ports of `Load Image Mini Pixaroma` and `Image Info
  Pixaroma` as `Load Image (Reaper)` and `Load Image Info (Reaper)`.
- Added a native V3 image upload selector, recursive input-folder listing,
  still/multi-frame decoding, EXIF orientation, transparency-to-mask extraction,
  cache fingerprinting, and input validation.
- Replaced the source node's Pixaroma-specific hidden frontend state with
  explicit documented V3 resize controls and a typed `REAPER_IMAGE_INFO` link.
- Added seven resize modes, automatic resampling, dimension snapping, crop
  anchoring, aspect-ratio crop/pad, and optional upscaling.

## 0.18.1

- Added detailed setting tooltips to every input and output on Color Correction
  and Mask to Image, including control direction, neutral values, mask behavior,
  execution device behavior, and output interpretation.

## 0.18.0

- Added V3 ports of comfy_mtb's GPU color correction and Mask to Image nodes.
- Registered them as `Color Correction (Reaper)` and `Mask to Image (Reaper)`
  under the Reaper Image & Mask category.
- Preserved GPU/CPU selection, optional masked correction, mask inversion, and
  configurable foreground/background colors with current V3 schemas.

## 0.17.1

- Added an `Invert Mask` Enabled/Disabled control to A Person Mask Generator.
- The control defaults to Disabled and inverts the final combined mask when
  enabled.

## 0.17.0

- Added a current ComfyUI V3 port of A Person Mask Generator.
- Added left/right eyebrow, eye, pupil, and lips landmark-mask controls.
- Added multi-face landmark detection and unions all enabled segmentation and
  landmark regions into one batch-safe mask output.
- Uses the current MediaPipe Tasks API and downloads official model assets to
  `ComfyUI/models/mediapipe/` on first use.

## 0.16.13

- Shortened node display-name suffixes from `(Reaper)` and `(Reaper)` to `(Reaper)` without changing project, package, class, or node ID names.

## 0.16.12

- Merged the Reaper Image and Mask node categories into `Reaper/🎨 Image & Mask`.

## 0.16.11

- Added an `Invert Mask` True/False setting to Resize Image/Mask, defaulting to `False`.
- Inverts the final resized and aligned mask when enabled.

## 0.16.10

- Updated DynamicCombo field IDs so Nodes 2.0 displays `Width`, `Height`, `Crop`, `Multiplier`, and the remaining settings in title case with spaces.
- Capitalized Resize Type, Crop, and Scale Method dropdown choices while retaining legacy execution-key compatibility.

## 0.16.9

- Changed Resize Image/Mask setting labels to title case with spaces instead of underscores.
- Added an `Auto` scale method that selects Lanczos for upscaling and Area for downscaling.

## 0.16.8

- Split Resize Image/Mask into dedicated Image and Mask inputs.
- Added separate `Resize_Image` and `Resize_Mask` outputs and guaranteed matching output dimensions.

## 0.16.7

- Added `Resize Image/Mask (Reaper)` under `Reaper/🔳 Mask`.
- Reused ComfyUI's current V3 dynamic resize schema and built-in execution logic for Nodes 2.0 compatibility.

## 0.16.6

- SetNode now derives an empty variable name from the connected output name.
- Automatically de-duplicates generated names with `_0`, `_1`, and subsequent suffixes while preserving manual editing.

## 0.16.5

- Added the virtual SetNode (Reaper) and GetNode (Reaper) flow-control nodes.
- Added Nodes 2.0 and nested-subgraph-aware wireless connection handling.
- Migrated the backend metadata definitions to the current ComfyUI V3 schema.

## 0.16.4

- Standardized the three image and mask Python class names with the `Reaper` prefix while retaining their stable ComfyUI node IDs.

## 0.16.3

- Updated the exported Krea2T, switch, and VAE utility node-collection names
  to follow the Reaper package naming convention.

## 0.16.2

- Renamed the internal flow-control node collection from
  `CONTROL_FLOW_NODES` to `ReaperFlowNodes` throughout the package.

## 0.16.1

- Updated both Krea2T Enhancer nodes to display lowercase `model` input/output
  socket names and clearer control labels: `Enable Enhancer`, `Enhancer
  Strength`, and Advanced-only `Text Strength`.

## 0.16.0

- Added `Krea2T Enhancer (Reaper)` and `Krea2T Enhancer Advanced
  (Reaper)` under the new Utilities category.
- Migrated both model-patching nodes from ComfyUI-Krea2T-Enhancer to ComfyUI's
  V3 schema with Nodes 2.0-native controls, descriptions, tooltips, and aliases.
- Isolated their runtime wrapper/configuration keys for safe coexistence with
  the source pack and preserved the original MIT attribution.

## 0.15.3

- Reset the Pause Text search field, match count, and highlights whenever a
  fresh text payload arrives from the node's upstream input.

## 0.15.2

- Fixed Pause Text search highlights being drawn on the wrong words when
  Nodes 2.0 overrode the textarea font metrics or added a vertical scrollbar.
- The highlight mirror now follows the textarea's computed typography,
  scrollbar-adjusted client size, scrolling, and live resize changes.

## 0.15.1

- Added a compact case-insensitive search field to Pause Text below its mode
  controls. The search icon or Enter highlights every matching instance in the
  editor, displays the match count, and keeps highlights aligned while scrolling.

## 0.15.0

- Added `Image Pass Through (Reaper)` under the Image category.
- The node returns the original image tensor unchanged for workflow routing
  and organization, using ComfyUI's V3 schema and native Nodes 2.0 sockets.

## 0.14.0

- Added `Text With Comments (Reaper)` under Prompt & Text, adapted from
  `text-node-with-comments` by Jan Schwalbe.
- Migrated the node to ComfyUI's V3 schema with Nodes 2.0-native multiline
  input, detailed descriptions, tooltips, and search aliases.
- Preserved quoted strings while removing `//` line comments and `/* ... */`
  block comments, and included the original MIT attribution.

## 0.13.0

- Added six Reaper switch nodes adapted from comfyui-rvtools_v2: Any
  Switch, VAE Switch, CLIP Switch, Mask Switch, Image Switch, and Model Switch.
- Consolidated the six nodes into `nodes/node_switches.py` and placed them in
  the new Reaper Switches category.
- Migrated every switch to the ComfyUI V3 schema with native Nodes 2.0
  controls, detailed descriptions, tooltips, search aliases, and lazy branch
  evaluation.
- Reused the packaged comfyui-rvtools_v2 Apache-2.0 attribution and included a
  modification notice in the adapted module.

## 0.12.0

- Added `Latent Switch (Reaper)`, adapted from Latent Switch V2 in
  comfyui-rvtools_v2.
- Migrated the node to the ComfyUI V3 schema and placed it under the existing
  Reaper VAE & Latent category.
- Added Nodes 2.0-native controls, detailed descriptions and tooltips, lazy
  evaluation for the selected latent branch, and the original optional VRAM
  purge behavior.
- Preserved the source project's Apache-2.0 license and added a modification
  notice to the adapted node module.

## 0.11.1

- Fixed tiled decoding for Wan 2x VAEs whose decoder produces 12 packed
  channels while ComfyUI 0.29.0 reports three final image channels.
- Added a targeted packed-channel tiled path that allocates the correct
  accumulation buffer, preserves ComfyUI memory/offload handling, and applies
  the requested pixel shuffle after decoding.

## 0.11.0

- Added eight Reaper V3 VAE and latent utility nodes adapted from
  ComfyUI-VAE-Utils: Load VAE, Disable VAE Offload, VAE Decode, Latent
  Upscale, Wan Latent Preview, Tile Model Patch, Visualize Tiles, and Scale /
  Unscale Latents.
- Replaced the source project's older copied VAE implementation with the
  current native ComfyUI VAE loader and decoder behavior for compatibility
  with ComfyUI 0.29.2 and frontend 1.47.10.
- Added detailed node descriptions, input/output tooltips, Reaper node
  IDs, display names, categories, and search aliases.
- Bundled the Wan 2.1 latent upscaler and preview-projector weights required
  by the two neural utility nodes.
- Preserved the original ComfyUI-VAE-Utils MIT license attribution.

## 0.10.1

- Moved the complete Pause Image Compare frontend into its own
  `js/pause_image_compare/` folder.
- Added independent pause UI, state, pruning, and comparison-renderer modules
  for the hybrid node.
- Restored the standalone Pause Image and Image Compare frontend modules to
  single-node responsibility.

## 0.10.0

- Added `Pause Image Compare (Reaper)`.
- Combined the Pause Image gate, snapshot controls, and downstream resume
  behavior with every Image Compare viewing mode and control.
- Added an Image 2 reference input while keeping Image 1 as the sole pause,
  copy, save, open, and downstream output image.
- Generalized the pause-image frontend and prompt pruning to support either
  `image` or `image1` as the gated input.

## 0.9.0

- Added the V3 `Pause Text (Reaper)` node and its complete frontend gate,
  editing, persistence, and prompt-pruning implementation.
- Added the V3 `Image Compare (Reaper)` node and its interactive viewer,
  comparison modes, settings, copy controls, and save integration.
- Added the required shared frontend resize and help-registry modules.
- Renamed all imported source-pack identifiers and UI text to Reaper.

## 0.8.0

- Added the V3 `Pause Image (Reaper)` node.
- Added its preview UI, persistent gate state, prompt-pruning behavior,
  canvas compatibility helpers, and image-save routes.
- Renamed all imported source-pack identifiers and endpoints to Reaper.

## 0.7.0

- Added eight V3 flow-control nodes: If / Else, If / Elif / Else,
  Switch / Case, Continue Flow, Flow Select, Force Calculation,
  Execution Order, and Is Connected.
- Replaced the legacy dynamic-input dictionary with native ComfyUI V3
  autogrowing inputs.
- Added matched-type conditional sockets and current lazy-evaluation handling
  so unselected branches are not calculated.
- Updated execution blocking and forced-recalculation behavior to current
  ComfyUI APIs.

## 0.6.0

- Added `Reaper - Resize Image to Pixels`.
- Added aspect-ratio-preserving resizing by target megapixel count.
- Added Auto, Bicubic, Bilinear, Lanczos, and Nearest-Exact interpolation.
- Added configurable output-dimension rounding with `Multiple Of`.
- Added complete V3 descriptions, display names, search aliases, and tooltips.

## 0.5.0

- Added `Reaper - Crop Image to Mask`.
- Migrated the uploaded crop node to the current ComfyUI V3 schema.
- Added friendly display names, tooltips, descriptions, and search aliases.
- Added shared `CROP_INFO` type registration in `nodes/types.py`.
- Added a single project-level `ComfyExtension` and `comfy_entrypoint`.
- Refactored `MaskToRectangle` into the shared project extension.
- Added robust image/mask shape validation and singleton batch broadcasting.
- Preserved the uploaded crop-info keys for future uncrop compatibility.
- Added README, requirements, and Registry metadata template files.
