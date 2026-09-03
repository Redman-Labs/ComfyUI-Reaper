// Load Image (Reaper) - the floating gear panel (Outpaint / Sizes / Save
// Image pattern: a themed panel beside the node, dragged by its header, closed
// on an outside click or Esc). It hosts Load Image's OWN resize UI - the mode
// chips (minus Pad), the per-mode controls, and the snap / resample / upscaling
// row - imported verbatim so the two loaders can never drift. Plus a per-node
// accent-color picker. The node face stays minimal; everything lives here.

import { app } from "/scripts/app.js";
import { isVueNodes } from "../shared/nodes2.mjs";
import { openReaperColorPickerPopup, BUTTON_PALETTE } from "../shared/color_picker.mjs";
import { injectCSS as injectLiCSS, renderGlobalControls } from "./ui.mjs";
import { buildModePanel } from "./resize_modes.mjs";
import { applyInlineLabel, applyWHLayout, applyCoverControls } from "./panel_polish.mjs";
import { GLOBAL_ACCENT_SETTING, repaintAllAccents } from "../shared/node_settings.mjs";
import {
  ACCENT_SETTING, BRAND, STATE_PROP, accentOf, readState, writeState,
} from "./core.mjs";

// Mode chips, in Load Image's order but WITHOUT Pad (Outpaint owns padding now).
const MODE_CHIPS = [
  { id: "off",          label: "Off",          title: "No resize. (Snap still applies if set.)" },
  { id: "max_mp",       label: "Max MP",       title: "Scale so the total pixel count stays under a megapixel cap. Keeps aspect ratio." },
  { id: "longest_side", label: "Longest side", title: "Scale so the longest side equals this many pixels. Keeps aspect ratio." },
  { id: "scale_factor", label: "Scale by ×",   title: "Multiply both dimensions by a factor. Keeps aspect ratio." },
  { id: "fit_inside",   label: "Fit inside",   title: "Scale to fit entirely within W×H without cropping. Keeps aspect ratio." },
  { id: "cover",        label: "Crop to fill", title: "Resize to exactly W×H, scaling then cropping the overflow. The anchor picks which part is kept." },
  { id: "match_ratio",  label: "Match ratio",  title: "Crop the image to a target aspect ratio (no scaling)." },
];

let _panel = null;
let _panelNode = null;
let _onChange = null;
let _cpHandle = null;

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function injectCSS() {
  if (document.getElementById("reaper-liset-css")) return;
  const s = document.createElement("style");
  s.id = "reaper-liset-css";
  // No backtick / CSS unicode escape inside this literal.
  s.textContent = `
    .rl-lmset { position:fixed; z-index:10010; width:320px; max-width:94vw; background:#1a1a1a;
      border:1px solid #4a4a4a; border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,0.6);
      color:#d8d8d8; font:12px 'Segoe UI',-apple-system,sans-serif; overflow:hidden; }
    .rl-lmset-t { display:flex; align-items:center; gap:8px; padding:10px 12px; background:#232323;
      border-bottom:1px solid #333; cursor:grab; user-select:none; color:#fff; }
    .rl-lmset-t .x { margin-left:auto; color:#8a8a8a; cursor:pointer; padding:0 4px; }
    .rl-lmset-t .x:hover { color:#fff; }
    .rl-lmset-b { padding:12px; display:flex; flex-direction:column; gap:12px; max-height:66vh; overflow-y:auto; }
    .rl-lmset-lab { font-size:12px; color:#9a9a9a; }
    /* Host the reused Load Image body on a .rl-li-root so its Image-Resize
       design-language overrides apply exactly as they do on the real node. */
    .rl-lmset-resize.rl-li-root { background:transparent; padding:0; display:flex;
      flex-direction:column; gap:9px; }
    /* 7 mode chips: flex-wrap so they fill each row (4 + 3) with no trailing
       gap, rather than a fixed 4-col grid that leaves an empty cell. */
    .rl-lmset-chips { display:flex; flex-wrap:wrap; gap:5px; }
    .rl-lmset-chips > .rl-li-chip { flex:1 1 64px; min-width:64px; box-sizing:border-box; }
    .rl-lmset-acc { display:flex; align-items:center; gap:10px; }
    .rl-lmset-sw { width:30px; height:22px; border-radius:5px; border:1px solid #555; cursor:pointer; flex:none; }
    .rl-lmset-sw:hover { border-color:#fff; }
    .rl-lmset-f { display:flex; gap:8px; align-items:center; padding:10px 12px; border-top:1px solid #333; background:#1f1f1f; }
    .rl-lmset-btn { border:1px solid #444; background:rgba(255,255,255,0.04); color:#d8d8d8; border-radius:5px;
      padding:6px 12px; font:12px 'Segoe UI',sans-serif; cursor:pointer; }
    .rl-lmset-btn:hover { border-color:var(--acc,${BRAND}); color:#fff; }
    .rl-lmset-push { margin-left:auto; }
  `;
  document.head.appendChild(s);
}

