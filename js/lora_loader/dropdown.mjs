// LoRA Loader Reaper - the searchable LoRA picker popup (opened by clicking a
// row's name field). Type to filter; results are grouped by subfolder. Closes on
// outside pointer / wheel / Esc. Follows Load Image Reaper Pattern #14 (the wheel
// handler must skip events inside the popup or scrolling the list would close it).

import { BRAND } from "./core.mjs";
import { listLoras } from "./api.mjs";

let _pop = null;
let _cleanup = null;

function injectCSS() {
  if (document.getElementById("red-ll-dd-css")) return;
  const s = document.createElement("style");
  s.id = "red-ll-dd-css";
  s.textContent = `
    .red-ll-dd { position:fixed; z-index:10020; width:300px; max-width:92vw; background:#242424;
      border:1px solid ${BRAND}; border-radius:9px; box-shadow:0 14px 44px rgba(0,0,0,0.6);
      overflow:hidden; font:12px 'Segoe UI',system-ui,sans-serif; color:#ddd;
      display:flex; flex-direction:column; max-height:60vh; }
    .red-ll-dd-srch { margin:8px; display:flex; align-items:center; gap:7px; background:#161616;
      border:1px solid ${BRAND}; border-radius:6px; padding:6px 9px; }
    .red-ll-dd-srch input { flex:1; min-width:0; background:transparent; border:0; outline:none;
      color:#fff; font:12px monospace; }
    .red-ll-dd-srch .ic { color:#888; flex:none; }
    .red-ll-dd-crumb { display:flex; flex-wrap:wrap; align-items:center; gap:2px; padding:3px 12px 6px;
      font:10.5px 'Segoe UI',sans-serif; color:#8a8a8a; border-bottom:1px solid #1c1c1c; }
    .red-ll-dd-crumb .c { cursor:pointer; color:#a8a8a8; }
    .red-ll-dd-crumb .c:hover { color:${BRAND}; }
    .red-ll-dd-crumb .c.here { color:#e0e0e0; cursor:default; }
    .red-ll-dd-crumb .s { color:#555; }
    .red-ll-dd-list { overflow-y:auto; overflow-x:hidden; padding:2px 0 6px; }
    .red-ll-dd-list::-webkit-scrollbar { width:7px; }
    .red-ll-dd-list::-webkit-scrollbar-thumb { background:#555; border-radius:3px; }
    .red-ll-dd-grp { font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:#7a7a7a;
      padding:6px 12px 3px; }
    .red-ll-dd-opt { padding:6px 12px; font:11.5px monospace; color:#bbb; cursor:pointer;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .red-ll-dd-opt:hover { background:#2f2f2f; color:#fff; }
    .red-ll-dd-opt.cur { color:${BRAND}; }
    .red-ll-dd-opt .sub { color:#666; }
    .red-ll-dd-folder { display:flex; align-items:center; gap:8px; padding:7px 12px; cursor:pointer;
      font:11.5px 'Segoe UI',sans-serif; color:#d0d0d0; }
    .red-ll-dd-folder:hover { background:#2f2f2f; color:#fff; }
    .red-ll-dd-folder .fi { color:#e0b24a; flex:none; }
    .red-ll-dd-folder .nm { flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .red-ll-dd-folder .ct { color:#777; font:10px monospace; } .red-ll-dd-folder .ch { color:#777; }
    .red-ll-dd-back { padding:6px 12px; cursor:pointer; color:#9a9a9a; font:11px 'Segoe UI'; }
    .red-ll-dd-back:hover { color:${BRAND}; }
    .red-ll-dd-empty { padding:14px 12px; color:#777; text-align:center; }
  `;
  document.head.appendChild(s);
}

export function closeLoraDropdown() {
  if (_cleanup) { try { _cleanup(); } catch {} }
  _cleanup = null;
  if (_pop) { try { _pop.remove(); } catch {} }
  _pop = null;
}

