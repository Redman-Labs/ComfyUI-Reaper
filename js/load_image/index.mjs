// ╔═══════════════════════════════════════════════════════════════╗
// ║  Reaper Shared — Barrel Export                             ║
// ╚═══════════════════════════════════════════════════════════════╝

// ── Reaper JS bundle version ────────────────────────────────────────────
// MUST stay in lockstep with `version` in pyproject.toml — bump BOTH together
// on every release. The Version Check node compares this (the version baked
// into the JS the BROWSER actually loaded) against the Python files version;
// a mismatch means the browser is running STALE cached code and the user needs
// a hard refresh (Ctrl+Shift+R). It lives in this existing, widely-imported
// module on purpose: a brand-new file is never in anyone's cache, so it could
// never reveal a stale bundle.
export const REAPER_JS_VERSION = "1.4.81";

export {
  allow_debug,
  REAPER_LOGO,
  BRAND,
  createDummyWidget,
  installFocusTrap,
  hideJsonWidget,
  restorePreview,
  resizeNode,
  getLogo,
  createPlaceholder,
  downloadDataURL,
} from "./utils.mjs";

export {
  createNodePreview,
  showNodePreview,
  restoreNodePreview,
  clearNodePreview,
  activateNodePreview,
} from "./preview.mjs";

export { injectLabelCSS } from "../shared/label_css.mjs";

export { isVueNodes, applyAdaptiveCanvasOnly, canvasBackingScale, installZoomRepaint } from "../shared/nodes2.mjs";

export { installResizeFloor, measureRootContent } from "../shared/resize_floor.mjs";

export { installCanvasZoomPassthrough } from "../shared/canvas_zoom.mjs";

// Node UI convention #27 - a document.body popup must track the canvas zoom and
// grow to fit, or it reads tiny beside a zoomed-in node. Use this for EVERY new
// picker popup rather than re-deriving the traps.
export { placeZoomedPopup, applyPopupZoom, popupZoom } from "../shared/popup_zoom.mjs";

// A read-only numbered gutter for a WRAPPING "one value per line" textarea.
export { attachLineNumbers } from "../shared/line_numbers.mjs";

export { onNodeDefsRefresh, runRefreshHandlers, installRefreshHook } from "../shared/refresh.mjs";

export { registerSweepProvider, getSweepProvider, sweepProviderFor, anyProviderOwns } from "../shared/sweep_targets.mjs";

export {
  createReaperColorPicker,
  openReaperColorPickerPopup,
  REAPER_PALETTE,
} from "../shared/color_picker.mjs";

export {
  createHelpButton,
  openHelpPopup,
  openHelpFor,
  closeHelpPopup,
  injectHelpCSS,
  registerNodeHelp,
  getNodeHelp,
  allNodeHelp,
} from "./help.mjs";

export {
  ACC,
  ACCENT_VAR,
  GLOBAL_ACCENT_SETTING,
  DEFAULT_ACCENT_PROP,
  registerNodeSettings,
  registerNodeAccent,
  getNodeSettings,
  openNodeSettings,
  openAccentPanel,
  createAccentSection,
  createOptionRows,
  nodeSetting,
  setNodeSetting,
  closeNodeSettingsPanel,
  closeNodeSettingsFor,
  accentOf,
  accentRgba,
  setNodeAccent,
  applyAccent,
  installNodeAccent,
  repaintAccent,
  repaintAllAccents,
  globalAccent,
  classAccentSetting,
} from "../shared/node_settings.mjs";