function getNodeScreenRect(node) {
  if (isVueNodes() && node && node.id != null) {
    const e = document.querySelector(`[data-node-id="${node.id}"]`);
    if (e) return e.getBoundingClientRect();
  }
  const c = app.canvas;
  const ds = c && c.ds;
  const cv = c && c.canvas;
  if (!ds || !cv || !node?.pos || !node?.size) return null;
  const cr = cv.getBoundingClientRect();
  const titleH = window.LiteGraph?.NODE_TITLE_HEIGHT || 30;
  const sc = ds.scale || 1;
  const off = ds.offset || [0, 0];
  const left = cr.left + (node.pos[0] + off[0]) * sc;
  const top = cr.top + (node.pos[1] - titleH + off[1]) * sc;
  return { left, top, right: left + node.size[0] * sc, bottom: top + (node.size[1] + titleH) * sc };
}

function placeBeside(panel, rect) {
  const vw = window.innerWidth, vh = window.innerHeight;
  const mw = panel.offsetWidth, mh = panel.offsetHeight;
  const gap = 12, pad = 8;
  if (!rect) {
    panel.style.left = Math.max(pad, (vw - mw) / 2) + "px";
    panel.style.top = Math.max(pad, (vh - mh) / 2) + "px";
    return;
  }
  let left = rect.right + gap;
  if (left + mw > vw - pad) left = rect.left - gap - mw;
  if (left < pad) left = Math.max(pad, vw - mw - pad);
  let top = rect.top;
  if (top + mh > vh - pad) top = vh - mh - pad;
  if (top < pad) top = pad;
  panel.style.left = left + "px";
  panel.style.top = top + "px";
}

function makeDraggable(panel, handle) {
  handle.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".x")) return;
    e.preventDefault();
    const r = panel.getBoundingClientRect();
    const ox = e.clientX - r.left, oy = e.clientY - r.top;
    const move = (ev) => {
      if (!panel.isConnected) return up();
      panel.style.left = Math.max(0, Math.min(window.innerWidth - panel.offsetWidth, ev.clientX - ox)) + "px";
      panel.style.top = Math.max(0, Math.min(window.innerHeight - panel.offsetHeight, ev.clientY - oy)) + "px";
    };
    const up = () => {
      window.removeEventListener("pointermove", move, true);
      window.removeEventListener("pointerup", up, true);
    };
    window.addEventListener("pointermove", move, true);
    window.addEventListener("pointerup", up, true);
  });
}

function outsideClose(e) {
  if (!_panel) return;
  if (_panel.contains(e.target)) return;
  // The reused resize UI opens its own popups (resample, ratio color, etc.) and
  // the accent picker - clicks inside those must not close the panel.
  if (e.target.closest?.(".rl-cp-popup, .rl-cp-modal-backdrop, .rl-li-rs-popup, .rl-li-popup")) return;
  closeMiniSettings();
}
function escClose(e) {
  if (e.key === "Escape" && _panel) {
    if (document.querySelector(".rl-cp-popup, .rl-cp-modal-backdrop, .rl-li-rs-popup, .rl-li-popup")) return;
    e.stopPropagation();
    closeMiniSettings();
  }
}

export function closeMiniSettings() {
  try { _cpHandle?.close(); } catch (_e) { /* already gone */ }
  _cpHandle = null;
  if (_panel) { try { _panel.remove(); } catch (_e) { /* already gone */ } }
  _panel = null;
  _panelNode = null;
  _onChange = null;
  document.removeEventListener("pointerdown", outsideClose, true);
  document.removeEventListener("keydown", escClose, true);
}

export function closeMiniSettingsFor(node) {
  if (_panelNode === node) closeMiniSettings();
}

