// Save Image Reaper — node-body DOM + CSS (both renderers).
// Layout follows the user's Photoshop mockup (2026-07-03): minimal labels,
// one wrapping button row (format seg + mode seg + Copy/Open/Open Folder),
// and a Preview-Image-style viewer that gets most of the node: single image
// fills the area, batches show as a GRID (click a cell to expand, ✕ back).
// The flex column lives on an INNER absolute layer (.red-si-inner) because
// ComfyUI forces the addDOMWidget ROOT to inline display:block on rebuild /
// collapse (see the Nodes 2.0 clobber note in CLAUDE.md).

import { DEFAULT_STATE, FORMATS } from "./state.mjs?reaper=2";

export function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

let _cssDone = false;
export function injectCSS() {
  if (_cssDone || document.getElementById("red-si-css")) {
    _cssDone = true;
    return;
  }
  _cssDone = true;
  const s = document.createElement("style");
  s.id = "red-si-css";
  s.textContent = [
    ".red-si-root{position:relative;width:100%;height:100%;box-sizing:border-box;}",
    ".red-si-inner{position:absolute;inset:0;display:flex;flex-direction:column;gap:10px;padding:8px 10px 4px;box-sizing:border-box;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;}",
    // top strip that holds the fold/unfold toggle (left-aligned + pulled up so
    // it hugs the slots and doesn't leave a big empty gap on the right)
    ".red-si-topbar{display:flex;justify-content:flex-start;align-items:center;flex:0 0 auto;min-height:20px;margin:-6px 0 -6px;}",
    // orange square + white triangle, same idea as the group fold icon
    ".red-si-fold{width:24px;height:22px;border:none;border-radius:4px;background:var(--red-acc);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;padding:0;flex:0 0 auto;}",
    ".red-si-fold:hover{filter:brightness(1.12);}",
    ".red-si-fold i{display:block;width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;}",
    ".red-si-fold:not(.folded) i{border-bottom:6px solid #fff;}", // ▲ = fold up
    ".red-si-fold.folded i{border-top:6px solid #fff;}", // ▼ = open back up
    // gear beside the fold triangle - the SAME settings the right-click entry
    // opens, just reachable without hunting for a menu. The icon is the
    // bundled SVG as a CSS mask, never the ⚙ emoji: an emoji is drawn by the
    // OS, so it changes shape (and color) per platform (convention #28).
    ".red-si-gear{width:24px;height:22px;border:none;border-radius:4px;background:transparent;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;padding:0;flex:0 0 auto;margin-left:4px;}",
    ".red-si-gear::before{content:'⚙';display:block;font-size:15px;line-height:1;color:#bbb;}",
    ".red-si-gear:hover::before{color:var(--red-acc);}",
    ".red-si-lab{display:block;font-size:10px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--red-acc);margin-bottom:4px;}",
    ".red-si-row{display:flex;gap:6px;align-items:center;}",
    ".red-si-field{flex:1;min-width:0;background:#1d1d1d;border:1px solid #444;border-radius:4px;color:#e0e0e0;padding:5px 8px;font-size:12px;outline:none;box-sizing:border-box;font-family:inherit;width:100%;}",
    ".red-si-field:focus{border-color:var(--red-acc);}",
    ".red-si-field.mono{font-family:Consolas,ui-monospace,monospace;font-size:12px;}",
    ".red-si-btn{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.16);color:#ccc;border-radius:4px;padding:5px 10px;font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;flex:0 0 auto;font-family:inherit;user-select:none;}",
    ".red-si-btn:hover{background:var(--red-acc);border-color:var(--red-acc);color:#fff;}",
    ".red-si-btn:disabled{opacity:.5;cursor:default;}",
    ".red-si-btn:disabled:hover{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.16);color:#ccc;}",
    // solid BRAND action buttons (Preview Image parity)
    ".red-si-primary{background:var(--red-acc);border-color:var(--red-acc);color:#fff;}",
    ".red-si-primary:hover{background:var(--red-acc);border-color:var(--red-acc);color:#fff;filter:brightness(1.12);}",
    ".red-si-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;}",
    ".red-si-chip{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.14);color:#ccc;border-radius:4px;padding:2px 7px;font-size:11px;cursor:pointer;font-family:inherit;user-select:none;}",
    ".red-si-chip:hover{border-color:var(--red-acc);color:#eee;}",
    ".red-si-prev{background:#1d1d1d;border:1px solid #444;border-radius:4px;padding:6px 8px;margin-top:8px;}",
    ".red-si-prevlab{font-size:10px;color:#8f8f8f;margin-bottom:2px;}",
    ".red-si-prevpath{font-family:Consolas,ui-monospace,monospace;font-size:11px;color:#ffb59e;word-break:break-all;line-height:1.45;}",
    ".red-si-hint{font-size:10px;color:#8f8f8f;margin-top:4px;line-height:1.5;}",
    // toggles are rounded PILLS so they read as switches, not action buttons
    // (the rectangular orange buttons are the actions - user request)
    ".red-si-seg{display:inline-flex;border:1px solid #444;border-radius:999px;overflow:hidden;flex:0 0 auto;}",
    ".red-si-seg button{background:#1d1d1d;color:#aaa;border:none;padding:4px 11px;font-size:12px;cursor:pointer;font-family:inherit;}",
    ".red-si-seg button.on{background:var(--red-acc);color:#fff;}",
    // the action buttons share the leftover row space EQUALLY and the row
    // ends flush with the right edge (flex-wrap only as a narrow fallback)
    ".red-si-btnrow{display:flex;flex-wrap:wrap;gap:6px;align-items:stretch;}",
    ".red-si-grow{flex:1 1 0;min-width:0;justify-content:center;}",
    // ── the viewer ──
    ".red-si-saved{flex:1 1 0;min-height:0;display:flex;flex-direction:column;gap:3px;}",
    ".red-si-view{position:relative;flex:1 1 0;min-height:120px;background:#151515;border:1px solid #3c3c3c;border-radius:4px;overflow:hidden;}",
    ".red-si-view.has{background:transparent;border-color:transparent;}",
    ".red-si-big{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;cursor:pointer;display:none;}",
    ".red-si-ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#777;font-size:11px;padding:8px;text-align:center;}",
    ".red-si-grid{position:absolute;inset:0;display:none;gap:4px;}",
    ".red-si-view.gridmode .red-si-grid{display:grid;}",
    ".red-si-cell{position:relative;overflow:hidden;cursor:pointer;display:flex;align-items:center;justify-content:center;min-width:0;min-height:0;}",
    ".red-si-cell img{width:100%;height:100%;object-fit:contain;display:block;}",
    ".red-si-cell:hover{outline:1px solid var(--red-acc);outline-offset:-1px;border-radius:3px;}",
    ".red-si-cellbadge{position:absolute;right:4px;bottom:4px;background:rgba(0,0,0,.55);color:#ddd;font-size:10px;padding:0 5px;border-radius:3px;pointer-events:none;}",
    ".red-si-nav{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.5);border:1px solid rgba(255,255,255,.18);color:#ddd;border-radius:4px;padding:4px 7px;font-size:11px;cursor:pointer;display:none;}",
    ".red-si-view.has:hover .red-si-nav.show{display:block;}",
    ".red-si-nav.prev{left:6px;}",
    ".red-si-nav.next{right:6px;}",
    ".red-si-nav:hover{background:var(--red-acc);border-color:var(--red-acc);color:#fff;}",
    ".red-si-count{position:absolute;right:6px;bottom:6px;background:rgba(0,0,0,.55);color:#ddd;font-size:11px;padding:1px 7px;border-radius:3px;display:none;}",
    ".red-si-x{position:absolute;top:6px;right:6px;background:rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.18);color:#ddd;border-radius:4px;padding:2px 9px;font-size:11px;cursor:pointer;display:none;}",
    ".red-si-x:hover{background:var(--red-acc);border-color:var(--red-acc);color:#fff;}",
    // one small info line under the image: dims + save summary + flashes
    ".red-si-info{flex:0 0 auto;text-align:center;font-size:11px;color:#8f8f8f;min-height:12px;line-height:1.25;word-break:break-word;}",
    // right-click settings panel (Run Timer palette; DROPPED by mistake in
    // the mockup-v2 rewrite - the panel rendered as an invisible unstyled
    // div at the page bottom. Keep this block when restyling the face!)
    ".red-si-panel{position:fixed;z-index:10010;width:300px;max-width:94vw;background:#1a1a1a;border:1px solid #444;border-radius:6px;box-shadow:0 8px 24px rgba(0,0,0,0.6);font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden;max-height:88vh;display:flex;flex-direction:column;}",
    ".red-si-phead{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid #333;color:#ddd;font-size:13px;font-weight:600;cursor:move;}",
    ".red-si-px{border:0;background:transparent;color:#999;font-size:13px;cursor:pointer;padding:2px 7px;border-radius:4px;}",
    ".red-si-px:hover{color:#fff;}",
    ".red-si-pbody{padding:12px;display:flex;flex-direction:column;gap:12px;color:#ddd;overflow-y:auto;min-height:0;}",
    ".red-si-prow{display:flex;align-items:center;gap:9px;}",
    ".red-si-plab{font-size:12px;color:#ddd;}",
    ".red-si-psub{font-size:10px;color:#8f8f8f;margin-top:2px;line-height:1.4;}",
    ".red-si-qval{font-size:12px;color:var(--red-acc);min-width:24px;text-align:right;}",
    // "Buttons on the node" - on/off chips. Convention #13: idle is a bordered
    // dark chip, hover only brightens the border, ON is a solid accent fill.
    ".red-si-bgrid{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px;}",
    ".red-si-bchip{flex:1 1 58px;background:#1d1d1d;border:1px solid #444;color:#aaa;border-radius:4px;padding:4px 8px;font-size:11px;cursor:pointer;font-family:inherit;user-select:none;}",
    ".red-si-bchip:hover{border-color:var(--red-acc);color:#ddd;}",
    ".red-si-bchip.on{background:var(--red-acc);border-color:var(--red-acc);color:#fff;}",
    ".red-si-qsl{flex:1;min-width:0;accent-color:var(--red-acc);}",
    '.red-si-sw{width:30px;height:16px;border-radius:8px;background:#555;position:relative;display:inline-block;cursor:pointer;flex:0 0 auto;transition:background .15s;}',
    '.red-si-sw::after{content:"";position:absolute;top:2px;left:2px;width:12px;height:12px;border-radius:50%;background:#ccc;transition:left .15s;}',
    ".red-si-sw.on{background:var(--red-acc);}",
    ".red-si-sw.on::after{left:16px;background:#fff;}",
    // right-click menu on the preview image (Open / Copy / Save image)
    ".red-si-menu{position:fixed;z-index:10011;background:#1a1a1a;border:1px solid #444;border-radius:6px;padding:4px;min-width:150px;box-shadow:0 8px 24px rgba(0,0,0,0.6);font-family:'Segoe UI',system-ui,sans-serif;}",
    ".red-si-mitem{padding:6px 12px;font-size:12px;color:#ddd;border-radius:4px;cursor:pointer;white-space:nowrap;user-select:none;}",
    ".red-si-mitem:hover{background:var(--red-acc);color:#fff;}",
    // Nodes 2.0: hide the native output-image preview panel for this node
    ".lg-node:has(.red-si-root) .image-preview{display:none !important;}",
  ].join("\n");
  document.head.appendChild(s);
}

