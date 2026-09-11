// Reroute (Reaper) — adapted from rgthree-comfy's Reroute under the MIT License.
// This is a frontend-only virtual passthrough node. Its former context-menu
// controls are consolidated into one ComfyUI-styled settings dialog.
import { app } from "/scripts/app.js";

// Unique backend ID; ComfyUI displays the schema's display_name ("Reroute")
// in search and Node Manager without colliding with its built-in Reroute.
const TYPE = "ReaperReroute";
const TITLE = "Reroute";
const CATEGORY = "Reaper/Tools";
const SIDES = ["Top", "Right", "Bottom", "Left"];
const LAYOUTS = [
  ["Left", "Right"], ["Left", "Top"], ["Left", "Bottom"],
  ["Right", "Left"], ["Right", "Top"], ["Right", "Bottom"],
  ["Top", "Left"], ["Top", "Right"], ["Top", "Bottom"],
  ["Bottom", "Left"], ["Bottom", "Right"], ["Bottom", "Top"],
];
const ROTATIONS = [
  "Rotate 90° Clockwise",
  "Rotate 90° Counter-Clockwise",
  "Rotate 180°",
  "Flip Horizontally",
  "Flip Vertically",
];
const SIDE_DATA = {
  Left: [() => LiteGraph.LEFT, 0, 0.5],
  Right: [() => LiteGraph.RIGHT, 1, 0.5],
  Top: [() => LiteGraph.UP, 0.5, 0],
  Bottom: [() => LiteGraph.DOWN, 0.5, 1],
};
const MIN_SIZE = 10;
const DEFAULT_SIZE = [40, 30];
let activeDialog = null;

function defaultStyleColor() {
  let value;
  try { value = app.extensionManager?.setting?.get?.("Reaper.DefaultStyle"); } catch {}
  if (value == null) {
    try { value = app.ui?.settings?.getSettingValue?.("Reaper.DefaultStyle"); } catch {}
  }
  if (value && typeof value === "object") value = value.hex ?? value.color ?? value.value;
  value = typeof value === "string" ? value.trim() : "";
  if (/^[0-9a-f]{3,8}$/i.test(value)) value = `#${value}`;
  return value && globalThis.CSS?.supports?.("color", value) ? value : "#f66744";
}

function graphLink(graph, id) {
  if (!graph || id == null) return null;
  if (typeof graph.getLink === "function") return graph.getLink(id);
  const links = graph._links ?? graph.links;
  return links instanceof Map ? links.get(id) ?? null : links?.[id] ?? null;
}

function isReroute(node) {
  return node?.type === TYPE || node?.comfyClass === TYPE;
}

function markChanged(node) {
  node.graph?.setDirtyCanvas?.(true, true);
  app.canvas?.setDirty?.(true, true);
}

function setLayout(node, layout) {
  if (!Array.isArray(layout) || layout.length !== 2 || layout[0] === layout[1]) return;
  if (!SIDE_DATA[layout[0]] || !SIDE_DATA[layout[1]]) return;
  node.properties.connections_layout = [...layout];
  node.stabilize?.();
  markChanged(node);
}

function rotateSide(side, steps) {
  const index = SIDES.indexOf(side);
  return SIDES[((index + steps) % 4 + 4) % 4];
}

function applyTransform(node, operation) {
  const layout = [...(node.properties.connections_layout || ["Left", "Right"] )];
  let swapSize = false;
  if (operation === ROTATIONS[0]) {
    layout[0] = rotateSide(layout[0], 1);
    layout[1] = rotateSide(layout[1], 1);
    swapSize = true;
  } else if (operation === ROTATIONS[1]) {
    layout[0] = rotateSide(layout[0], -1);
    layout[1] = rotateSide(layout[1], -1);
    swapSize = true;
  } else if (operation === ROTATIONS[2]) {
    layout[0] = rotateSide(layout[0], 2);
    layout[1] = rotateSide(layout[1], 2);
  } else if (operation === ROTATIONS[3]) {
    layout[0] = ({ Left: "Right", Right: "Left" })[layout[0]] || layout[0];
    layout[1] = ({ Left: "Right", Right: "Left" })[layout[1]] || layout[1];
  } else if (operation === ROTATIONS[4]) {
    layout[0] = ({ Top: "Bottom", Bottom: "Top" })[layout[0]] || layout[0];
    layout[1] = ({ Top: "Bottom", Bottom: "Top" })[layout[1]] || layout[1];
  }
  node.properties.connections_layout = layout;
  if (swapSize) node.setSize([node.size[1], node.size[0]]);
  node.stabilize?.();
  markChanged(node);
}

