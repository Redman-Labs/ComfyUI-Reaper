// Prompt Progress Bar for ComfyUI-Reaper.
// Adapted from rgthree-comfy's Prompt Progress Bar under the MIT License.
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const INSTANCE_KEY = "__reaperPromptProgressBarInstance";
const IDS = {
  enabled: "Reaper.PromptProgressBar.Enabled",
  position: "Reaper.PromptProgressBar.Position",
  height: "Reaper.PromptProgressBar.Height",
  nodeColor: "Reaper.PromptProgressBar.NodeColor",
  stepColor: "Reaper.PromptProgressBar.StepColor",
};
const DEFAULTS = {
  [IDS.enabled]: true,
  [IDS.position]: "Top",
  [IDS.height]: 14,
  [IDS.nodeColor]: "#008000",
  [IDS.stepColor]: "#f66744",
};

globalThis[INSTANCE_KEY]?.dispose?.();

let bar = null;
let currentPromptId = null;
let queueRemaining = 0;
let disposed = false;
const prompts = new Map();
const listeners = [];

function setting(id) {
  try {
    const value = app.extensionManager?.setting?.get?.(id);
    if (value !== undefined) return value;
  } catch {}
  try {
    const value = app.ui?.settings?.getSettingValue?.(id);
    if (value !== undefined) return value;
  } catch {}
  return DEFAULTS[id];
}

function clampHeight(value) {
  const height = Math.round(Number(value));
  return Number.isFinite(height) ? Math.max(4, Math.min(100, height)) : DEFAULTS[IDS.height];
}

function cssColor(value, fallback) {
  let color = value;
  if (color && typeof color === "object") {
    color = color.hex ?? color.color ?? color.value;
  }
  color = typeof color === "string" ? color.trim() : "";
  // ComfyUI's color setting persists picker values without the leading '#'.
  if (/^[0-9a-f]{3,8}$/i.test(color)) color = `#${color}`;
  return color && globalThis.CSS?.supports?.("color", color) ? color : fallback;
}

function promptState(id) {
  const key = String(id ?? "unknown");
  let state = prompts.get(key);
  if (!state) {
    state = { id: key, nodes: null, total: 0, completed: new Set(), current: null, step: 0, max: 0, error: null };
    prompts.set(key, state);
  }
  return state;
}

function eventDetail(event) {
  return event?.detail ?? event ?? {};
}

function nodeLabel(state, nodeId) {
  const key = String(nodeId ?? "");
  const apiNode = state?.nodes?.[key];
  if (apiNode?._meta?.title) return apiNode._meta.title;
  if (apiNode?.class_type) return apiNode.class_type;
  const graphNode = app.graph?.getNodeById?.(Number(key));
  return graphNode?.title || graphNode?.type || key;
}

function ensureBar() {
  if (bar?.isConnected) return bar;
  document.querySelectorAll(".reaper-prompt-progress-bar").forEach((element) => element.remove());
  bar = document.createElement("div");
  bar.className = "reaper-prompt-progress-bar";
  bar.title = "Prompt progress. Click to center the currently executing node.";
  const nodes = document.createElement("div");
  nodes.className = "reaper-prompt-progress-nodes";
  const steps = document.createElement("div");
  steps.className = "reaper-prompt-progress-steps";
  const overlay = document.createElement("div");
  overlay.className = "reaper-prompt-progress-overlay";
  const text = document.createElement("span");
  text.className = "reaper-prompt-progress-text";
  text.textContent = "Idle";
  bar.append(nodes, steps, overlay, text);
  bar.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const state = currentPromptId != null ? prompts.get(String(currentPromptId)) : null;
    const node = state?.current != null ? app.graph?.getNodeById?.(Number(state.current)) : null;
    if (node) app.canvas?.centerOnNode?.(node);
  });
  const position = String(setting(IDS.position)).toLowerCase() === "bottom" ? "bottom" : "top";
  bar.dataset.position = position;
  placeBar(bar, position);
  return bar;
}

function placeBar(element, position) {
  // Current ComfyUI exposes dedicated grid rows above and below the main UI.
  // Appending there makes the bar consume layout space instead of covering the
  // workflow canvas, toolbar, tabs, or floating canvas controls.
  const host = document.querySelector(
    position === "bottom" ? ".comfyui-body-bottom" : ".comfyui-body-top"
  );
  if (host) {
    element.dataset.layout = "comfy-grid";
    if (element.parentElement !== host) host.appendChild(element);
    return;
  }

  // Compatibility fallback for older ComfyUI frontends without grid hosts.
  element.dataset.layout = "viewport";
  if (element.parentElement !== document.body) document.body.appendChild(element);
}

