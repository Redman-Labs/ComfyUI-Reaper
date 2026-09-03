// Pause Text Reaper - the node body UI, ONE DOM widget for both renderers.
// Layout: a STATUS line sits in the empty band BETWEEN the input and output dots
// (Classic paints it on the canvas via onDrawForeground; Nodes 2.0 shows a DOM
// band lifted into the slot row by the block-nudge - see index.js). Below that:
// the editable text box (fills the height) whose header carries the field label,
// the Pause/Pass toggle and the Copy/Revert icons; a compact search row and
// synchronized match-highlighting layer; then the count + Regenerate / Continue
// buttons. No status dot (it read as an input dot).
import { BRAND_CSS } from "../shared/utils.mjs";
import { api } from "/scripts/api.js";
import { getState, isEdited } from "./state.mjs";

// Fixed vertical budget for the non-fill rows -> getMinHeight is a per-renderer
// CONSTANT (Vue Compat #18): byte-identical every save/load, node.size never
// jitters. The band costs 0 height in Classic (painted) and BAND_H in Nodes 2.0
// (in-flow, then the nudge overlaps it onto the slot row).
const PAD = 6;
const HDR_H = 24;
const SEARCH_H = 25;
const BODY_MIN_H = 120;
const BOT_H = 28;
const BAND_H = 18;
const CORE_H = PAD + HDR_H + SEARCH_H + BODY_MIN_H + PAD + BOT_H + PAD;
// Minimum width where the count + both buttons fit comfortably (like the wide
// reference node). Below this the buttons don't fit: Classic clamps here in
// onResize; Nodes 2.0 snaps back here on resize release (it has no live width
// clamp). Kept modest so the node is still fairly compact.
export const NODE_MIN_W = 400;
export function nodeMinH(vue) { return CORE_H + (vue ? BAND_H + PAD : 0); }