function cloneReroute(node, where) {
  const graph = node.graph;
  if (!graph) return;
  const clone = node.clone();
  clone.pos = [node.pos[0] + (where === "Before" ? -20 : 20), node.pos[1] + (where === "Before" ? -20 : 20)];
  const inputLink = graphLink(graph, node.inputs?.[0]?.link);
  const outputLinks = (node.outputs?.[0]?.links || []).map((id) => graphLink(graph, id)).filter(Boolean);
  graph.add(clone);
  setTimeout(() => {
    if (where === "Before") {
      const source = inputLink && graph.getNodeById?.(inputLink.origin_id);
      source?.connect?.(inputLink.origin_slot, clone, 0);
      clone.connect?.(0, node, 0);
    } else {
      node.connect?.(0, clone, 0);
      for (const link of outputLinks) {
        const target = graph.getNodeById?.(link.target_id);
        clone.connect?.(0, target, link.target_slot);
      }
    }
    clone.scheduleStabilize?.(0);
    app.canvas?.selectNode?.(clone, false);
    markChanged(clone);
  }, 0);
}

function createToggle(label, checked, onChange) {
  const row = document.createElement("label");
  row.className = "reaper-reroute-toggle-row";
  const text = document.createElement("span");
  text.textContent = label;
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = checked;
  const track = document.createElement("span");
  track.className = "reaper-reroute-toggle";
  input.addEventListener("change", () => onChange(input.checked));
  row.append(text, input, track);
  return row;
}

function createNumber(label, value, onChange) {
  const wrap = document.createElement("label");
  wrap.className = "reaper-reroute-field reaper-reroute-number";
  const text = document.createElement("span");
  text.textContent = label;
  const input = document.createElement("input");
  input.type = "number";
  input.min = String(MIN_SIZE);
  input.max = "1000";
  input.step = "1";
  input.value = String(Math.round(value));
  input.addEventListener("change", () => {
    const number = Math.max(MIN_SIZE, Math.min(1000, Math.round(Number(input.value) || MIN_SIZE)));
    input.value = String(number);
    onChange(number);
  });
  wrap.append(text, input);
  return wrap;
}

function createSelect(label, values, selected, onChange, placeholder = null) {
  const wrap = document.createElement("label");
  wrap.className = "reaper-reroute-field";
  const text = document.createElement("span");
  text.textContent = label;
  const select = document.createElement("select");
  if (placeholder) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    option.selected = true;
    select.appendChild(option);
  }
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    option.selected = !placeholder && value === selected;
    select.appendChild(option);
  }
  select.addEventListener("change", () => {
    if (!select.value) return;
    onChange(select.value);
    if (placeholder) select.value = "";
  });
  wrap.append(text, select);
  return wrap;
}

