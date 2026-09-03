// ============================================================
// Inpaint Crop Reaper — node entry (open button, preview, source, persist)
// ============================================================
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { redApiUrl } from "../shared/api_url.mjs";
import { isGraphLoading } from "../shared/graph_loading.mjs";
import { InpaintCropEditor, INPAINT_PREVIEW_COLORS } from "./core.mjs";
import { registerNodeAccent } from "../shared/node_settings.mjs";
import "./paint.mjs";   // mixin: brush / mask / keys
import "./render.mjs";  // mixin: canvas render + save
import {
  createNodePreview, showNodePreview, restoreNodePreview, clearNodePreview, activateNodePreview,
  downloadDataURL, applyAdaptiveCanvasOnly,
  installCanvasZoomPassthrough,
} from "../shared/index.mjs";

const SIZE_MODE_MAP = {
  "keep shape (long side)": "keep",
  "force size (square)": "force",
  "free (multiple only)": "free",
};

// node-widget label <-> internal blend_mode key (the editor pill uses the internal key)
const BLEND_MODE_MAP = { "mask": "mask", "whole crop": "whole_crop" };

function readParams(node) {
  const g = (n) => node.widgets?.find((w) => w.name === n)?.value;
  return {
    size_mode: SIZE_MODE_MAP[g("size_mode")] || "keep",
    target: parseInt(g("target")) || 1024,
    multiple: parseInt(g("multiple")) || 8,
    context_px: g("context_px") != null ? parseInt(g("context_px")) : 24,
    mask_grow: g("mask_grow") != null ? parseInt(g("mask_grow")) : 4,
    mask_blur: g("mask_blur") != null ? parseInt(g("mask_blur")) : 4,
    blend: g("softness") != null ? parseInt(g("softness")) : 16,
    // blend_mode is now a node widget too (mirrored by the editor pill).
    blend_mode: BLEND_MODE_MAP[g("blend_mode")] || "mask",
  };
}

// friendly-label <- internal size-mode key, for writing the editor's choice back
const SIZE_MODE_LABEL = Object.fromEntries(
  Object.entries(SIZE_MODE_MAP).map(([k, v]) => [v, k]));
const BLEND_MODE_LABEL = Object.fromEntries(
  Object.entries(BLEND_MODE_MAP).map(([k, v]) => [v, k]));

function setNodeWidget(node, name, value) {
  const w = node.widgets?.find((x) => x.name === name);
  if (w && w.value !== value) { w.value = value; w.callback?.(value); }
}

// write the editor's mirrored geometry knobs back to the native node widgets
function writeBackWidgets(node, extra) {
  if (!extra) return;
  if (extra.context_px != null) setNodeWidget(node, "context_px", extra.context_px);
  if (extra.mask_grow != null) setNodeWidget(node, "mask_grow", extra.mask_grow);
  if (extra.mask_blur != null) setNodeWidget(node, "mask_blur", extra.mask_blur);
  if (extra.softness != null) setNodeWidget(node, "softness", extra.softness);
  if (extra.target != null) setNodeWidget(node, "target", extra.target);
  if (extra.multiple != null) setNodeWidget(node, "multiple", extra.multiple);
  if (extra.size_mode != null)
    setNodeWidget(node, "size_mode", SIZE_MODE_LABEL[extra.size_mode] || "keep shape (long side)");
  if (extra.blend_mode != null)
    setNodeWidget(node, "blend_mode", BLEND_MODE_LABEL[extra.blend_mode] || "mask");
}

// Give a duplicated node its own on-disk scratch space. The state_json carries
// a project_id that keys the src/mask files on disk; a duplicate (alt-drag,
// right-click Duplicate, or Ctrl+C/V) copies it verbatim, so saving from the
// copy's editor would overwrite the parent's files. If another live node of the
// same type already holds this id, re-mint it + clear the paths so the copy
// starts blank and isolated. A clean workflow load never has two nodes sharing
// an id, so this is a no-op (no write) on load -> no dirty-on-load.
function dedupeInpaintProjectId(node) {
  try {
    const w = node.widgets?.find((x) => x.name === "InpaintCropWidget");
    if (!w) return;
    let meta;
    try { meta = JSON.parse(w.value?.state_json || "{}"); } catch { return; }
    const myId = meta?.project_id;
    if (!myId) return;
    const g = node.graph || app.graph;
    const nodes = g?._nodes || g?.nodes || [];
    const collides = nodes.some((n) => {
      if (n === node || n?.comfyClass !== node.comfyClass) return false;
      const ow = n.widgets?.find((x) => x.name === "InpaintCropWidget");
      if (!ow) return false;
      let om; try { om = JSON.parse(ow.value?.state_json || "{}"); } catch { return false; }
      return om?.project_id === myId;
    });
    if (!collides) return;
    meta.project_id = "inpaint_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
    meta.src_path = "";
    meta.mask_path = "";
    w.value = { state_json: JSON.stringify(meta) };
    // Also clear the copied cached-source references, else the node-body
    // thumbnail keeps showing the parent's image (restoreNodePreview can't
    // blank an already-drawn image). Then repaint: the upstream if the copy is
    // wired, otherwise the empty placeholder.
    node._redInpaintSourceURL = null;
    if (node.properties) delete node.properties.redInpaintSource;
    if (getUpstreamImageURL(node)) node._redInpaintRefresh?.();
    else node._redInpaintClearPreview?.();
  } catch (e) { console.warn("[InpaintCrop] dedupe project id failed:", e); }
}

