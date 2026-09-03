// ╔═══════════════════════════════════════════════════════════════╗
// ║  Reaper Editor Framework — Theme & CSS Injection           ║
// ║  Brand colors, CSS custom properties, and shared stylesheet  ║
// ╚═══════════════════════════════════════════════════════════════╝

import { redAsset } from "../shared/api_url.mjs";
import { BRAND } from "../shared/utils.mjs";

/** Brand accent color hex — re-exported for editor-specific use. */
export { BRAND };

/**
 * Asset TAIL for UI icon SVGs - NOT a usable url on its own.
 *
 * It is deliberately a bare tail so callers build the url as
 * `redAsset(UI_ICON + "save.svg")`. Do NOT turn this into a pre-built base
 * (`redAsset("icons/ui/")`): a hosted ComfyUI appends its auth token as a
 * query string, so a wrapped base that is then concatenated puts the token in
 * the MIDDLE of the url and the request dies. See js/shared/api_url.mjs.
 */
export const UI_ICON = "icons/ui/";

/**
 * Creates an <img> element pointing to a UI icon SVG.
 * @param {string} name - Filename inside the UI icons folder (e.g. "save.svg")
 * @param {number} [size=14] - Width and height in px
 * @returns {HTMLImageElement}
 */
export function _uiIcon(name, size = 14) {
  const img = document.createElement("img");
  img.src = redAsset("icons/ui/" + name);
  img.style.cssText = `width:${size}px;height:${size}px;pointer-events:none;`;
  img.draggable = false;
  return img;
}

/** ID used for the injected <style> element — prevents duplicate injection. */
const STYLE_ID = "reaper-framework-v1";

// ═════════════════════════════════════════════════════════════════
//  CSS Injection
// ═════════════════════════════════════════════════════════════════

export function injectFrameworkStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
/* ═══════════════════════════════════════════════════════
   Reaper Editor Framework — Shared Stylesheet
   ═══════════════════════════════════════════════════════ */

/* ── CSS Custom Properties ──────────────────────────── */
.rdx-overlay {
  --rdx-accent: ${BRAND};
  --rdx-accent-hover: ${BRAND};
  --rdx-bg-darkest: #131415;
  --rdx-bg-dark: #171718;
  --rdx-bg-sidebar: #181a1b;
  --rdx-bg-panel: #242628;
  --rdx-bg-input: #111;
  --rdx-bg-btn: #353535;
  --rdx-border: #3a3d40;
  --rdx-border-subtle: #2a2c2e;
  --rdx-border-titlebar: #2e3033;
  --rdx-text: #e0e0e0;
  --rdx-text-dim: #888;
  --rdx-text-dimmer: #666;
  --rdx-text-label: #999;
  --rdx-select-bg: #2a1800;
  --rdx-select-border: ${BRAND};
  --rdx-multi-bg: #0a1a2a;
  --rdx-multi-border: #0ea5e9;
  --rdx-danger: #d46060;
  --rdx-danger-bg: #2a1a1a;
  --rdx-font: 'Segoe UI', system-ui, sans-serif;
  --rdx-font-mono: monospace;
}

/* ── Overlay (fullscreen editor) ────────────────────── */
.rdx-overlay {
  position: fixed; inset: 0; z-index: 11000;
  display: flex; flex-direction: column;
  background: var(--rdx-bg-dark);
  font-family: var(--rdx-font);
  color: var(--rdx-text);
  overflow: hidden; user-select: none;
}

/* ── Titlebar ───────────────────────────────────────── */
.rdx-titlebar {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; background: var(--rdx-bg-darkest);
  border-bottom: 1px solid var(--rdx-border-titlebar);
  flex-shrink: 0; height: 38px;
}
.rdx-title {
  color: #fff; font-size: 13px; font-weight: bold;
  display: flex; align-items: center; gap: 6px;
  flex-shrink: 0;
}
.rdx-title-brand { color: var(--rdx-accent); }
.rdx-title-logo { width: 20px; height: 20px; }
.rdx-titlebar-center {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  min-width: 0;
}
.rdx-titlebar-actions {
  display: flex; align-items: center; gap: 6px;
  flex-shrink: 0;
}
.rdx-titlebar-zoom {
  display: flex; align-items: center; gap: 3px;
  background: rgba(255,255,255,0.05); border: 1px solid var(--rdx-border);
  border-radius: 5px; padding: 2px 4px;
}
.rdx-titlebar-zoom .rdx-zoom-label {
  font-size: 10px; color: var(--rdx-text-dim);
  min-width: 36px; text-align: center;
}
.rdx-titlebar-sep {
  width: 1px; height: 18px; background: var(--rdx-border); flex-shrink: 0;
  margin: 0 4px;
}

