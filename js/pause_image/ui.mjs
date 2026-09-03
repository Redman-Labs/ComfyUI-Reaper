// Pause Image Reaper - the node body UI, built as ONE DOM widget so it
// renders identically in the Classic and Nodes 2.0 renderers with zero
// isVueNodes() branching (the project's recommended dual-mode strategy).
// Layout top->bottom: toggle pill (Pause | Pass), status line, the two
// action buttons (Regenerate, Continue), then the preview image filling the
// remaining height at the bottom.
import { BRAND_CSS } from "../shared/utils.mjs";
import { getState } from "../shared/pause_image_state.mjs";

const HEADER_H = 130;       // toggle + status + two button rows
const PREVIEW_MIN_H = 150;  // minimum preview area
const DIMS_H = 16;          // the dimensions line under the preview
export const NODE_MIN_W = 300;  // room for the 4-button utility row
// Constant getMinHeight (Vue Compat #18): a fixed number is byte-identical on
// every save/load, so node.size never jitters and the workflow is never
// falsely flagged "modified".
export const NODE_MIN_H = HEADER_H + PREVIEW_MIN_H + DIMS_H;

function injectCSS() {
  if (document.getElementById("red-pause-css")) return;
  const s = document.createElement("style");
  s.id = "red-pause-css";
  s.textContent = `
    .red-lb-root { display:flex; flex-direction:column; flex:1 1 0; min-height:0;
      box-sizing:border-box; padding:6px; gap:6px; font:12px sans-serif; color:#ddd;
      overflow:hidden; }
    .red-lb-toggle { display:flex; background:rgba(0,0,0,0.25); border-radius:6px; padding:2px; gap:2px; flex:0 0 auto; }
    .red-lb-seg { flex:1 1 0; text-align:center; padding:4px 0; border-radius:5px; cursor:pointer;
      color:rgba(255,255,255,0.6); user-select:none; border:1px solid transparent; }
    .red-lb-seg.active { background:${BRAND_CSS}; color:#fff; border-color:${BRAND_CSS}; }
    .red-lb-seg:not(.active):hover { border-color:${BRAND_CSS}; color:#ddd; }
    .red-lb-status { flex:0 0 auto; font-size:11px; color:rgba(255,255,255,0.7); min-height:14px; text-align:center; }
    .red-lb-btns { display:flex; gap:6px; flex:0 0 auto; }
    .red-lb-btn { flex:1 1 0; min-width:0; height:26px; line-height:24px; border-radius:4px;
      border:1px solid rgba(255,255,255,0.18); background:rgba(255,255,255,0.05);
      color:rgba(255,255,255,0.85); font:12px sans-serif; cursor:pointer; padding:0 6px;
      box-sizing:border-box; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; user-select:none; }
    .red-lb-btn:hover:not(:disabled) { border-color:${BRAND_CSS}; color:#fff; }
    .red-lb-btn.primary:not(:disabled) { background:${BRAND_CSS}; border-color:${BRAND_CSS}; color:#fff; }
    .red-lb-btn.primary:hover:not(:disabled) { background:#ff8a5e; border-color:#ff8a5e; }
    .red-lb-btn:disabled { opacity:0.45; cursor:default; }
    .red-lb-preview { flex:1 1 0; min-height:0; position:relative; background:#1d1d1d;
      border:1px solid #333; border-radius:4px; overflow:hidden; }
    .red-lb-img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; display:none; }
    .red-lb-empty { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
      text-align:center; color:#777; font-size:11px; padding:8px; box-sizing:border-box; }
    .red-lb-dims { flex:0 0 auto; text-align:center; font-size:10px; color:#aaa;
      min-height:13px; line-height:13px; }
  `;
  document.head.appendChild(s);
}