function buildSourceURL(part, bust) {
  if (!part || !part.filename) return null;
  // The cache-buster is part of the ROUTE handed to redApiUrl, never appended to
  // its RESULT: a hosted ComfyUI adds its auth token to the finished url, so
  // concatenating afterwards writes our param on the far side of that token
  // (see js/shared/api_url.mjs). Locally the two produce the identical string.
  return redApiUrl(`/view?filename=${encodeURIComponent(part.filename)}` +
    `&subfolder=${encodeURIComponent(part.subfolder || "")}` +
    `&type=${encodeURIComponent(part.type || "temp")}` +
    (bust ? `&t=${Date.now()}` : ""));
}

// A LoadImage combo value can be "name.png", "sub/name.png", or carry an
// annotation like "clipspace/clipboard.png [input]" (this is what PASTING into a
// LoadImage produces - a subfolder + suffix). /view wants filename + subfolder as
// SEPARATE params and no annotation, so split it; otherwise the editor 404s with
// "Failed to load the source image" (only on paste, since a plain pick has no
// subfolder/suffix). Mirrors the image-picker split used elsewhere.
function parseAnnotatedImageValue(value) {
  let v = String(value || "");
  let type = "input";
  const m = v.match(/\s*\[(input|output|temp)\]\s*$/i);
  if (m) { type = m[1].toLowerCase(); v = v.slice(0, m.index); }
  v = v.replace(/\\/g, "/").trim();
  const i = v.lastIndexOf("/");
  return {
    filename: i >= 0 ? v.slice(i + 1) : v,
    subfolder: i >= 0 ? v.slice(0, i) : "",
    type,
  };
}

// Load Image Reaper resizes in PYTHON, at execute time, so the resized pixels
// do not exist in the browser at all before a run - the editor can only open the
// file on disk. That is fine for a plain loader, but it is NOT harmless here:
// with an aspect-changing mode (crop / cover) the mask would be painted against
// geometry the run never sees, and the node reads as "it ignored my resize"
// (reported 2026-08-15).
//
// getUpstreamImageURL has a branch for core LoadImage and otherwise falls back
// to src.imgs, which for this node is the /view URL of the INPUT file - i.e.
// always the original. Rather than guess a resized preview we cannot produce,
// say plainly which picture is on screen.
function upstreamResizeNote(node) {
  const graph = node.graph;
  const input = (node.inputs || []).find((i) => i.name === "image");
  if (!input || input.link == null || !graph) return "";
  let link = graph.links?.[input.link];
  if (!link && typeof graph.links?.get === "function") link = graph.links.get(input.link);
  const src = link && graph.getNodeById(link.origin_id);
  if (!src || src.comfyClass !== "ReaperLoadImage") return "";
  let st = null;
  try {
    const raw = src.properties?.loadImagePixState;
    st = typeof raw === "string" ? JSON.parse(raw || "{}") : raw;
  } catch (e) {
    return "";                       // unreadable state is not worth a warning
  }
  const mode = st && typeof st.mode === "string" ? st.mode : "";
  if (!mode || mode === "off") return "";
  return ` — this is the ORIGINAL. The Load Image above resizes it (${mode}), `
    + "and the resized picture only exists after a run.";
}