export function buildRoot() {
  const root = el("div", "red-si-root");
  const inner = el("div", "red-si-inner");
  root.appendChild(inner);

  // ── fold/unfold toggle (top strip, always visible) ──
  const topbar = el("div", "red-si-topbar");
  const foldBtn = el("button", "red-si-fold");
  foldBtn.type = "button";
  foldBtn.appendChild(el("i"));
  topbar.appendChild(foldBtn);
  const gearBtn = el("button", "red-si-gear");
  gearBtn.type = "button";
  gearBtn.title = "Settings: quality, counter digits, which buttons show, and more";
  topbar.appendChild(gearBtn);
  inner.appendChild(topbar);

  // ── folder (no label - the placeholder + hint say it all) ──
  const secFolder = el("div");
  const rowF = el("div", "red-si-row");
  const folderInput = el("input", "red-si-field");
  folderInput.type = "text";
  folderInput.spellcheck = false;
  folderInput.placeholder = "ComfyUI output folder";
  folderInput.title = "Where the images are saved. Empty = ComfyUI's output folder. To use a folder of your own, click Browse and pick it once - that approves it for good, and you can type or paste it from then on.";
  const browseBtn = el("button", "red-si-btn");
  browseBtn.type = "button";
  const browseLbl = el("span", null, "Browse");
  browseBtn.appendChild(browseLbl);
  browseBtn.title = "Pick a folder with the system folder dialog";
  rowF.appendChild(folderInput);
  rowF.appendChild(browseBtn);
  secFolder.appendChild(rowF);
  secFolder.appendChild(
    el("div", "red-si-hint", "Leave empty for the ComfyUI output folder. For your own folder, click Browse once.")
  );
  inner.appendChild(secFolder);

  // ── filename ──
  const secName = el("div");
  secName.appendChild(el("span", "red-si-lab", "Filename"));
  const patternInput = el("input", "red-si-field mono");
  patternInput.type = "text";
  patternInput.spellcheck = false;
  patternInput.placeholder = DEFAULT_STATE.pattern;
  patternInput.title = "Filename pattern. Click the chips to insert tokens; the line below shows the exact next file. Files never overwrite: the counter continues from the highest number already in the folder.";
  secName.appendChild(patternInput);
  const chipsWrap = el("div", "red-si-chips");
  secName.appendChild(chipsWrap);
  const prev = el("div", "red-si-prev");
  prev.appendChild(el("div", "red-si-prevlab", "Will save as"));
  const prevPath = el("div", "red-si-prevpath", "");
  prev.appendChild(prevPath);
  secName.appendChild(prev);
  secName.appendChild(el("div", "red-si-hint", "Type / in the name to create subfolders."));
  inner.appendChild(secName);

  // ── one wrapping button row: format + mode + actions (user's mockup) ──
  const secBtns = el("div");
  const btnRow = el("div", "red-si-btnrow");
  const segFmt = el("div", "red-si-seg");
  // One button per format, built from the FORMATS table and keyed by id so the
  // settings panel can hide any of them without this file knowing the rules.
  const fmtBtns = {};
  for (const f of FORMATS) {
    const b = el("button", null, f.label);
    b.type = "button";
    b.dataset.fmt = f.id;
    segFmt.appendChild(b);
    fmtBtns[f.id] = b;
  }
  fmtBtns.png.title = "Lossless PNG. Keeps transparency and embeds the workflow for drag-back reload.";
  fmtBtns.webp.title = "WebP: much smaller than PNG, keeps transparency, and it still drags back into ComfyUI to reload the workflow.";
  fmtBtns.jpg.title = "Smaller JPG files. Quality is in the settings. No transparency, and ComfyUI cannot reload a workflow from a JPG.";
  const segMode = el("div", "red-si-seg");
  const modeSave = el("button", null, "Save");
  modeSave.type = "button";
  modeSave.title = "Write the files on every run";
  const modePreview = el("button", null, "Preview");
  modePreview.type = "button";
  modePreview.title = "Show the images on the node without writing anything to your folder";
  segMode.appendChild(modeSave);
  segMode.appendChild(modePreview);
  const btnCopy = el("button", "red-si-btn red-si-primary red-si-grow", "Copy");
  btnCopy.type = "button";
  btnCopy.title = "Copy the shown image to the clipboard";
  const btnOpen = el("button", "red-si-btn red-si-primary red-si-grow", "Open");
  btnOpen.type = "button";
  btnOpen.title = "Open the shown image in a new browser tab";
  const btnFolder = el("button", "red-si-btn red-si-primary red-si-grow", "Folder");
  btnFolder.type = "button";
  btnFolder.title = "Open the save folder in your file explorer (the window can appear on the taskbar)";
  // order (user pick): Open, Copy, Open Folder, then the PNG/JPG + Save/Preview pills
  btnRow.appendChild(btnOpen);
  btnRow.appendChild(btnCopy);
  btnRow.appendChild(btnFolder);
  btnRow.appendChild(segFmt);
  btnRow.appendChild(segMode);
  secBtns.appendChild(btnRow);
  inner.appendChild(secBtns);

  // ── the viewer: single image fills, batches show a grid ──
  const secSaved = el("div", "red-si-saved");
  const view = el("div", "red-si-view");
  const bigImg = el("img", "red-si-big");
  const grid = el("div", "red-si-grid");
  const ph = el("div", "red-si-ph", "Run the workflow to save and preview the result here");
  const navPrev = el("button", "red-si-nav prev", "◀");
  navPrev.type = "button";
  navPrev.title = "Previous image";
  const navNext = el("button", "red-si-nav next", "▶");
  navNext.type = "button";
  navNext.title = "Next image";
  const counter = el("div", "red-si-count", "");
  const closeX = el("button", "red-si-x", "✕");
  closeX.type = "button";
  closeX.title = "Back to the grid";
  view.appendChild(bigImg);
  view.appendChild(grid);
  view.appendChild(ph);
  view.appendChild(navPrev);
  view.appendChild(navNext);
  view.appendChild(counter);
  view.appendChild(closeX);
  secSaved.appendChild(view);
  const infoLine = el("div", "red-si-info", "");
  secSaved.appendChild(infoLine);
  inner.appendChild(secSaved);

  return {
    root,
    inner,
    topbar,
    foldBtn,
    gearBtn,
    segFmt,
    fmtBtns,
    secFolder,
    secName,
    secBtns,
    folderInput,
    browseBtn,
    browseLbl,
    patternInput,
    chipsWrap,
    prevPath,
    modeSave,
    modePreview,
    btnCopy,
    btnOpen,
    btnFolder,
    savedSec: secSaved,
    view,
    grid,
    bigImg,
    ph,
    navPrev,
    navNext,
    counter,
    closeX,
    infoLine,
  };
}