/* ── Top options bar (below titlebar, e.g. Paint brush opts) ── */
.rdx-top-options {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 4px 10px; background: var(--rdx-bg-darkest);
  border-bottom: 1px solid var(--rdx-border-subtle);
  flex-shrink: 0; min-height: 34px;
}

/* ── Body (sidebars + workspace) ────────────────────── */
.rdx-body {
  display: flex; flex: 1; overflow: hidden; min-height: 0;
}

/* ── Sidebars ───────────────────────────────────────── */
.rdx-sidebar {
  flex-shrink: 0; background: var(--rdx-bg-sidebar);
  display: flex; flex-direction: column;
  overflow-y: auto; overflow-x: hidden;
  scrollbar-gutter: stable;
  position: relative; z-index: 5;
}
.rdx-sidebar-left { border-right: 1px solid var(--rdx-border-subtle); }
.rdx-sidebar-right { border-left: 1px solid var(--rdx-border-subtle); overflow-y: hidden; }

/* Sidebar scrollbar */
.rdx-sidebar::-webkit-scrollbar { width: 5px; }
.rdx-sidebar::-webkit-scrollbar-track { background: var(--rdx-bg-input); }
.rdx-sidebar::-webkit-scrollbar-thumb { background: var(--rdx-border); border-radius: 3px; }
.rdx-sidebar::-webkit-scrollbar-thumb:hover { background: var(--rdx-accent); }

/* ── Workspace (center canvas area) ─────────────────── */
.rdx-workspace {
  flex: 1; position: relative; overflow: hidden;
  background: #111315;
  display: flex; align-items: center; justify-content: center;
}

/* Sidebar footer (save/close/help — always at bottom) */
.rdx-sidebar-footer {
  padding: 10px 12px; margin-top: auto;
  border-top: 1px solid var(--rdx-border-titlebar);
  display: flex; flex-direction: column; gap: 6px;
  flex-shrink: 0;
}

/* ── Tool info (floating tooltip in workspace, bottom-left) ── */
.rdx-tool-info {
  position: absolute; bottom: 10px; left: 10px;
  background: rgba(0,0,0,0.75); color: #ccc;
  padding: 5px 12px; border-radius: 5px;
  font-size: 10px; font-family: var(--rdx-font-mono);
  pointer-events: none; z-index: 5;
  max-width: 80%;
  transition: color 0.15s ease;
}
/* Editors that never write status text (AudioReact) leave this element
   empty — its padding + dark background still rendered a small box that
   overlapped AudioReact's bottom-left transport buttons. :empty hides it
   until an editor actually writes text via setStatusText(). */