function injectCSS() {
  if (document.getElementById("red-pt-css")) return;
  const s = document.createElement("style");
  s.id = "red-pt-css";
  s.textContent = `
    .red-pt-root { position:relative; display:flex; flex-direction:column; flex:1 1 0;
      min-height:0; box-sizing:border-box; padding:${PAD}px; gap:${PAD}px;
      font:12px sans-serif; color:#ddd; overflow:hidden; background:transparent; }
    /* Status band. Classic hides it (painted on canvas); Nodes 2.0 shows it and
       the nudge lifts it onto the slot row. Reserve the sides for the dot labels. */
    .red-pt-band { flex:0 0 auto; height:${BAND_H}px; line-height:${BAND_H}px;
      font:11px sans-serif; color:rgba(255,255,255,0.72); text-align:center;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis; pointer-events:none;
      padding:0 66px; box-sizing:border-box; }

    .red-pt-box { flex:1 1 0; min-height:0; display:flex; flex-direction:column;
      background:#1d1d1d; border:1px solid #333; border-radius:5px; overflow:hidden; }
    .red-pt-box.pt-focus { border-color:${BRAND_CSS}; }
    .red-pt-box.pt-off { opacity:0.55; }
    .red-pt-hdr { flex:0 0 auto; display:flex; align-items:center; gap:6px;
      padding:3px 6px 3px 9px; border-bottom:1px solid #2c2c2c; background:rgba(255,255,255,0.02); }
    .red-pt-hlbl { font:10px 'Segoe UI',-apple-system,sans-serif; color:#8f8f8f; flex:1 1 0;
      overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .red-pt-toggle { display:flex; background:rgba(0,0,0,0.25); border-radius:5px; padding:1px; gap:2px; flex:0 0 auto; }
    .red-pt-seg { text-align:center; padding:2px 9px; border-radius:4px; cursor:pointer;
      color:rgba(255,255,255,0.6); user-select:none; border:1px solid transparent; font-size:10px; }
    .red-pt-seg.active { background:${BRAND_CSS}; color:#fff; border-color:${BRAND_CSS}; }
    .red-pt-seg.pause-mode.active { background:#a40505; border-color:#a40505; color:#fff; }
    .red-pt-seg.pass-mode.active { background:#04a72a; border-color:#04a72a; color:#fff; }
    .red-pt-seg:not(.active):hover { border-color:${BRAND_CSS}; color:#ddd; }
    .red-pt-hic { width:19px; height:18px; border-radius:4px; display:flex; align-items:center;
      justify-content:center; cursor:pointer; background:rgba(255,255,255,0.06);
      border:1px solid rgba(255,255,255,0.14); color:rgba(255,255,255,0.72); flex:0 0 auto; }
    .red-pt-hic:hover:not(.off) { background:${BRAND_CSS}; border-color:${BRAND_CSS}; color:#fff; }
    .red-pt-hic.ok, .red-pt-hic.ok:hover { background:#3ec371; border-color:#3ec371; color:#fff; }
    .red-pt-hic.off { opacity:0.35; cursor:default; }
    .red-pt-search { flex:0 0 ${SEARCH_H}px; display:flex; align-items:center; gap:5px;
      padding:2px 6px; box-sizing:border-box; border-bottom:1px solid #2c2c2c;
      background:rgba(0,0,0,0.12); }
    .red-pt-search-input { flex:1 1 0; min-width:0; height:20px; box-sizing:border-box;
      border:1px solid #3a3a3a; border-radius:4px; outline:none; padding:1px 6px;
      background:#151515; color:#ddd; font:10px sans-serif; }
    .red-pt-search-input:focus { border-color:${BRAND_CSS}; }
    .red-pt-search-count { flex:0 0 auto; min-width:48px; text-align:right;
      color:#999; font:9px sans-serif; white-space:nowrap; }
    .red-pt-search-btn { flex:0 0 22px; width:22px; height:20px; display:flex;
      align-items:center; justify-content:center; padding:0; border-radius:4px;
      border:1px solid rgba(255,255,255,0.16); background:rgba(255,255,255,0.05);
      color:#bbb; cursor:pointer; }
    .red-pt-search-btn:hover { background:${BRAND_CSS}; border-color:${BRAND_CSS}; color:#fff; }
    .red-pt-search-btn.pt-spell-on { background:#fd6e6d; border-color:#fd6e6d; color:#171717; }
    .red-pt-search-btn.pt-spell-on:hover { background:#ff8584; border-color:#ff8584; color:#171717; }
    .red-pt-editor { position:relative; flex:1 1 0; min-height:0; overflow:hidden; }
    .red-pt-highlights, .red-pt-ta { position:absolute; inset:0; width:100%; height:100%;
      box-sizing:border-box; margin:0; border:0; font:12px monospace; line-height:1.4;
      padding:6px 8px; white-space:pre-wrap; overflow-wrap:break-word; tab-size:8; }
    .red-pt-highlights { z-index:0; overflow:hidden; visibility:hidden;
      color:transparent !important; -webkit-text-fill-color:transparent !important;
      text-shadow:none !important; pointer-events:none; scrollbar-width:none; }
    .red-pt-highlights.pt-search-active { visibility:visible; }
    .red-pt-highlights::-webkit-scrollbar { display:none; }
    .red-pt-highlights mark { color:transparent !important;
      -webkit-text-fill-color:transparent !important; text-shadow:none !important;
      background:rgba(255,215,0,0.48);
      outline:1px solid rgba(255,235,120,0.5); border-radius:2px; }
    .red-pt-highlights mark.pt-spelling {
      background:#fd6e6d; outline:1px solid #ff8a89; border-radius:2px;
    }
    .red-pt-ta { z-index:1; min-height:0; background:transparent; color:#e0e0e0;
      outline:none; resize:none; overflow:auto; caret-color:#e0e0e0; }
    .red-pt-ta::placeholder { color:#5c5c5c; font-style:italic; }
    .red-pt-ta:disabled { color:#9a9a9a; }

    /* flex-wrap so if the node is transiently narrower than the buttons (during a
       resize drag, before the width snaps back), Continue wraps to a new line
       instead of spilling past / being clipped at the right edge. */
    .red-pt-bot { display:flex; align-items:center; gap:6px; flex:0 0 auto; flex-wrap:wrap; justify-content:flex-end; }
    .red-pt-count { flex:1 1 0; min-width:0; font-size:10px; color:#aaa;
      overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .red-pt-btn { height:26px; padding:0 12px; border-radius:4px;
      border:1px solid rgba(255,255,255,0.18); background:rgba(255,255,255,0.05);
      color:rgba(255,255,255,0.85); font:12px sans-serif; cursor:pointer;
      box-sizing:border-box; white-space:nowrap; user-select:none; flex:0 0 auto; }
    .red-pt-btn:hover:not(:disabled) { border-color:${BRAND_CSS}; color:#fff; }
    .red-pt-btn.primary:not(:disabled) { background:${BRAND_CSS}; border-color:${BRAND_CSS}; color:#fff; }
    .red-pt-btn.primary:hover:not(:disabled) { background:#ff8a5e; border-color:#ff8a5e; }
    .red-pt-btn.continue-ready:not(:disabled) { background:#04a72a; border-color:#04a72a; color:#fff; }
    .red-pt-btn.continue-ready:hover:not(:disabled) { background:#038c23; border-color:#d85b5b; color:#fff; }
    .red-pt-btn.regenerate-ready:not(:disabled) { background:#e2ac06; border-color:#e2ac06; color:#111; }
    .red-pt-btn.regenerate-ready:hover:not(:disabled) { background:#f2bd18; border-color:#ffe07a; color:#111; }
    .red-pt-btn:disabled { opacity:0.45; cursor:default; }
  `;
  document.head.appendChild(s);
}