function getUpstreamImageURL(node) {
  // Prefer the LIVE wired source so a just-changed Load Image (or any live
  // preview) is what the editor opens. The cached executed-source URL below is
  // only a fallback for generative upstreams whose pixels exist solely as the
  // temp PNG the Python node saved on the last run. (Without this order,
  // swapping the Load Image file showed the PREVIOUS run's image until re-run.)
  const input = (node.inputs || []).find((i) => i.name === "image");
  const graph = node.graph;
  if (input && input.link != null && graph) {
    let link = graph.links?.[input.link];
    if (!link && typeof graph.links?.get === "function") link = graph.links.get(input.link);
    const src = link && graph.getNodeById(link.origin_id);
    if (src) {
      if (src.comfyClass === "LoadImage" || src.type === "LoadImage") {
        const w = (src.widgets || []).find((x) => x.name === "image");
        if (w && w.value) return buildSourceURL(parseAnnotatedImageValue(w.value), true);
      }
      if (src.imgs && src.imgs.length > 0) {
        const img = src.imgs[link.origin_slot] || src.imgs[0];
        if (typeof img === "string") return img;
        if (img && img.src) return img.src;
      }
    }
  }
  // fallback: source PNG from the last Python execute (generative upstreams, or
  // before a live preview exists), and the paste / drag-drop / restored case.
  if (node._redInpaintSourceURL) return node._redInpaintSourceURL;
  return null;
}

// ── clipboard paste → selected Inpaint Crop node ──
let _pasteInstalled = false;
function installPasteHandler() {
  if (_pasteInstalled) return;
  _pasteInstalled = true;
  window.addEventListener("paste", async (e) => {
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    const node = findActiveNode();
    if (!node) return;
    // editor open -> let the editor's own paste handler load it into the canvas
    if (node._redInpaintEditor?.el?.overlay?.isConnected) return;
    const items = e.clipboardData?.items || [];
    const it = Array.from(items).find((x) => x.type?.startsWith("image/"));
    if (!it) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const idx = (node.inputs || []).findIndex((i) => i.name === "image");
    if (idx >= 0 && node.inputs[idx].link != null) { try { node.disconnectInput(idx); } catch {} }
    const idsBefore = new Set((app.graph?._nodes || []).map((n) => n.id));
    const blob = it.getAsFile();
    if (!blob) return;
    const reader = new FileReader();
    reader.onload = (ev) => node._redInpaintPaste(ev.target.result);
    reader.readAsDataURL(blob);
    setTimeout(() => {
      for (const n of app.graph?._nodes || []) {
        if (idsBefore.has(n.id)) continue;
        if (n.comfyClass !== "LoadImage" && n.type !== "LoadImage") continue;
        const w = (n.widgets || []).find((x) => x.name === "image");
        if (typeof w?.value === "string" && w.value.startsWith("pasted/")) { try { app.graph.remove(n); } catch {} }
      }
    }, 50);
  }, true);
}

function findActiveNode() {
  const c = app.canvas;
  if (!c) return null;
  const ok = (n) => n && n.comfyClass === "ReaperInpaintCrop" && typeof n._redInpaintPaste === "function";
  const sel = c.selected_nodes;
  if (sel) {
    let iter = Array.isArray(sel) ? sel : (typeof sel.values === "function" ? Array.from(sel.values()) : Object.values(sel));
    const hit = iter?.find(ok);
    if (hit) return hit;
  }
  if (ok(c.current_node)) return c.current_node;
  if (ok(c.node_over)) return c.node_over;
  for (const n of app.graph?._nodes || []) if (ok(n) && (n.is_selected || n.flags?.is_selected)) return n;
  return null;
}