function injectStyle() {
  if (document.getElementById("reaper-prompt-progress-style")) return;
  const style = document.createElement("style");
  style.id = "reaper-prompt-progress-style";
  style.textContent = `
    .reaper-prompt-progress-bar{display:block;position:relative;left:0;width:100%;flex:0 0 auto;z-index:999;overflow:hidden;box-sizing:border-box;background:rgba(23,23,23,.92);color:#fff;font-family:system-ui,sans-serif;cursor:pointer;isolation:isolate}
    .reaper-prompt-progress-bar[data-layout="viewport"]{position:fixed;z-index:100000}
    .reaper-prompt-progress-bar[data-layout="viewport"][data-position="top"]{top:0;bottom:auto}.reaper-prompt-progress-bar[data-layout="viewport"][data-position="bottom"]{top:auto;bottom:0}
    .reaper-prompt-progress-nodes,.reaper-prompt-progress-steps{position:absolute;left:0;width:0;transition:width 50ms ease-in-out;pointer-events:none}
    .reaper-prompt-progress-nodes{top:0;height:50%;background:var(--reaper-prompt-node-color,#008000)}.reaper-prompt-progress-steps{top:50%;height:50%;background:var(--reaper-prompt-step-color,#f66744)}
    .reaper-prompt-progress-bar[data-error="true"] .reaper-prompt-progress-nodes,.reaper-prompt-progress-bar[data-error="true"] .reaper-prompt-progress-steps{height:100%;top:0;background:#800000}
    .reaper-prompt-progress-overlay{position:absolute;inset:0;z-index:2;background:linear-gradient(to bottom,rgba(255,255,255,.25),rgba(0,0,0,.25));mix-blend-mode:overlay;pointer-events:none}
    .reaper-prompt-progress-text{position:relative;z-index:3;display:flex;align-items:center;height:100%;padding:0 6px;box-sizing:border-box;white-space:nowrap;text-shadow:0 0 2px #000;pointer-events:none}
  `;
  document.head.appendChild(style);
}

function configure() {
  if (disposed) return;
  if (!setting(IDS.enabled)) {
    bar?.remove();
    return;
  }
  injectStyle();
  const element = ensureBar();
  const height = clampHeight(setting(IDS.height));
  const position = String(setting(IDS.position)).toLowerCase() === "bottom" ? "bottom" : "top";
  element.dataset.position = position;
  placeBar(element, position);
  element.style.height = `${height}px`;
  element.style.setProperty("--reaper-prompt-node-color", cssColor(setting(IDS.nodeColor), DEFAULTS[IDS.nodeColor]));
  element.style.setProperty("--reaper-prompt-step-color", cssColor(setting(IDS.stepColor), DEFAULTS[IDS.stepColor]));
  const fontSize = Math.max(8, Math.min(18, height - 4));
  element.style.fontSize = `${fontSize}px`;
  render();
}

function render() {
  if (!setting(IDS.enabled)) return;
  const element = ensureBar();
  const nodesEl = element.querySelector(".reaper-prompt-progress-nodes");
  const stepsEl = element.querySelector(".reaper-prompt-progress-steps");
  const textEl = element.querySelector(".reaper-prompt-progress-text");
  const state = currentPromptId != null ? prompts.get(String(currentPromptId)) : null;
  element.dataset.error = state?.error ? "true" : "false";
  if (state?.error) {
    nodesEl.style.width = "100%";
    stepsEl.style.width = "100%";
    textEl.textContent = `${state.error.exception_type || "Execution error"}${state.error.node_id ? ` — ${nodeLabel(state, state.error.node_id)}` : ""}`;
    return;
  }
  if (state?.current != null) {
    const completed = state.completed.size;
    const nodePercent = state.total ? Math.min(100, (completed / state.total) * 100) : 0;
    const stepPercent = state.max > 0 ? Math.min(100, (state.step / state.max) * 100) : 0;
    nodesEl.style.width = `${state.total ? Math.max(2, nodePercent) : 0}%`;
    stepsEl.style.width = `${stepPercent}%`;
    const queue = queueRemaining ? `(${queueRemaining}) ` : "";
    const nodeProgress = state.total ? `${Math.round(nodePercent)}%` : "??%";
    const stepProgress = state.max > 0 ? ` (${Math.round(stepPercent)}%)` : "";
    textEl.textContent = `${queue}${nodeProgress} — ${nodeLabel(state, state.current)}${stepProgress}`;
    return;
  }
  nodesEl.style.width = "0%";
  stepsEl.style.width = "0%";
  textEl.textContent = queueRemaining ? `(${queueRemaining}) Running in another tab` : "Idle";
}