// Slice the NORMALISED string, not the original. Windows hands us
// "wan2.2\4steps\file.safetensors", and returning "wan2.2\4steps" made a
// curPath that levelItems() could never match, because it compares against a
// slash-normalised name - so opening the picker on a LoRA two folders deep
// showed "Empty folder." and the user had to click back to the root and start
// again. ONE level worked by luck: there is no separator left inside "wan2.2".
// Reported 2026-08-11.
function group(name) {
  const norm = name.replace(/\\/g, "/");
  const i = norm.lastIndexOf("/");
  return i < 0 ? "" : norm.slice(0, i);
}
function base(name) {
  const i = name.replace(/\\/g, "/").lastIndexOf("/");
  return i < 0 ? name : name.slice(i + 1);
}

export async function openLoraDropdown(anchorEl, opts) {
  closeLoraDropdown();
  injectCSS();
  const { current = "", accent = BRAND, onPick } = opts || {};

  const pop = document.createElement("div");
  pop.className = "red-ll-dd";
  pop.style.borderColor = accent;

  const srch = document.createElement("div");
  srch.className = "red-ll-dd-srch";
  srch.style.borderColor = accent;
  const ic = document.createElement("span"); ic.className = "ic"; ic.textContent = "⌕";
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Search LoRAs…";
  input.addEventListener("keydown", (e) => e.stopPropagation()); // don't trigger canvas shortcuts
  srch.append(ic, input);

  const crumb = document.createElement("div");
  crumb.className = "red-ll-dd-crumb";
  const list = document.createElement("div");
  list.className = "red-ll-dd-list";
  pop.append(srch, crumb, list);
  document.body.appendChild(pop);
  _pop = pop; // set BEFORE the await so a mid-fetch reopen closes THIS popup, not nothing

  const r = anchorEl.getBoundingClientRect();
  pop.style.width = Math.min(Math.max(r.width, 240), 360) + "px";
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pop.offsetWidth - 8)) + "px";

  // Placed below the anchor by default; flipped above if there isn't room. Recomputed
  // once the list has content (its real height is known then).
  function place() {
    const h = pop.offsetHeight;
    if (r.bottom + 4 + h <= window.innerHeight - 8) pop.style.top = (r.bottom + 4) + "px";
    else pop.style.top = Math.max(8, r.top - 4 - h) + "px";
  }
  place();

  // Force-fetch on EVERY open: the list is tiny, the server re-validates against
  // disk each request, and serving the session cache here is exactly the reported
  // bug (rename a file, press R, picker still shows the old name until a full
  // restart). Freshness on open also covers users who never press R at all.
  const all = await listLoras(true);
  if (!pop.isConnected) return; // closed while loading

  // Folder navigation: `curPath` is the folder we're browsing ("" = root). Typing
  // in the search box overrides nav and searches EVERY LoRA (flat), so the user can
  // still find anything without drilling. Start inside the current LoRA's folder.
  let curPath = current ? group(current) : "";

  function levelItems() {
    const prefix = curPath ? curPath + "/" : "";
    const folders = new Map();
    const files = [];
    for (const name of all) {
      const norm = name.replace(/\\/g, "/");
      if (curPath && !norm.startsWith(prefix)) continue;
      const rest = norm.slice(prefix.length);
      const slash = rest.indexOf("/");
      if (slash < 0) files.push(name);
      else { const f = rest.slice(0, slash); folders.set(f, (folders.get(f) || 0) + 1); }
    }
    return { folders: [...folders.entries()].sort((a, b) => a[0].localeCompare(b[0])), files };
  }

  function fileRow(name, showSub) {
    const opt = document.createElement("div");
    opt.className = "red-ll-dd-opt" + (name === current ? " cur" : "");
    opt.title = name;
    opt.appendChild(document.createTextNode(base(name)));
    if (showSub) {
      const g = group(name);
      if (g) { const s = document.createElement("span"); s.className = "sub"; s.textContent = " · " + g; opt.appendChild(s); }
    }
    opt.addEventListener("click", () => { onPick?.(name); closeLoraDropdown(); });
    return opt;
  }

  function folderRow(f, count) {
    const row = document.createElement("div");
    row.className = "red-ll-dd-folder";
    const fi = document.createElement("span"); fi.className = "fi"; fi.textContent = "📁";
    const nm = document.createElement("span"); nm.className = "nm"; nm.textContent = f;
    const ct = document.createElement("span"); ct.className = "ct"; ct.textContent = String(count);
    const ch = document.createElement("span"); ch.className = "ch"; ch.textContent = "›";
    row.append(fi, nm, ct, ch);
    row.addEventListener("click", () => { curPath = curPath ? curPath + "/" + f : f; input.value = ""; renderList(); });
    return row;
  }

  function crumbLink(label, path, here) {
    const c = document.createElement("span");
    c.className = "c" + (here ? " here" : "");
    c.textContent = label;
    if (!here) c.addEventListener("click", () => { curPath = path; input.value = ""; renderList(); });
    return c;
  }

  function renderCrumb() {
    crumb.innerHTML = "";
    if (input.value.trim()) { crumb.style.display = "none"; return; }
    crumb.style.display = "";
    const parts = curPath ? curPath.split("/") : [];
    crumb.appendChild(crumbLink("All", "", parts.length === 0));
    let acc = "";
    parts.forEach((p, i) => {
      const s = document.createElement("span"); s.className = "s"; s.textContent = "›"; crumb.appendChild(s);
      acc = acc ? acc + "/" + p : p;
      crumb.appendChild(crumbLink(p, acc, i === parts.length - 1));
    });
  }

  function emptyRow(text) {
    const e = document.createElement("div");
    e.className = "red-ll-dd-empty";
    e.textContent = text;
    list.appendChild(e);
  }

  function renderList() {
    renderCrumb();
    list.innerHTML = "";
    const q = input.value.trim().toLowerCase();
    if (q) {
      const matched = all.filter((n) => n.toLowerCase().includes(q));
      if (!matched.length) { emptyRow(all.length ? "No match." : "No LoRAs in models/loras."); return; }
      for (const name of matched) list.appendChild(fileRow(name, true));
      return;
    }
    const { folders, files } = levelItems();
    if (curPath) {
      const back = document.createElement("div");
      back.className = "red-ll-dd-back";
      back.textContent = "‹ back";
      back.addEventListener("click", () => {
        const i = curPath.lastIndexOf("/");
        curPath = i < 0 ? "" : curPath.slice(0, i);
        renderList();
      });
      list.appendChild(back);
    }
    for (const [f, count] of folders) list.appendChild(folderRow(f, count));
    for (const name of files) list.appendChild(fileRow(name, false));
    if (!folders.length && !files.length) emptyRow(all.length ? "Empty folder." : "No LoRAs in models/loras.");
  }
  renderList();
  place(); // list now has height - re-anchor (flip up if needed)
  input.addEventListener("input", renderList);
  setTimeout(() => input.focus(), 0);

  const onDown = (e) => { if (!pop.contains(e.target)) closeLoraDropdown(); };
  const onWheel = (e) => { if (!pop.contains(e.target)) closeLoraDropdown(); };
  const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); closeLoraDropdown(); } };
  setTimeout(() => {
    if (_pop !== pop) return; // closed in the same tick - don't attach orphan listeners
    document.addEventListener("pointerdown", onDown, true);
    document.addEventListener("wheel", onWheel, true);
    document.addEventListener("keydown", onKey, true);
  }, 0);
  _cleanup = () => {
    document.removeEventListener("pointerdown", onDown, true);
    document.removeEventListener("wheel", onWheel, true);
    document.removeEventListener("keydown", onKey, true);
  };
  // (_pop was already set right after append, so the "closed mid-fetch" guard works.)
}