const COPY_SVG =
  '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" ' +
  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<rect x="9" y="9" width="11" height="11" rx="2"/>' +
  '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';
const REVERT_SVG =
  '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" ' +
  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-1"/></svg>';
const SEARCH_SVG =
  '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" ' +
  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>';
const SPELLCHECK_SVG =
  '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" ' +
  'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M3 17h7"/><path d="m4 14 3-8 3 8"/><path d="M5 11h4"/>' +
  '<path d="m13 14 3 3 5-6"/></svg>';

function syncSearchScroll(node) {
  const els = node._redPtEls;
  if (!els) return;
  els.highlights.scrollTop = els.ta.scrollTop;
  els.highlights.scrollLeft = els.ta.scrollLeft;
}

// The ComfyUI frontend can override textarea typography, especially in Nodes
// 2.0. The highlight mirror must use the textarea's ACTUAL computed metrics or
// line wrapping drifts and a correct match is painted several lines away.
function syncSearchMetrics(node) {
  const els = node._redPtEls;
  if (!els) return;
  const { ta, highlights } = els;
  const computed = getComputedStyle(ta);
  for (const property of [
    "fontFamily",
    "fontSize",
    "fontStyle",
    "fontVariant",
    "fontWeight",
    "fontStretch",
    "lineHeight",
    "letterSpacing",
    "wordSpacing",
    "textAlign",
    "textIndent",
    "textTransform",
    "tabSize",
    "whiteSpace",
    "overflowWrap",
    "wordBreak",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
  ]) {
    highlights.style[property] = computed[property];
  }

  // A textarea's vertical scrollbar reduces its text-layout width. The mirror
  // hides its own scrollbar, so match that reduced client box explicitly.
  highlights.style.width = `${ta.clientWidth}px`;
  highlights.style.height = `${ta.clientHeight}px`;
}

function renderSearchHighlights(node) {
  const els = node._redPtEls;
  if (!els) return;
  const text = els.ta.value || "";
  const query = node._redPtSearchQuery || "";
  const spelling = Array.isArray(node._redPtSpellingRanges)
    ? node._redPtSpellingRanges
    : [];
  const fragment = document.createDocumentFragment();
  syncSearchMetrics(node);
  const ranges = spelling
    .filter((range) => Number.isInteger(range.start) && Number.isInteger(range.end))
    .map((range) => ({
      start: Math.max(0, Math.min(text.length, range.start)),
      end: Math.max(0, Math.min(text.length, range.end)),
      kind: "spelling",
    }))
    .filter((range) => range.end > range.start);
  let matches = 0;
  if (query) {
    const haystack = text.toLocaleLowerCase();
    const needle = query.toLocaleLowerCase();
    let cursor = 0;
    while (needle && cursor <= text.length) {
      const found = haystack.indexOf(needle, cursor);
      if (found < 0) break;
      ranges.push({ start: found, end: found + query.length, kind: "search" });
      matches += 1;
      cursor = found + query.length;
    }
  }
  els.highlights.classList.toggle("pt-search-active", ranges.length > 0);
  els.searchCount.textContent = query
    ? `${matches} match${matches === 1 ? "" : "es"}`
    : spelling.length
      ? `${spelling.length} error${spelling.length === 1 ? "" : "s"}`
      : "";

  if (ranges.length) {
    const boundaries = new Set([0, text.length]);
    for (const range of ranges) {
      boundaries.add(range.start);
      boundaries.add(range.end);
    }
    const points = [...boundaries].sort((a, b) => a - b);
    for (let index = 0; index < points.length - 1; index += 1) {
      const start = points[index];
      const end = points[index + 1];
      if (end <= start) continue;
      const covering = ranges.filter((range) => range.start <= start && range.end >= end);
      const kind = covering.some((range) => range.kind === "spelling")
        ? "spelling"
        : covering.length ? "search" : null;
      if (!kind) {
        fragment.appendChild(document.createTextNode(text.slice(start, end)));
        continue;
      }
      const mark = document.createElement("mark");
      if (kind === "spelling") mark.className = "pt-spelling";
      mark.textContent = text.slice(start, end);
      fragment.appendChild(mark);
    }
  }

  els.highlights.replaceChildren(fragment);
  syncSearchScroll(node);
  requestAnimationFrame(() => {
    if (!node.graph) return;
    syncSearchMetrics(node);
    syncSearchScroll(node);
  });
}