app.registerExtension({
  name: "Reaper.InpaintCrop",

  // No Settings-panel row: the mask preview color lives on the node itself (the
  // gear in the selection toolbar / the right-click entry). The setting id is
  // unchanged and merely unregistered, so an existing choice carries over; the
  // read site supplies the default for the unset case.

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "ReaperInpaintCrop") return;
    const origExec = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      origExec?.apply(this, arguments);
      this.imgs = null;
    };
    const origCfg = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (data) {
      const ret = origCfg?.apply(this, arguments);
      this.imgs = null;
      if (!this._redInpaintSourceURL && this.properties?.redInpaintSource) {
        this._redInpaintSourceURL = buildSourceURL(this.properties.redInpaintSource, true);
      }
      if (this._redInpaintRefresh) {
        queueMicrotask(() => this._redInpaintRefresh());
        setTimeout(() => this._redInpaintRefresh?.(), 250);
      }
      // After the node settles, give a DUPLICATE its own project_id (see
      // dedupeInpaintProjectId). Deferred a microtask so a clipboard paste has
      // added the node to its graph (so this.graph + the sibling are both live).
      queueMicrotask(() => { if (!isGraphLoading()) dedupeInpaintProjectId(this); });
      return ret;
    };
  },

  async nodeCreated(node) {
    if (node.comfyClass !== "ReaperInpaintCrop") return;
    node.imgs = null;
    // Fresh-drop default size only; never on the load path (configure restores
    // the saved size, so writing it during load would dirty the workflow). Mutate
    // the array elements (convention #9), don't replace the array.
    if (!isGraphLoading() && node.size) { node.size[0] = 330; node.size[1] = 500; }

    if (!(node.inputs || []).some((i) => i.name === "image")) node.addInput("image", "IMAGE");
    if (!(node.inputs || []).some((i) => i.name === "mask")) node.addInput("mask", "MASK");

    const parts = createNodePreview(
      "Inpaint Crop", "Reaper",
      "Wire an IMAGE and Run,\nor click 'Open mask editor' to load + paint",
    );
    // let dedupe (module scope) blank this node's thumbnail after a duplicate
    node._redInpaintClearPreview = () => clearNodePreview(parts, node);

    let stateJson = "{}";
    let widget;

    const refreshSourcePreview = () => {
      const url = getUpstreamImageURL(node);
      if (url) showNodePreview(parts, url, null, node);
    };

    // ── Open mask editor button ──
    node.addWidget("button", "Open mask editor", null, () => {
      if (node._redInpaintEditor?.el?.overlay?.isConnected) return;
      refreshSourcePreview();   // sync the node thumbnail to the current upstream image
      const editor = new InpaintCropEditor();
      node._redInpaintEditor = editor;
      // brush size / opacity persist across opens on this node
      const captureBrush = () => {
        node._redInpaintBrush = { brushSize: editor.brushSize, maskOpacity: editor.maskOpacity };
      };

      // preview tint (display only) - seed from the setting, persist on change
      const colName = app.ui.settings?.getSettingValue?.("Reaper.Inpaint.PreviewColor") || "Red";
      const colHex = INPAINT_PREVIEW_COLORS[colName] || INPAINT_PREVIEW_COLORS.Red;
      editor.previewColor = colHex;
      editor._cropBoxColor = (colHex === INPAINT_PREVIEW_COLORS.Orange) ? "#ffffff" : null;
      editor.onPreviewColor = (name) => {
        try { app.ui.settings?.setSettingValueAsync?.("Reaper.Inpaint.PreviewColor", name); } catch {}
      };

      editor.onSave = (jsonStr, extra, preview) => {
        stateJson = jsonStr;
        if (widget) widget.value = { state_json: jsonStr };
        writeBackWidgets(node, extra);
        if (preview) showNodePreview(parts, preview, null, node);
        if (app.graph) { app.graph.setDirtyCanvas(true, true); app.graph.change?.(); }
        captureBrush();
      };
      editor.onSaveToDisk = (d) => downloadDataURL(d, "reaper_inpaint_crop");
      editor.onLoadImage = () => {
        const idx = (node.inputs || []).findIndex((i) => i.name === "image");
        if (idx >= 0 && node.inputs[idx].link != null) { try { node.disconnectInput(idx); } catch {} }
      };
      editor.onClose = () => { captureBrush(); node._redInpaintEditor = null; node.setDirtyCanvas(true, true); };

      // Read BEFORE open: the loader's onload appends it to the "Loaded: W×H"
      // status, so it has to be on the editor by the time the image lands.
      editor._redResizeNote = upstreamResizeNote(node);
      editor.open(stateJson, getUpstreamImageURL(node),
        readParams(node), node._redInpaintBrush);
    });

    // ── mini-preview DOM widget (also carries the hidden state) ──
    installCanvasZoomPassthrough(parts.container);
    widget = node.addDOMWidget("InpaintCropWidget", "custom", parts.container, {
      getValue: () => ({ state_json: stateJson }),
      setValue: (v) => {
        if (!v || typeof v !== "object") return;
        stateJson = v.state_json || "{}";
        const imgInput = (node.inputs || []).find((i) => i.name === "image");
        if (imgInput && imgInput.link != null) queueMicrotask(refreshSourcePreview);
        else restoreNodePreview(parts, stateJson, node);   // rebuild from src_path when present
      },
      getMinHeight: () => 200,
      margin: 5,
    });
    applyAdaptiveCanvasOnly(widget);
    activateNodePreview(parts, node);

    // ── paste / drag-drop a source directly onto the node ──
    installPasteHandler();
    node._redInpaintPaste = async (dataURL) => {
      try {
        const r = await api.fetchApi(redApiUrl("/reaper/api/inpaint/upload_src"), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project_id: "inpaint_paste_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9), image: dataURL }),
        });
        const d = await r.json();
        const srcPath = d.path || "";
        let meta = {};
        try { meta = JSON.parse(stateJson) || {}; } catch {}
        meta.src_path = srcPath;
        meta.mask_path = "";  // a new source clears the old painted mask
        stateJson = JSON.stringify(meta);
        if (widget) widget.value = { state_json: stateJson };
        if (srcPath) {
          const part = { filename: srcPath.split(/[\\/]/).pop(), subfolder: "reaper", type: "input" };
          node._redInpaintSourceURL = buildSourceURL(part, true);
          if (!node.properties) node.properties = {};
          node.properties.redInpaintSource = part;
        }
        showNodePreview(parts, dataURL, null, node);
        if (app.graph) app.graph.setDirtyCanvas(true, true);
      } catch (err) { console.warn("[InpaintCrop] paste failed:", err); }
    };
    const dropTarget = parts?.container;
    if (dropTarget) {
      dropTarget.addEventListener("dragover", (e) => { if (e.dataTransfer?.types?.includes("Files")) { e.preventDefault(); e.stopPropagation(); } });
      dropTarget.addEventListener("drop", (e) => {
        e.preventDefault(); e.stopPropagation();
        const file = e.dataTransfer?.files?.[0];
        if (!file || !file.type?.startsWith("image/")) return;
        const idx = (node.inputs || []).findIndex((i) => i.name === "image");
        if (idx >= 0 && node.inputs[idx].link != null) { try { node.disconnectInput(idx); } catch {} }
        const reader = new FileReader();
        reader.onload = (ev) => node._redInpaintPaste(ev.target.result);
        reader.readAsDataURL(file);
      });
    }

    // ── source URL caching from Python execute + refresh hooks ──
    node._redInpaintRefresh = () => {
      if (getUpstreamImageURL(node)) refreshSourcePreview();
      // pass the real state (not "{}") so restoreNodePreview can rebuild from src_path
      // - e.g. a source loaded via the editor's Load Image, where the wire is gone.
      else restoreNodePreview(parts, stateJson, node);
    };
    const onExec = (event) => {
      const detail = event?.detail;
      if (!detail?.output) return;
      const matched = app.graph.getNodeById(detail.node) || app.graph.getNodeById(parseInt(detail.node, 10));
      if (matched !== node) return;
      const frames = detail.output.reaper_inpaint_source;
      if (!frames?.length) return;
      const f = frames[0];
      const part = { filename: f.filename, subfolder: f.subfolder || "", type: f.type || "temp" };
      node._redInpaintSourceURL = buildSourceURL(part, true);
      if (!node.properties) node.properties = {};
      node.properties.redInpaintSource = part;
      refreshSourcePreview();
    };
    api.addEventListener("executed", onExec);

    // wrap (don't clobber) any existing handler from the prototype / another ext;
    // forward all args, then run our image-input source-preview logic.
    const origConnChange = node.onConnectionsChange;
    node.onConnectionsChange = function (type, slotIndex, connected) {
      const r = origConnChange?.apply(this, arguments);
      if (type === LiteGraph.INPUT && node.inputs?.[slotIndex]?.name === "image" && !isGraphLoading()) {
        node._redInpaintSourceURL = null;
        if (node.properties) delete node.properties.redInpaintSource;
        if (connected) refreshSourcePreview();
        else restoreNodePreview(parts, "{}", node);
      }
      return r;
    };

    const origRemoved = node.onRemoved;
    node.onRemoved = () => {
      try { if (node._redInpaintEditor?.el?.overlay?.isConnected) node._redInpaintEditor._close(); } catch (e) {}
      try { parts?.resizeObserver?.disconnect(); } catch (e) {}
      origRemoved?.call(node);
      try { api.removeEventListener("executed", onExec); } catch {}
    };
  },
});

// No color block: this node's face is ComfyUI's own grey button plus a preview,
// so there is no Reaper orange on it to change. The panel hosts the mask
// preview color, which used to sit in the global Settings panel.
registerNodeAccent("ReaperInpaintCrop", {
  title: "Inpaint Crop",
  accent: false,
  rows: [
    { kind: "combo", setting: "Reaper.Inpaint.PreviewColor",
      options: ["Red", "Green", "Blue", "Yellow", "Orange"], defaultValue: "Red",
      label: "Mask preview color",
      hint: "The tint over the mask and seam in the editor. Display only." },
  ],
});