function ensureDialogStyle() {
  if (document.getElementById("reaper-reroute-settings-style")) return;
  const style = document.createElement("style");
  style.id = "reaper-reroute-settings-style";
  style.textContent = `
    .reaper-reroute-backdrop{font-size:12px;position:fixed;inset:0;z-index:100000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.45);font-family:Inter,system-ui,sans-serif;color:var(--fg-color,#ddd)}
    .reaper-reroute-dialog{--reaper-reroute-accent:var(--reaper-brand,#f66744);width:min(400px,calc(100vw - 32px));background:var(--comfy-menu-bg,#202020);border:1px solid var(--border-color,#555);border-radius:10px;overflow:hidden;box-shadow:0 16px 48px rgba(0,0,0,.55)}
    .reaper-reroute-header{display:flex;align-items:center;gap:10px;padding:13px 16px;border-bottom:1px solid var(--border-color,#444);font-size:16px}.reaper-reroute-logo{color:var(--reaper-reroute-accent)}
    .reaper-reroute-header strong{flex:1;font-weight:500}.reaper-reroute-close{border:0;background:transparent;color:inherit;font-size:20px;cursor:pointer;opacity:.7}.reaper-reroute-close:hover{opacity:1}
    .reaper-reroute-content{display:flex;flex-direction:column;gap:12px;padding:16px}.reaper-reroute-size-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .reaper-reroute-field{display:flex;align-items:center;gap:12px}.reaper-reroute-field>span{min-width:128px;color:var(--input-text,#ccc)}.reaper-reroute-field select,.reaper-reroute-field input{flex:1;min-width:0;height:36px;padding:0 10px;font-size:12px;color:var(--input-text,#eee);background:var(--comfy-input-bg,#111);border:1px solid var(--border-color,#555);border-radius:6px;accent-color:var(--reaper-reroute-accent)}.reaper-reroute-field select:focus,.reaper-reroute-field input:focus{border-color:var(--reaper-reroute-accent);outline:1px solid var(--reaper-reroute-accent)}
    .reaper-reroute-number{position:relative}.reaper-reroute-number>span{min-width:auto}.reaper-reroute-number input{font-weight:600}
    .reaper-reroute-toggle-row{display:flex;align-items:center;position:relative;min-height:28px;cursor:pointer}.reaper-reroute-toggle-row>span:first-child{flex:1}.reaper-reroute-toggle-row input{position:absolute;opacity:0}.reaper-reroute-toggle{width:38px;height:22px;border-radius:12px;background:var(--input-surface,#444);transition:.15s;position:relative}.reaper-reroute-toggle:after{content:"";position:absolute;width:16px;height:16px;left:3px;top:3px;border-radius:50%;background:#fff;transition:.15s}.reaper-reroute-toggle-row input:checked+.reaper-reroute-toggle{background:var(--reaper-reroute-accent)}.reaper-reroute-toggle-row input:checked+.reaper-reroute-toggle:after{transform:translateX(16px)}
    .reaper-reroute-footer{display:flex;justify-content:flex-end;padding:12px 16px;border-top:1px solid var(--border-color,#444)}.reaper-reroute-done{padding:8px 16px;color:var(--p-primary-contrast-color,#FFF);background:var(--reaper-reroute-accent);border:0;border-radius:6px;cursor:pointer}
  `;
  document.head.appendChild(style);
}

function openSettings(node) {
  activeDialog?.close?.();
  ensureDialogStyle();
  const backdrop = document.createElement("div");
  backdrop.className = "reaper-reroute-backdrop";
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-modal", "true");
  backdrop.setAttribute("aria-label", "Reroute Settings");
  const dialog = document.createElement("div");
  dialog.className = "reaper-reroute-dialog";
  // Read the setting at open time rather than depending on extension load
  // order to have initialized the shared CSS variable already.
  dialog.style.setProperty("--reaper-reroute-accent", defaultStyleColor());
  const header = document.createElement("div");
  header.className = "reaper-reroute-header";
  header.innerHTML = '<span class="reaper-reroute-logo">⚙</span><strong>Reroute Settings</strong>';
  const closeButton = document.createElement("button");
  closeButton.className = "reaper-reroute-close";
  closeButton.type = "button";
  closeButton.setAttribute("aria-label", "Close");
  closeButton.textContent = "×";
  header.appendChild(closeButton);

  const content = document.createElement("div");
  content.className = "reaper-reroute-content";
  const sizes = document.createElement("div");
  sizes.className = "reaper-reroute-size-grid";
  sizes.append(
    createNumber("Static Width", node.size[0], (value) => node.setSize([value, node.size[1]])),
    createNumber("Static Height", node.size[1], (value) => node.setSize([node.size[0], value]))
  );
  content.append(
    sizes,
    createToggle("Show Label/Title", !!node.properties.showLabel, (value) => {
      node.properties.showLabel = value;
      markChanged(node);
    }),
    createToggle("Allow Resizing", node.resizable !== false, (value) => {
      node.setResizable(value);
      markChanged(node);
    }),
    createSelect(
      "Connection Layout",
      LAYOUTS.map((layout) => `${layout[0]} → ${layout[1]}`),
      (node.properties.connections_layout || ["Left", "Right"]).join(" → "),
      (value) => setLayout(node, value.split(" → "))
    ),
    createSelect("Rotate / Flip", ROTATIONS, "", (value) => applyTransform(node, value), "Choose an operation"),
    createSelect("Clone Reroute", ["Before", "After"], "", (value) => cloneReroute(node, value), "Choose a position")
  );

  const footer = document.createElement("div");
  footer.className = "reaper-reroute-footer";
  const done = document.createElement("button");
  done.className = "reaper-reroute-done";
  done.type = "button";
  done.textContent = "Done";
  footer.appendChild(done);
  dialog.append(header, content, footer);
  backdrop.appendChild(dialog);
  document.body.appendChild(backdrop);

  const close = () => {
    document.removeEventListener("keydown", onKey);
    backdrop.remove();
    if (activeDialog?.element === backdrop) activeDialog = null;
  };
  const onKey = (event) => { if (event.key === "Escape") close(); };
  closeButton.addEventListener("click", close);
  done.addEventListener("click", close);
  backdrop.addEventListener("pointerdown", (event) => { if (event.target === backdrop) close(); });
  document.addEventListener("keydown", onKey);
  activeDialog = { element: backdrop, node, close };
  closeButton.focus();
}