// The current status string, shared by the DOM band (Nodes 2.0) and the canvas
// paint (Classic). busy > flash > gate-derived.
export function statusText(node) {
  const s = getState(node);
  if (node._redPtBusy) return node._redPtBusy;
  if (node._redPtFlash) return node._redPtFlash;
  if (s.gate === "pass") return "Passing through: whole workflow runs";
  if (s.gate === "keep") return "Keeping this text: each Run makes an image";
  return isEdited(node) ? "Edited. Continue when ready." : "Paused. Edit and press Continue.";
}

// Build the DOM widget. callbacks: { onGate, onContinue, onRegenerate, onCopy,
// onRevert, onInput }. Caches refs on node._redPtEls.
export function buildPauseTextWidget(node, callbacks) {
  injectCSS();
  const root = document.createElement("div");
  root.className = "red-pt-root";

  // Status band (between the dots).
  const band = document.createElement("div");
  band.className = "red-pt-band";

  // The editable box; its header carries the label + Pause/Pass toggle + icons.
  const box = document.createElement("div");
  box.className = "red-pt-box";
  const hdr = document.createElement("div");
  hdr.className = "red-pt-hdr";
  const hlbl = document.createElement("span");
  hlbl.className = "red-pt-hlbl";
  hlbl.textContent = "text";
  const toggle = document.createElement("div");
  toggle.className = "red-pt-toggle";
  const segPause = document.createElement("div");
  segPause.className = "red-pt-seg pause-mode";
  segPause.textContent = "Pause";
  segPause.title = "Pause here on Run so you can edit before continuing";
  const segPass = document.createElement("div");
  segPass.className = "red-pt-seg pass-mode";
  segPass.textContent = "Pass";
  segPass.title = "Pass straight through; run the whole workflow in one go";
  const segKeep = document.createElement("div");
  segKeep.className = "red-pt-seg";
  segKeep.textContent = "Keep";
  segKeep.title = "Keep this text; every Run makes a new image with it (the model is skipped)";
  toggle.append(segPause, segPass, segKeep);
  const copyBtn = document.createElement("span");
  copyBtn.className = "red-pt-hic";
  copyBtn.innerHTML = COPY_SVG;
  copyBtn.title = "Copy this text";
  const revertBtn = document.createElement("span");
  revertBtn.className = "red-pt-hic";
  revertBtn.innerHTML = REVERT_SVG;
  revertBtn.title = "Put the model's original text back";
  hdr.append(hlbl, toggle, copyBtn, revertBtn);

  const search = document.createElement("div");
  search.className = "red-pt-search";
  const searchInput = document.createElement("input");
  searchInput.className = "red-pt-search-input";
  searchInput.type = "text";
  searchInput.placeholder = "Search text…";
  searchInput.title = "Search the main text. Matching is case-insensitive.";
  const searchCount = document.createElement("span");
  searchCount.className = "red-pt-search-count";
  const searchBtn = document.createElement("button");
  searchBtn.className = "red-pt-search-btn";
  searchBtn.type = "button";
  searchBtn.innerHTML = SEARCH_SVG;
  searchBtn.title = "Highlight every matching instance";
  searchBtn.setAttribute("aria-label", "Search text");
  const spellcheckBtn = document.createElement("button");
  spellcheckBtn.className = "red-pt-search-btn";
  spellcheckBtn.type = "button";
  spellcheckBtn.innerHTML = SPELLCHECK_SVG;
  spellcheckBtn.title = "Check spelling and highlight misspelled words";
  spellcheckBtn.setAttribute("aria-label", "Check spelling");
  search.append(searchInput, searchCount, searchBtn, spellcheckBtn);

  const editor = document.createElement("div");
  editor.className = "red-pt-editor";
  const highlights = document.createElement("div");
  highlights.className = "red-pt-highlights";
  highlights.setAttribute("aria-hidden", "true");
  const ta = document.createElement("textarea");
  ta.className = "red-pt-ta";
  // Reaper paints explicit server-returned ranges in the synchronized mirror.
  ta.spellcheck = false;
  ta.placeholder = "The model's text will appear here on Run";
  editor.append(highlights, ta);
  box.append(hdr, search, editor);

  // Bottom row: count + Regenerate / Continue.
  const bot = document.createElement("div");
  bot.className = "red-pt-bot";
  const count = document.createElement("span");
  count.className = "red-pt-count";
  const btnRegen = document.createElement("button");
  btnRegen.className = "red-pt-btn";
  btnRegen.textContent = "⟳ Regenerate";
  btnRegen.title = "Get fresh text: roll the seed of whatever is generating it upstream";
  const btnContinue = document.createElement("button");
  btnContinue.className = "red-pt-btn primary";
  btnContinue.textContent = "▶ Continue";
  btnContinue.title = "Run only the rest of the workflow with your edited text";
  bot.append(count, btnRegen, btnContinue);

  root.append(band, box, bot);

  // Events. stopPropagation so canvas drag/deselect/shortcuts don't fire.
  ta.addEventListener("input", () => {
    node._redPtSpellingRanges = [];
    node._redPtSpellcheckActive = false;
    spellcheckBtn.classList.remove("pt-spell-on");
    callbacks.onInput(ta.value);
    renderSearchHighlights(node);
  });
  ta.addEventListener("scroll", () => syncSearchScroll(node));
  ta.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") return;  // let run-workflow through
    e.stopPropagation();
  });
  ta.addEventListener("pointerdown", (e) => e.stopPropagation());
  ta.addEventListener("mousedown", (e) => e.stopPropagation());
  ta.addEventListener("focus", () => box.classList.add("pt-focus"));
  ta.addEventListener("blur", () => box.classList.remove("pt-focus"));

  const runSearch = () => {
    node._redPtSearchQuery = searchInput.value;
    renderSearchHighlights(node);
  };
  searchBtn.addEventListener("click", (e) => { e.stopPropagation(); runSearch(); });
  spellcheckBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    spellcheckBtn.disabled = true;
    spellcheckBtn.title = "Checking spelling…";
    try {
      const response = await api.fetchApi("/reaper/api/spellcheck", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: ta.value }),
      });
      if (!response.ok) throw new Error(`spellcheck failed: ${response.status}`);
      const payload = await response.json();
      node._redPtSpellingRanges = Array.isArray(payload.errors) ? payload.errors : [];
      node._redPtSpellcheckActive = true;
      spellcheckBtn.classList.add("pt-spell-on");
      renderSearchHighlights(node);
    } catch (error) {
      console.error("[Pause Text] spellcheck failed", error);
      node._redPtSpellingRanges = [];
      node._redPtSpellcheckActive = false;
      spellcheckBtn.classList.remove("pt-spell-on");
      renderSearchHighlights(node);
      searchCount.textContent = "Check failed";
    } finally {
      spellcheckBtn.disabled = false;
      spellcheckBtn.title = "Check spelling and highlight misspelled words";
    }
  });
  searchInput.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch();
    }
  });
  for (const el of [search, searchInput, searchBtn, spellcheckBtn]) {
    el.addEventListener("pointerdown", (e) => e.stopPropagation());
    el.addEventListener("mousedown", (e) => e.stopPropagation());
  }

  segPause.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onGate("pause"); });
  segPass.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onGate("pass"); });
  segKeep.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onGate("keep"); });
  copyBtn.addEventListener("click", (e) => { e.stopPropagation(); if (!copyBtn.classList.contains("off")) callbacks.onCopy(); });
  revertBtn.addEventListener("click", (e) => { e.stopPropagation(); if (!revertBtn.classList.contains("off")) callbacks.onRevert(); });
  for (const b of [segPause, segPass, segKeep, copyBtn, revertBtn]) {
    b.addEventListener("pointerdown", (e) => e.stopPropagation());
    b.addEventListener("mousedown", (e) => e.stopPropagation());
  }
  btnRegen.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onRegenerate(); });
  btnContinue.addEventListener("click", (e) => { e.stopPropagation(); callbacks.onContinue(); });

  node._redPtEls = {
    root, band, box, hlbl, segPause, segPass, segKeep, copyBtn, revertBtn,
    searchInput, searchCount, searchBtn, spellcheckBtn, highlights, ta, count, btnRegen, btnContinue,
  };
  if (typeof ResizeObserver !== "undefined") {
    node._redPtSearchRO?.disconnect?.();
    node._redPtSearchRO = new ResizeObserver(() => {
      syncSearchMetrics(node);
      syncSearchScroll(node);
    });
    node._redPtSearchRO.observe(editor);
    node._redPtSearchRO.observe(ta);
  }
  renderSearchHighlights(node);
  return root;
}