// ctx = { onChange() } - onChange refreshes the node face (cards + accent).
export function openMiniSettings(node, ctx) {
  closeMiniSettings(); // single-open guard
  injectLiCSS();        // the shared .rl-li-* control styles
  injectCSS();
  _onChange = ctx?.onChange || null;
  _panelNode = node;

  const fire = () => { _onChange?.(); };

  const panel = el("div", "rl-lmset");
  // The floating panel uses --acc for its own chrome, while the reused Load
  // Image controls use --red-acc. Keep both tied to this node's accent so the
  // entire settings panel follows the color picker.
  panel.style.setProperty("--acc", accentOf(node));
  panel.style.setProperty("--red-acc", accentOf(node));

  const title = el("div", "rl-lmset-t");
  title.append(el("span", null, "⚙"), el("span", null, "Load Image settings"));
  const x = el("span", "x", "✕");
  x.addEventListener("click", closeMiniSettings);
  title.appendChild(x);

  const body = el("div", "rl-lmset-b");
  const foot = el("div", "rl-lmset-f");

  // The accent swatch is built ONCE (outside renderBody) so an open picker never
  // loses its anchor across a body rebuild.
  const sw = el("div", "rl-lmset-sw");
  sw.title = "Pick the accent color";
  sw.style.background = accentOf(node);
  sw.addEventListener("click", () => {
    try { _cpHandle?.close(); } catch (_e) { /* already gone */ }
    _cpHandle = openReaperColorPickerPopup(sw, {
      initialColor: accentOf(node),
      swatches: BUTTON_PALETTE,
      wide: true,
      resetColor: BRAND,
      onPick: (c) => {
        writeState(node, { ...readState(node), accent: c || BRAND });
        const a = accentOf(node);
        panel.style.setProperty("--acc", a);
        panel.style.setProperty("--red-acc", a);
        sw.style.background = a;
        fire();
      },
    });
  });

  function renderBody() {
    body.innerHTML = "";
    const state = readState(node);

    // Host the reused Load Image body pieces under a .rl-li-root so the
    // Image-Resize design-language overrides apply.
    const resize = el("div", "rl-lmset-resize rl-li-root");

    // ── mode chips (no Pad) ──
    const chips = el("div", "rl-lmset-chips");
    for (const c of MODE_CHIPS) {
      const chip = el("div", "rl-li-chip" + (state.mode === c.id ? " active" : ""), c.label);
      chip.title = c.title;
      chip.addEventListener("click", () => {
        if (readState(node).mode === c.id) return;
        writeState(node, { ...readState(node), mode: c.id });
        renderBody();   // structural change - rebuild the mode panel
        fire();
      });
      chips.appendChild(chip);
    }
    resize.appendChild(chips);

    // ── per-mode panel (imported from Load Image) ──
    // Input dims for the cover/fit preview - from node.imgs OR the fetched
    // preview image (restored-workflow case), matching the node face's
    // currentImage() so the preview isn't blank on a restored node.
    const srcImg = node.imgs?.[0]?.naturalWidth ? node.imgs[0]
      : (node._redLmPreviewImgEl?.naturalWidth ? node._redLmPreviewImgEl : null);
    const live = srcImg ? { w: srcImg.naturalWidth, h: srcImg.naturalHeight } : null;
    // onChange is NON-destructive: refresh the face only, never rebuild the
    // panel (or a focused numeric input would be destroyed mid-edit - Load
    // Image Pattern #5).
    const panelEl = buildModePanel(state.mode, node, state, writeState, () => fire(),
      STATE_PROP, { previewMaxW: 148, previewMaxH: 100, cropOnly: true, inputDims: live, oneLine: true });
    if (panelEl) {
      applyInlineLabel(panelEl, state.mode);
      if (state.mode === "fit_inside" || state.mode === "cover") applyWHLayout(panelEl);
      if (state.mode === "cover") applyCoverControls(node, panelEl, readState, writeState, () => fire());
      panelEl.querySelector(".rl-li-panel-label")?.remove();
      resize.appendChild(panelEl);
    }

    // ── snap / resample / upscaling (imported from Load Image) ──
    resize.appendChild(renderGlobalControls(node, state, writeState, () => fire()));

    body.appendChild(resize);

    // ── accent ──
    const acc = el("div", "rl-lmset-acc");
    sw.style.background = accentOf(node);
    acc.append(sw, el("span", "rl-lmset-lab", "The accent for this node"));
    body.appendChild(acc);
  }

  renderBody();

  // ── footer ──
  const mkDefault = el("button", "rl-lmset-btn", "Color as default");
  mkDefault.title = "Use this color for every new Load Image (Reaper) node";
  mkDefault.addEventListener("click", async () => {
    try {
      await app.ui.settings.setSettingValueAsync(ACCENT_SETTING, accentOf(node));
      mkDefault.textContent = "Saved as default";
      setTimeout(() => { mkDefault.textContent = "Color as default"; }, 1200);
    } catch (_e) { /* settings not ready */ }
  });
  const done = el("button", "rl-lmset-btn rl-lmset-push", "Done");
  done.addEventListener("click", closeMiniSettings);

  // The SECOND default: one master color every Reaper node follows unless it
  // (or its node type) has been given one of its own. Written through the shared
  // helper so all the panels agree on the key.
  const mkAll = el("button", "rl-lmset-btn", "Every Reaper node");
  mkAll.title = "Every Reaper node follows this color, unless it has been given one of its own";
  mkAll.addEventListener("click", async () => {
    try {
      await app.ui.settings.setSettingValueAsync(GLOBAL_ACCENT_SETTING, accentOf(node));
      mkAll.textContent = "Saved";
      setTimeout(() => { mkAll.textContent = "Every Reaper node"; }, 1200);
      repaintAllAccents();
    } catch { /* settings not ready */ }
  });
  foot.append(mkDefault, mkAll, done);

  panel.append(title, body, foot);
  document.body.appendChild(panel);

  placeBeside(panel, getNodeScreenRect(node));
  makeDraggable(panel, title);

  setTimeout(() => {
    if (!_panel) return;
    document.addEventListener("pointerdown", outsideClose, true);
    document.addEventListener("keydown", escClose, true);
  }, 0);
  _panel = panel;
}