// Build the DOM widget element. callbacks: { onGate(gate), onContinue(), onRegenerate() }.
// Caches element refs on node._redPauseEls for renderPause / showFrame.
export function buildPauseWidget(node, callbacks) {
  injectCSS();
  const root = document.createElement("div");
  root.className = "red-lb-root";

  const toggle = document.createElement("div");
  toggle.className = "red-lb-toggle";
  const segPause = document.createElement("div");
  segPause.className = "red-lb-seg";
  segPause.textContent = "Pause";
  segPause.title = "Pause here on Run so you can preview before continuing";
  const segPass = document.createElement("div");
  segPass.className = "red-lb-seg";
  segPass.textContent = "Pass";
  segPass.title = "Pass straight through; run the whole workflow in one go";
  toggle.append(segPause, segPass);
  segPause.addEventListener("click", () => callbacks.onGate("pause"));
  segPass.addEventListener("click", () => callbacks.onGate("pass"));

  const status = document.createElement("div");
  status.className = "red-lb-status";

  // Row 1: the workflow decisions.
  const btns = document.createElement("div");
  btns.className = "red-lb-btns";
  const btnContinue = document.createElement("button");
  btnContinue.className = "red-lb-btn primary";
  btnContinue.textContent = "▶ Continue";
  btnContinue.title = "Run only the rest of the workflow, from the snapshot";
  const btnRegen = document.createElement("button");
  btnRegen.className = "red-lb-btn";
  btnRegen.textContent = "⟳ Regenerate";
  btnRegen.title = "Roll a new image at this point (respects your seed)";
  // Regenerate on the LEFT, Continue on the RIGHT (Continue is the primary
  // "commit" action; putting it right of Regenerate reads less confusingly).
  btns.append(btnRegen, btnContinue);

  // Row 2: utilities that act on the previewed image.
  const btns2 = document.createElement("div");
  btns2.className = "red-lb-btns";
  const btnCopy = document.createElement("button");
  btnCopy.className = "red-lb-btn";
  btnCopy.textContent = "Copy";
  btnCopy.title = "Copy the previewed image to the clipboard";
  const btnSaveDisk = document.createElement("button");
  btnSaveDisk.className = "red-lb-btn";
  btnSaveDisk.textContent = "Save Disk";
  btnSaveDisk.title = "Save the previewed image to a folder on your computer";
  const btnSaveOut = document.createElement("button");
  btnSaveOut.className = "red-lb-btn";
  btnSaveOut.textContent = "Save Output";
  btnSaveOut.title = "Save the previewed image to ComfyUI's output folder";
  const btnOpen = document.createElement("button");
  btnOpen.className = "red-lb-btn";
  btnOpen.textContent = "Open";
  btnOpen.title = "Open the previewed image in a new browser tab";
  btns2.append(btnCopy, btnSaveDisk, btnSaveOut, btnOpen);

  // stopPropagation so the click doesn't reach the canvas (deselect / drag).
  btnContinue.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onContinue(); });
  btnRegen.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onRegenerate(); });
  btnCopy.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onCopy(); });
  btnSaveDisk.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onSaveDisk(); });
  btnSaveOut.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onSaveOutput(); });
  btnOpen.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onOpen(); });

  const preview = document.createElement("div");
  preview.className = "red-lb-preview";
  const img = document.createElement("img");
  img.className = "red-lb-img";
  const empty = document.createElement("div");
  empty.className = "red-lb-empty";
  empty.textContent = "Press Run to preview the image here";
  preview.append(img, empty);

  // Dimensions line sits BELOW the preview (its own row), not over the image.
  const dims = document.createElement("div");
  dims.className = "red-lb-dims";

  root.append(toggle, status, btns, btns2, preview, dims);

  node._redPauseEls = {
    segPause, segPass, status,
    btnContinue, btnRegen, btnCopy, btnSaveDisk, btnSaveOut, btnOpen,
    img, empty, dims,
  };
  return root;
}

// Re-render the controls from current state. DOM-only (never touches node.size
// or node.properties values), so it is safe to call on the load path.
export function renderPause(node) {
  const els = node._redPauseEls;
  if (!els) return;
  const s = getState(node);
  const paused = s.gate === "pause";
  const hasSnap = !!node._redPauseHasSnapshot;  // runtime-only (Vue Compat #18)
  els.segPause.classList.toggle("active", paused);
  els.segPass.classList.toggle("active", !paused);

  // Continue / Regenerate only make sense in Pause mode; Copy / Open work
  // whenever there is a captured image to act on (any mode).
  els.btnRegen.disabled = !paused;
  els.btnContinue.disabled = !paused || !hasSnap;
  els.btnCopy.disabled = !hasSnap;
  els.btnSaveDisk.disabled = !hasSnap;
  els.btnSaveOut.disabled = !hasSnap;
  els.btnOpen.disabled = !hasSnap;

  if (node._redPauseFlash) {
    els.status.textContent = node._redPauseFlash;
  } else if (node._redPauseBusy) {
    els.status.textContent = node._redPauseBusy;
  } else if (!paused) {
    els.status.textContent = "Passing through: whole workflow runs";
  } else if (hasSnap) {
    els.status.textContent = "Paused and ready. Continue to run the rest.";
  } else {
    els.status.textContent = "Paused. Press Run to preview.";
  }
}

// Build the /view URL for a snapshot frame. Cache-busted because the snapshot
// filename is deterministic per node (it's overwritten each pause run).
export function frameViewUrl(frame) {
  const params = new URLSearchParams({
    filename: frame.filename,
    subfolder: frame.subfolder || "",
    type: frame.type || "temp",
    t: String(Date.now()),
  });
  return `/view?${params.toString()}`;
}

// Load + show a snapshot frame in the preview. frame = {filename, subfolder, type}.
// On success enables Continue; on error (temp PNG cleared after a restart) shows
// an "expired" message and disables Continue.
export function showFrame(node, frame) {
  const els = node._redPauseEls;
  if (!els || !frame || !frame.filename) return;
  const url = frameViewUrl(frame);
  const { img, empty, dims } = els;
  img.onload = () => {
    img.style.display = "block";
    empty.style.display = "none";
    dims.textContent = `${img.naturalWidth} × ${img.naturalHeight}`;
    // Runtime-only flag (NOT node.properties) so this load-time resolution
    // never rewrites serialized state and dirties the workflow (Vue Compat #18).
    node._redPauseHasSnapshot = true;
    renderPause(node);
  };
  img.onerror = () => {
    img.style.display = "none";
    empty.style.display = "flex";
    empty.textContent = "Preview expired. Press Run to pause again.";
    dims.textContent = "";
    node._redPauseHasSnapshot = false;
    renderPause(node);
  };
  img.src = url;
}