function listen(type, handler) {
  api.addEventListener(type, handler);
  listeners.push([type, handler]);
}

const originalQueuePrompt = api.queuePrompt;
api.queuePrompt = async function (...args) {
  const response = await originalQueuePrompt.apply(this, args);
  const prompt = args[1] || args[0];
  const output = prompt?.output || prompt?.prompt?.output || null;
  const state = promptState(response?.prompt_id);
  state.nodes = output;
  state.total = output ? Object.keys(output).length : 0;
  state.completed.clear();
  state.error = null;
  return response;
};

listen("status", (event) => {
  const detail = eventDetail(event);
  queueRemaining = Number(detail?.exec_info?.queue_remaining) || 0;
  render();
});
listen("execution_start", (event) => {
  const detail = eventDetail(event);
  currentPromptId = String(detail?.prompt_id ?? detail ?? "unknown");
  const state = promptState(currentPromptId);
  state.completed.clear();
  state.current = null;
  state.error = null;
  render();
});
listen("executing", (event) => {
  const detail = eventDetail(event);
  const state = promptState(detail?.prompt_id ?? currentPromptId);
  const nodeId = detail && typeof detail === "object" ? (detail.node ?? detail.node_id) : detail;
  if (state.current != null && nodeId !== state.current) state.completed.add(String(state.current));
  state.current = nodeId == null ? null : String(nodeId);
  state.step = 0;
  state.max = 0;
  if (nodeId == null) currentPromptId = null;
  render();
});
listen("progress", (event) => {
  const detail = eventDetail(event);
  const state = promptState(detail?.prompt_id ?? currentPromptId);
  if (detail?.node != null) state.current = String(detail.node);
  state.step = Number(detail?.value) || 0;
  state.max = Number(detail?.max) || 0;
  render();
});
listen("execution_cached", (event) => {
  const detail = eventDetail(event);
  const state = promptState(detail?.prompt_id ?? currentPromptId);
  for (const id of detail?.nodes || []) state.completed.add(String(id));
  render();
});
listen("execution_error", (event) => {
  const detail = eventDetail(event);
  const state = promptState(detail?.prompt_id ?? currentPromptId);
  state.error = detail;
  currentPromptId = state.id;
  render();
});
for (const type of ["execution_success", "execution_interrupted"]) {
  listen(type, () => {
    currentPromptId = null;
    render();
  });
}

function dispose() {
  disposed = true;
  for (const [type, handler] of listeners) api.removeEventListener(type, handler);
  if (api.queuePrompt === instance.queuePromptWrapper) api.queuePrompt = originalQueuePrompt;
  bar?.remove();
}

const instance = { dispose, queuePromptWrapper: api.queuePrompt };
globalThis[INSTANCE_KEY] = instance;

const refresh = () => setTimeout(configure, 0);
app.registerExtension({
  name: "Reaper.PromptProgressBar",
  settings: [
    // ComfyUI currently prepends extension settings within a category, so these
    // are registered bottom-to-top to produce the intended visible order.
    { id: IDS.stepColor, name: "Step Progress Bar Color", type: "color", defaultValue: DEFAULTS[IDS.stepColor], category: ["Reaper", "Prompt Progress Bar", "step color"], tooltip: "Color used for progress within the currently executing node, such as sampler steps.", onChange: refresh },
    { id: IDS.nodeColor, name: "Node Progress Bar Color", type: "color", defaultValue: DEFAULTS[IDS.nodeColor], category: ["Reaper", "Prompt Progress Bar", "node color"], tooltip: "Color used for overall workflow node progress.", onChange: refresh },
    { id: IDS.height, name: "Height", type: "slider", defaultValue: DEFAULTS[IDS.height], attrs: { min: 4, max: 100, step: 1 }, category: ["Reaper", "Prompt Progress Bar", "height"], tooltip: "Prompt Progress Bar height in whole pixels (4–100). Use the slider or the integer box on its right.", onChange: refresh },
    { id: IDS.position, name: "Position", type: "combo", defaultValue: DEFAULTS[IDS.position], options: ["Top", "Bottom"], category: ["Reaper", "Prompt Progress Bar", "position"], tooltip: "Place the Prompt Progress Bar at the top or bottom of the window.", onChange: refresh },
    { id: IDS.enabled, name: "Enable Prompt Progress Bar", type: "boolean", defaultValue: DEFAULTS[IDS.enabled], category: ["Reaper", "Prompt Progress Bar", "enabled"], tooltip: "Show prompt, node, sampler-step, and queue progress at the edge of the ComfyUI window.", onChange: refresh },
  ],
  setup: configure,
});

window.addEventListener("beforeunload", dispose, { once: true });