function registerNode() {
  if (LiteGraph.registered_node_types?.[TYPE]?.__reaperReroute) return;
  const LGraphNode = LiteGraph.LGraphNode;

  class Reroute extends LGraphNode {
    static __reaperReroute = true;
    static title = TITLE;
    static category = CATEGORY;
    static collapsable = false;
    static title_mode = LiteGraph.NO_TITLE;
    static layout_slot_offset = 5;

    constructor(title = TITLE) {
      super(title);
      this.comfyClass = TYPE;
      this.isVirtualNode = true;
      this.serialize_widgets = true;
      this.properties ||= {};
      this.properties.showLabel ??= false;
      this.properties.resizable ??= true;
      this.properties.connections_layout ||= ["Left", "Right"];
      this.color = "#2c2c2c";
      this.bgcolor ||= "#2a2a2a";
      this.addInput("", "*");
      this.addOutput("", "*");
      this.size = [...DEFAULT_SIZE];
      this.setResizable(this.properties.resizable);
    }

    configure(info) {
      if (info?.inputs?.length > 1) info.inputs.length = 1;
      if (info?.outputs?.length > 1) info.outputs.length = 1;
      super.configure(info);
      this.properties ||= {};
      this.properties.showLabel ??= false;
      this.properties.resizable ??= true;
      this.properties.connections_layout ||= ["Left", "Right"];
      this.setResizable(this.properties.resizable);
      const saved = this.properties.size || this.size || DEFAULT_SIZE;
      this.setSize(saved);
      this.scheduleStabilize(0);
    }

    clone() {
      const cloned = super.clone();
      cloned.properties = globalThis.structuredClone
        ? globalThis.structuredClone(this.properties)
        : JSON.parse(JSON.stringify(this.properties));
      if (cloned.inputs?.[0]) cloned.inputs[0].type = "*";
      if (cloned.outputs?.[0]) cloned.outputs[0].type = "*";
      return cloned;
    }

    setResizable(value) {
      this.resizable = !!value;
      this.properties.resizable = this.resizable;
    }

    // Current LiteGraph treats computeSize() as the minimum size during a
    // pointer resize. Its generic implementation returns the standard node
    // width (currently 140px), which is inappropriate for a compact reroute.
    computeSize(out = [0, 0]) {
      out[0] = MIN_SIZE;
      out[1] = MIN_SIZE;
      return out;
    }

    setSize(size) {
      const next = [
        Math.max(MIN_SIZE, Math.round(Number(size?.[0]) || DEFAULT_SIZE[0])),
        Math.max(MIN_SIZE, Math.round(Number(size?.[1]) || DEFAULT_SIZE[1])),
      ];
      super.setSize(next);
      this.properties ||= {};
      this.properties.size = [...this.size];
      markChanged(this);
    }

    getConnectionPos(isInput, slotNumber, out = new Float32Array(2)) {
      const side = (this.properties.connections_layout || ["Left", "Right"])[isInput ? 0 : 1];
      const data = SIDE_DATA[side] || SIDE_DATA[isInput ? "Left" : "Right"];
      const slot = (isInput ? this.inputs : this.outputs)?.[slotNumber];
      if (slot) {
        slot.dir = data[0]();
        slot.label = " ";
      }
      out[0] = this.pos[0] + this.size[0] * data[1];
      out[1] = this.pos[1] + this.size[1] * data[2];
      if (side === "Left") out[0] += this.constructor.layout_slot_offset;
      if (side === "Right") out[0] -= this.constructor.layout_slot_offset - 1;
      if (side === "Top") out[1] += this.constructor.layout_slot_offset;
      if (side === "Bottom") out[1] -= this.constructor.layout_slot_offset;
      return out;
    }

    getInputPos(slotNumber) { return this.getConnectionPos(true, slotNumber, [0, 0]); }
    getOutputPos(slotNumber) { return this.getConnectionPos(false, slotNumber, [0, 0]); }

    getInputLink() {
      return graphLink(this.graph, this.inputs?.[0]?.link);
    }

    onConnectionsChange() {
      this.scheduleStabilize();
    }

    scheduleStabilize(delay = 32) {
      clearTimeout(this._reaperStabilizeTimer);
      this._reaperStabilizeTimer = setTimeout(() => {
        this._reaperStabilizeTimer = null;
        if (this.graph) this.stabilize();
      }, delay);
    }

    stabilize() {
      if (!this.graph) return;
      let cursor = this;
      const seen = new Set();
      let sourceType = "*";
      while (cursor && !seen.has(cursor.id)) {
        seen.add(cursor.id);
        const link = graphLink(this.graph, cursor.inputs?.[0]?.link);
        if (!link) break;
        const source = this.graph.getNodeById?.(link.origin_id);
        if (!source) break;
        if (isReroute(source)) cursor = source;
        else {
          sourceType = source.outputs?.[link.origin_slot]?.type || link.type || "*";
          break;
        }
      }

      // A reroute can be wired from its output first. In that case adopt the
      // first concrete downstream input type until an upstream source arrives.
      if (sourceType === "*") {
        const downstream = [this];
        const downstreamSeen = new Set();
        while (downstream.length && sourceType === "*") {
          const node = downstream.shift();
          if (!node || downstreamSeen.has(node.id)) continue;
          downstreamSeen.add(node.id);
          for (const id of node.outputs?.[0]?.links || []) {
            const link = graphLink(this.graph, id);
            const target = link && this.graph.getNodeById?.(link.target_id);
            if (!target) continue;
            if (isReroute(target)) downstream.push(target);
            else sourceType = target.inputs?.[link.target_slot]?.type || link.type || "*";
            if (sourceType !== "*") break;
          }
        }
      }

      const queue = [this];
      const visited = new Set();
      while (queue.length) {
        const node = queue.shift();
        if (!node || visited.has(node.id)) continue;
        visited.add(node.id);
        if (node.inputs?.[0]) node.inputs[0].type = sourceType;
        if (node.outputs?.[0]) {
          node.outputs[0].type = sourceType;
          for (const id of [...(node.outputs[0].links || [])]) {
            const link = graphLink(this.graph, id);
            if (!link) continue;
            link.type = sourceType;
            const target = this.graph.getNodeById?.(link.target_id);
            if (isReroute(target)) queue.push(target);
          }
        }
      }
      markChanged(this);
    }

    onDrawForeground(ctx, canvas) {
      super.onDrawForeground?.(ctx, canvas);
      if (!this.properties.showLabel || canvas?.ds?.scale < 0.6 || this.size[0] <= 10) return;
      const fontSize = Math.min(12, Math.floor(this.size[1] * 0.65));
      ctx.save();
      ctx.fillStyle = "#aaa";
      ctx.font = `${fontSize}px Arial`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const label = this.title && this.title !== TITLE ? this.title : (this.outputs?.[0]?.type || "");
      ctx.fillText(String(label), this.size[0] / 2, this.size[1] / 2, Math.max(0, this.size[0] - 20));
      ctx.restore();
    }

    getExtraMenuOptions(canvas, options) {
      super.getExtraMenuOptions?.(canvas, options);
      options.unshift(null, {
        content: "Reroute Settings",
        callback: () => openSettings(this),
      });
    }

    onRemoved() {
      clearTimeout(this._reaperStabilizeTimer);
      if (activeDialog?.node === this) activeDialog.close();
      super.onRemoved?.();
    }
  }

  LiteGraph.registerNodeType(TYPE, Reroute);
  Reroute.category = CATEGORY;
}

app.registerExtension({
  name: "Reaper.Reroute",
  registerCustomNodes: registerNode,
});