.rdx-tool-info:empty { display: none; }
.rdx-tool-info.warn { color: ${BRAND}; }
.rdx-tool-info.error { color: #f08080; }

/* ── Panel / Section ────────────────────────────────── */
.rdx-panel {
  padding: 8px 10px;
  border-bottom: 1px solid var(--rdx-border-subtle);
}
.rdx-panel-title {
  font-size: 9px; color: var(--rdx-accent); font-weight: bold;
  text-transform: uppercase; letter-spacing: .06em;
  margin-bottom: 6px; cursor: default;
  display: flex; align-items: center; gap: 4px;
}
.rdx-panel-title-arrow {
  font-size: 8px; transition: transform .15s; display: inline-block;
}
.rdx-panel.collapsed .rdx-panel-title-arrow { transform: rotate(-90deg); }
.rdx-panel.collapsed .rdx-panel-content { display: none; }
.rdx-panel-title.clickable { cursor: pointer; }
.rdx-panel-title.clickable:hover { color: #fff; }

/* ── Buttons ────────────────────────────────────────── */
.rdx-btn, .rdx-btn-full, .rdx-btn-sm {
  font-family: inherit; cursor: pointer;
  border-radius: 5px; border: 1px solid var(--rdx-border);
  transition: all .15s ease; white-space: nowrap;
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
}
.rdx-btn:disabled, .rdx-btn-full:disabled, .rdx-btn-sm:disabled {
  opacity: 0.35; cursor: default; pointer-events: none;
}
.rdx-btn img, .rdx-btn-full img, .rdx-btn-sm img {
  width: 14px; height: 14px; filter: brightness(0) invert(0.7);
  pointer-events: none;
}
.rdx-btn:hover img, .rdx-btn-full:hover img, .rdx-btn-sm:hover img {
  filter: brightness(0) invert(1);
}

.rdx-btn {
  background: var(--rdx-bg-btn); color: #ccc;
  padding: 6px 14px; font-size: 12px;
}
.rdx-btn:hover { background: #2e3033; color: var(--rdx-accent); border-color: var(--rdx-accent); }

.rdx-btn.rdx-btn-accent, .rdx-btn-accent {
  background: var(--rdx-accent); border-color: var(--rdx-accent);
  color: #fff; font-weight: bold;
}
.rdx-btn.rdx-btn-accent:hover, .rdx-btn-accent:hover {
  background: var(--rdx-accent-hover); border-color: var(--rdx-accent-hover);
}
.rdx-btn-accent img { filter: brightness(0) invert(1); }

.rdx-btn.rdx-btn-danger, .rdx-btn-full.rdx-btn-danger, .rdx-btn-sm.rdx-btn-danger {
  background: #1e2022 !important; color: #ccc !important;
  border-color: ${BRAND} !important;
}
.rdx-btn.rdx-btn-danger:hover, .rdx-btn-full.rdx-btn-danger:hover, .rdx-btn-sm.rdx-btn-danger:hover {
  background: ${BRAND} !important; color: #fff !important;
  border-color: ${BRAND} !important;
}
.rdx-btn-danger img, .rdx-btn-danger svg {
  filter: none !important;
}
.rdx-btn-danger:hover img, .rdx-btn-danger:hover svg {
  filter: brightness(0) invert(1) !important;
}

.rdx-btn-full {
  width: 100%; padding: 7px 10px; font-size: 11px;
  background: #1e2022; color: #ccc;
}
.rdx-btn-full:hover { background: #2e3033; color: var(--rdx-accent); border-color: var(--rdx-accent); }

.rdx-btn-sm {
  min-width: 28px; height: 28px; padding: 0 4px; flex-shrink: 0;
  background: var(--rdx-bg-panel); color: #ccc; font-size: 13px;
}
.rdx-btn-sm:hover { background: #2e3033; color: var(--rdx-accent); border-color: var(--rdx-accent); }

.rdx-btn-icon {
  background: none; border: none; color: #ccc; padding: 4px;
  cursor: pointer; font-size: 16px; border-radius: 4px; transition: all .15s;
  display: inline-flex; align-items: center; justify-content: center;
}
.rdx-btn-icon:hover { color: var(--rdx-accent); background: rgba(255,255,255,0.05); }
.rdx-btn-icon:disabled { opacity: 0.3; cursor: default; pointer-events: none; }

.rdx-btn-row { display: flex; gap: 6px; }
.rdx-btn-row > .rdx-btn, .rdx-btn-row > .rdx-btn-full { flex: 1; }

.rdx-btn.active { background: var(--rdx-accent); border-color: var(--rdx-accent); color: #fff; }
.rdx-btn.active img { filter: brightness(0) invert(1); }

/* ── Pill grid ─────────────────────────────────────── */
.rdx-pill-grid { display: grid; gap: 4px; }
.rdx-pill {
  font-size: 10px; background: #1e2022; border: 1px solid var(--rdx-border);
  color: #aaa; border-radius: 3px; padding: 4px 0; cursor: pointer;
  transition: all .1s; text-align: center; font-family: inherit;
}
.rdx-pill:hover { background: #444; color: #fff; }
.rdx-pill.active { background: var(--rdx-accent); border-color: var(--rdx-accent); color: #fff; }

/* ── Slider row ─────────────────────────────────────── */
.rdx-slider-row {
  display: flex; align-items: center; gap: 5px; margin-bottom: 5px;
}
.rdx-slider-label {
  font-size: 10px; color: var(--rdx-text-dim); flex-shrink: 0;
}
.rdx-slider-row input[type=number] {
  width: 48px; background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-border); border-radius: 4px;
  padding: 3px 4px; font-size: 10px; font-family: var(--rdx-font-mono);
  flex-shrink: 0; text-align: center;
}
.rdx-slider-row input[type=number]:focus {
  border-color: var(--rdx-accent); outline: none;
}

/* ── Unified slider styling ──────────────────────────── */
.rdx-overlay input[type=range] {
  -webkit-appearance: none; appearance: none;
  flex: 1; min-width: 0; height: 6px; cursor: pointer;
  background: linear-gradient(to right,
    var(--rdx-accent) 0%, var(--rdx-accent) var(--rdx-fill, 50%),
    var(--rdx-border) var(--rdx-fill, 50%), var(--rdx-border) 100%);
  border-radius: 3px; border: none; outline: none;
}
.rdx-overlay input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 12px; height: 12px; border-radius: 50%;
  background: var(--rdx-accent); border: none;
  box-shadow: 0 0 3px rgba(0,0,0,0.5);
  cursor: pointer; margin-top: -3px;
}
.rdx-overlay input[type=range]::-moz-range-thumb {
  width: 12px; height: 12px; border-radius: 50%;
  background: var(--rdx-accent); border: none;
  box-shadow: 0 0 3px rgba(0,0,0,0.5);
  cursor: pointer;
}
.rdx-overlay input[type=range]::-webkit-slider-runnable-track {
  height: 6px; border-radius: 3px; background: transparent;
}
.rdx-overlay input[type=range]::-moz-range-track {
  height: 6px; border-radius: 3px; background: transparent;
}
.rdx-overlay input[type=range]::-moz-range-progress {
  height: 6px; border-radius: 3px; background: var(--rdx-accent);
}

/* ── Number input ───────────────────────────────────── */
.rdx-input-num {
  width: 55px; background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-border); border-radius: 3px;
  padding: 3px 4px; font-size: 10px; font-family: var(--rdx-font-mono);
  text-align: center;
}

/* ── Select dropdown ────────────────────────────────── */
.rdx-select {
  background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-border); border-radius: 4px;
  padding: 4px 6px; font-size: 11px; font-family: inherit;
  cursor: pointer; width: 100%;
}

/* ── Color input ────────────────────────────────────── */
.rdx-color-input {
  width: 50px; height: 22px; cursor: pointer;
  border: 1px solid var(--rdx-border); border-radius: 4px;
  background: var(--rdx-bg-input); padding: 0;
}

/* ── Row (label + content) ──────────────────────────── */
.rdx-row {
  display: flex; align-items: center; gap: 6px; margin-bottom: 5px;
}
.rdx-row-label {
  font-size: 10px; color: var(--rdx-text-dim); flex-shrink: 0;
}

/* ── Button row ─────────────────────────────────────── */
.rdx-btn-row { display: flex; gap: 6px; }

/* ── Tool button ────────────────────────────────────── */
.rdx-tool-btn {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 1px;
  height: 38px; background: #1c1e1f; border: 1px solid var(--rdx-border);
  color: #ccc; border-radius: 4px; cursor: pointer;
  font-family: inherit; font-size: 10px; transition: all .12s;
  padding: 2px;
}
.rdx-tool-btn:hover { background: #2e3033; color: #fff; border-color: #555; }
.rdx-tool-btn.active { background: var(--rdx-accent); border-color: var(--rdx-accent); color: #fff; }
.rdx-tool-btn-icon { font-size: 14px; line-height: 1; }
.rdx-tool-btn-label { font-size: 8px; line-height: 1; }

/* ── Tool grid ──────────────────────────────────────── */
.rdx-tool-grid { display: grid; gap: 4px; }

/* ── Layer Panel (unified Photoshop-style) ──────────── */
.rdx-layer-panel {
  display: flex; flex-direction: column; min-height: 0; flex: 1;
}
.rdx-layer-blend-row {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; border-bottom: 1px solid var(--rdx-border-subtle);
}
.rdx-layer-blend-select {
  flex: 1; background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-border); border-radius: 4px;
  padding: 4px 6px; font-size: 11px; font-family: inherit;
}
.rdx-layer-opacity-row {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 8px; border-bottom: 1px solid var(--rdx-border-subtle);
}
.rdx-layer-opacity-label {
  font-size: 9px; color: var(--rdx-text-dim); flex-shrink: 0;
}
.rdx-layer-opacity-row input[type=number] {
  width: 42px; background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-border); border-radius: 4px;
  padding: 3px 4px; font-size: 10px; font-family: var(--rdx-font-mono);
  text-align: center; flex-shrink: 0;
}
.rdx-layer-opacity-row input[type=number]:focus {
  border-color: var(--rdx-accent); outline: none;
}

/* Layer list */
.rdx-layers-list {
  overflow-y: auto; min-height: 40px; flex: 1;
  padding: 2px 0;
}
.rdx-layers-resize {
  height: 1px; background: var(--rdx-border-subtle); flex-shrink: 0;
}
.rdx-layers-list::-webkit-scrollbar { width: 4px; }
.rdx-layers-list::-webkit-scrollbar-track { background: transparent; }
.rdx-layers-list::-webkit-scrollbar-thumb { background: var(--rdx-border); border-radius: 2px; }

/* Layer item */
.rdx-layer-item {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 6px; border-radius: 4px;
  border: 1px solid transparent; cursor: pointer;
  font-size: 11px; transition: background .1s;
  min-height: 30px;
}
.rdx-layer-item:hover { background: rgba(255,255,255,0.04); }
.rdx-layer-item.active {
  background: var(--rdx-select-bg); border-color: var(--rdx-select-border);
}
.rdx-layer-item.multi-selected {
  background: var(--rdx-multi-bg); border-color: var(--rdx-multi-border);
}
.rdx-layer-item.drag-over-top { border-top: 2px solid var(--rdx-accent); }
.rdx-layer-item.drag-over-bottom { border-bottom: 2px solid var(--rdx-accent); }
.rdx-layer-item.dragging { opacity: 0.35; }

/* Layer icon buttons (eye, lock) */
.rdx-layer-icon {
  width: 16px; height: 16px; flex-shrink: 0; cursor: pointer;
  opacity: 0.5; transition: opacity .15s;
  display: flex; align-items: center; justify-content: center;
}
.rdx-layer-icon:hover { opacity: 1; }
.rdx-layer-icon img {
  width: 12px; height: 12px; display: block;
  filter: brightness(0) invert(0.7);
}
.rdx-layer-icon:hover img { filter: brightness(0) invert(1); }
.rdx-layer-item.active .rdx-layer-icon img { filter: brightness(0) invert(0.9); }

/* Layer thumbnail */
.rdx-layer-thumb {
  width: 28px; height: 28px; flex-shrink: 0; border-radius: 3px;
  background: repeating-conic-gradient(#333 0% 25%, #222 0% 50%) 50% / 8px 8px;
  overflow: hidden; border: 1px solid rgba(255,255,255,0.06);
}

/* Layer name */
.rdx-layer-name {
  flex: 1; font-size: 11px; color: #ccc;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  padding: 2px 4px; min-width: 0;
}
.rdx-layer-name-input {
  flex: 1; background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-accent); border-radius: 3px;
  font-size: 11px; padding: 2px 6px; outline: none;
  font-family: inherit; min-width: 0;
}

/* Action bar (add, dup, delete, up, down, merge) */
.rdx-layers-actions {
  display: flex; gap: 2px; padding: 5px 4px;
  border-top: 1px solid var(--rdx-border-subtle);
  justify-content: center;
}
.rdx-layer-action-btn {
  width: 28px; height: 28px; padding: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--rdx-bg-panel); border: 1px solid var(--rdx-border);
  border-radius: 4px; cursor: pointer; transition: all .12s;
}
.rdx-layer-action-btn:hover {
  background: #2e3033; border-color: var(--rdx-accent);
}
.rdx-layer-action-btn:disabled { opacity: 0.3; cursor: default; pointer-events: none; }
.rdx-layer-action-btn img {
  width: 14px; height: 14px; display: block;
  filter: brightness(0) invert(0.7);
}
.rdx-layer-action-btn:hover img { filter: brightness(0) invert(1); }
.rdx-layer-action-btn.danger { border-color: ${BRAND}; }
.rdx-layer-action-btn.danger:hover {
  background: ${BRAND}; border-color: ${BRAND};
}
.rdx-layer-action-btn.danger:hover img {
  filter: brightness(0) invert(1) !important;
}

/* ── Canvas Toolbar (Add Image, BG Color, Clear) ───── */
.rdx-canvas-toolbar {
  display: flex; flex-direction: column; gap: 5px;
  padding: 8px 10px; border-bottom: 1px solid var(--rdx-border-subtle);
}
.rdx-canvas-toolbar-row {
  display: flex; align-items: center; gap: 6px;
}
.rdx-canvas-toolbar .rdx-btn-full {
  font-size: 11px; padding: 6px 8px;
}
/* Drag & drop overlay on workspace */
.rdx-drop-overlay {
  display: none; position: absolute; inset: 0; z-index: 50;
  background: rgba(246, 103, 68, 0.08);
  border: 3px dashed var(--rdx-accent);
  border-radius: 8px;
  pointer-events: none;
  align-items: center; justify-content: center;
}
.rdx-drop-overlay.active { display: flex; }
.rdx-drop-label {
  background: rgba(0,0,0,0.7); color: var(--rdx-accent);
  padding: 12px 24px; border-radius: 8px;
  font-size: 14px; font-weight: bold;
}

/* ── Help overlay (unified modal, 2-column layout) ───── */
.rdx-help-overlay {
  display: none; position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  background: #171718; border: 1px solid var(--rdx-accent);
  border-radius: 10px; padding: 0;
  width: 960px; max-width: 95%; max-height: 86vh;
  z-index: 100; overflow: hidden;
  box-shadow: 0 12px 40px rgba(0,0,0,0.6);
  font-family: var(--rdx-font);
}
.rdx-help-header {
  display: flex; align-items: center; padding: 14px 20px;
  border-bottom: 1px solid #2a2a2a;
}
.rdx-help-header h3 { flex: 1; color: var(--rdx-accent); font-size: 14px; margin: 0; font-weight: 600; }
.rdx-help-content {
  padding: 18px 24px; overflow-y: auto;
  max-height: calc(86vh - 110px);
  font-size: 11px; line-height: 1.7; color: #ccc;
  column-count: 2; column-gap: 36px;
}
.rdx-help-section {
  break-inside: avoid; margin-bottom: 14px;
}
.rdx-help-section:last-child { margin-bottom: 0; }
.rdx-help-section h4 {
  color: var(--rdx-accent);
  margin: 0 0 6px 0; font-size: 11px; font-weight: 700;
  letter-spacing: 0.6px; text-transform: uppercase;
}
.rdx-help-grid {
  display: grid; grid-template-columns: max-content 1fr;
  gap: 3px 14px;
}
.rdx-help-grid b { color: #eee; white-space: nowrap; font-weight: 600; }
.rdx-help-grid span { color: #bbb; }
.rdx-help-content kbd {
  background: #2a2c2e; border: 1px solid #444; border-radius: 3px;
  padding: 1px 5px; font-size: 10px; color: var(--rdx-text);
  font-family: var(--rdx-font-mono, monospace);
}
.rdx-help-content b { color: #eee; }
.rdx-help-footer {
  padding: 10px 20px; border-top: 1px solid #2a2a2a;
  font-size: 10px; color: #666; text-align: center; line-height: 1.6;
  flex-shrink: 0;
}
.rdx-help-footer a { color: var(--rdx-accent); text-decoration: none; }
.rdx-help-footer a:hover { text-decoration: underline; }

/* ── Zoom controls ──────────────────────────────────── */
.rdx-zoom-bar {
  position: absolute; bottom: 8px; left: 50%;
  transform: translateX(-50%);
  display: flex; align-items: center; gap: 4px;
  background: rgba(20,20,22,0.85); border: 1px solid var(--rdx-border);
  border-radius: 6px; padding: 3px 6px;
}
.rdx-zoom-label {
  font-size: 10px; color: var(--rdx-text-dim);
  min-width: 36px; text-align: center;
}

/* ── Checkbox ───────────────────────────────────────── */
.rdx-check-row {
  display: flex; align-items: center; gap: 6px; cursor: pointer;
  font-size: 11px; color: #ccc;
}
.rdx-check-row input[type=checkbox] { accent-color: var(--rdx-accent); }

/* ── Divider ────────────────────────────────────────── */
.rdx-divider {
  height: 1px; background: var(--rdx-border-subtle);
  margin: 6px 0; flex-shrink: 0;
}

/* ── Info text ──────────────────────────────────────── */
.rdx-info { font-size: 10px; color: var(--rdx-text-dim); line-height: 1.6; }
.rdx-info b { color: #ccc; font-weight: 600; }

/* ── Canvas Frame (orange border + dimension label + gray masks) ── */
.rdx-canvas-frame {
  position: absolute; pointer-events: none; z-index: 2;
  box-sizing: border-box;
  border: 2px solid rgba(249, 115, 22, 0.45);
}
.rdx-canvas-frame-label {
  position: absolute; bottom: -18px; right: 0;
  font-size: 12px; color: rgba(249, 115, 22, 0.6);
  font-family: var(--rdx-font-mono); white-space: nowrap;
  transform-origin: bottom right;
}
.rdx-canvas-mask {
  position: absolute; pointer-events: none; z-index: 1;
  background: rgba(0, 0, 0, 0.4);
}

/* ── Canvas Settings component ──────────────────────── */
.rdx-canvas-settings { display: flex; flex-direction: column; gap: 6px; }
.rdx-ratio-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; }
.rdx-ratio-btn {
  font-size: 10px; background: #1e2022; border: 1px solid var(--rdx-border);
  color: #aaa; border-radius: 4px; padding: 5px 0; cursor: pointer;
  transition: all .12s; text-align: center; font-family: inherit;
  font-weight: 500;
}
.rdx-ratio-btn:hover { background: #444; color: #fff; border-color: #555; }
.rdx-ratio-btn.active {
  background: var(--rdx-accent); border-color: var(--rdx-accent); color: #fff;
}
.rdx-size-row {
  display: flex; align-items: center; gap: 4px;
}
.rdx-size-input {
  flex: 1; background: var(--rdx-bg-input); color: var(--rdx-text);
  border: 1px solid var(--rdx-border); border-radius: 4px;
  padding: 5px 6px; font-size: 11px; font-family: var(--rdx-font-mono);
  text-align: center; min-width: 0;
}
.rdx-size-label {
  font-size: 9px; color: var(--rdx-text-dim); width: 14px; flex-shrink: 0;
  text-align: center;
}
.rdx-size-x { font-size: 10px; color: var(--rdx-text-dimmer); flex-shrink: 0; }
.rdx-swap-btn {
  width: 100%; padding: 5px; font-size: 11px; text-align: center;
  background: #1e2022; border: 1px solid var(--rdx-border); color: #aaa;
  border-radius: 4px; cursor: pointer; transition: all .12s; font-family: inherit;
}
.rdx-swap-btn:hover { background: var(--rdx-accent); border-color: var(--rdx-accent); color: #fff; }
  `;
  document.head.appendChild(s);

  // ── Slider Fill System ──────────────────────────────────────
  if (!window._pxfSliderFillInit) {
    window._pxfSliderFillInit = true;
    window._pxfUpdateFill = function (input) {
      const mn = parseFloat(input.min) || 0,
        mx = parseFloat(input.max) || 100;
      const v = parseFloat(input.value) || 0;
      input.style.setProperty(
        "--rdx-fill",
        Math.max(0, Math.min(100, ((v - mn) / (mx - mn)) * 100)) + "%",
      );
    };
    document.addEventListener("input", (e) => {
      if (e.target.type === "range" && e.target.closest(".rdx-overlay"))
        window._pxfUpdateFill(e.target);
    });
    const desc = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    );
    const origSet = desc.set;
    desc.set = function (v) {
      origSet.call(this, v);
      if (this.type === "range" && this.closest(".rdx-overlay"))
        window._pxfUpdateFill(this);
    };
    Object.defineProperty(HTMLInputElement.prototype, "value", desc);
  }
}