function countLabel(text) {
  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  return `${chars} char${chars === 1 ? "" : "s"} · ${words} word${words === 1 ? "" : "s"}`;
}

export function flashIcon(iconEl) {
  if (!iconEl) return;
  iconEl.classList.add("ok");
  setTimeout(() => iconEl.classList.remove("ok"), 700);
}

// Push the stored text into the textarea. Only sets when different so it never
// fights the user's caret mid-type.
export function syncText(node) {
  const els = node._redPtEls;
  if (!els) return;
  const s = getState(node);
  if (els.ta.value !== s.text) els.ta.value = s.text;
  renderSearchHighlights(node);
}

// Clear the runtime-only search when a fresh upstream text payload replaces the
// editor contents. Ordinary typing deliberately keeps the active search live.
export function resetSearch(node) {
  node._redPtSearchQuery = "";
  node._redPtSpellcheckActive = false;
  node._redPtSpellingRanges = [];
  const els = node._redPtEls;
  if (!els) return;
  els.searchInput.value = "";
  els.spellcheckBtn.classList.remove("pt-spell-on");
  renderSearchHighlights(node);
}

// Re-render controls from state. DOM-only, safe on the load path (Vue Compat #18).
// The status band is a DOM element in BOTH renderers (index.js floats it into the
// slot dead-space in Classic, nudges the slot block in Nodes 2.0).
export function renderPause(node) {
  const els = node._redPtEls;
  if (!els) return;
  const s = getState(node);
  const gate = s.gate;
  const pass = gate === "pass";
  const keep = gate === "keep";
  const edited = isEdited(node);
  // Editing + the action buttons are ON in Pause and Keep, OFF in Pass (which
  // runs the model fresh and ignores the box).
  const editable = !pass;

  els.segPause.classList.toggle("active", gate === "pause");
  els.segPass.classList.toggle("active", pass);
  els.segKeep.classList.toggle("active", keep);

  els.ta.disabled = !editable;
  els.box.classList.toggle("pt-off", pass);
  els.ta.placeholder = editable
    ? "The model's text will appear here on Run"
    : "Passing through - the model's text is sent as-is";

  els.hlbl.innerHTML = edited
    ? 'text · <span style="color:' + BRAND_CSS + '">edited</span>'
    : "text";

  const hasText = !!s.text;
  els.copyBtn.classList.toggle("off", !hasText);
  els.revertBtn.classList.toggle("off", !edited);
  // Regenerate is greyed in Keep mode: Keep reuses the current text, so getting a
  // new prompt from the model doesn't belong here - switch back to Pause for that.
  els.btnRegen.disabled = !editable || keep || !!node._redPtBusy;
  els.btnRegen.classList.toggle("regenerate-ready", !els.btnRegen.disabled);
  els.btnRegen.title = keep
    ? "Switch to Pause to get fresh text from the model"
    : "Get fresh text: roll the seed of whatever is generating it upstream";
  els.btnContinue.disabled = !editable || !!node._redPtBusy;
  els.btnContinue.classList.toggle(
    "continue-ready",
    gate === "pause" && hasText && !els.btnContinue.disabled,
  );
  // In Keep the button just makes an image (like the top Run button), so call it
  // Run there; in Pause it commits your edit, so it stays Continue.
  els.btnContinue.textContent = keep ? "▶ Run" : "▶ Continue";
  els.btnContinue.title = keep
    ? "Make a new image with this text (same as pressing Run)"
    : "Run only the rest of the workflow with your edited text";

  els.count.textContent = countLabel(s.text);
  els.band.textContent = statusText(node);
  // Classic paints the status on the canvas from statusText(node), so nudge a
  // repaint whenever the state changes (harmless in Nodes 2.0).
  node.setDirtyCanvas?.(true, false);
}
