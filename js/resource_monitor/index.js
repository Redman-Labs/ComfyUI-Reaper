import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

const INSTANCE_KEY = "__reaperResourceMonitorInstance";

// ComfyUI may evaluate extension modules again while rebuilding its frontend.
// Dispose the previous module instance before creating another timer or widget.
globalThis[INSTANCE_KEY]?.dispose?.();

const IDS = {
  rate: "Reaper.ResourceMonitor.RefreshRate",
  width: "Reaper.ResourceMonitor.PixelWidth",
  height: "Reaper.ResourceMonitor.PixelHeight",
  cpu: "Reaper.ResourceMonitor.ShowCPU",
  ram: "Reaper.ResourceMonitor.ShowRAM",
  gpu: "Reaper.ResourceMonitor.ShowGPU",
  vram: "Reaper.ResourceMonitor.ShowVRAM",
  temp: "Reaper.ResourceMonitor.ShowTemperature",
  power: "Reaper.ResourceMonitor.ShowPower",
};

const defaults = { [IDS.rate]: .5, [IDS.width]: 72, [IDS.height]: 26,
  [IDS.cpu]: true, [IDS.ram]: true, [IDS.gpu]: true,
  [IDS.vram]: true, [IDS.temp]: true, [IDS.power]: true };

let root;
let timer;
let stopped = false;

function removeStaleRoots(keep = null) {
  document.querySelectorAll(".rl-resource-monitor").forEach((element) => {
    if (element !== keep) element.remove();
  });
}

function dispose() {
  stopped = true;
  clearTimeout(timer);
  removeStaleRoots();
  root = undefined;
}

const instance = { dispose };
globalThis[INSTANCE_KEY] = instance;

function setting(id) {
  try {
    const value = app.extensionManager?.setting?.get?.(id);
    if (value !== undefined) return value;
  } catch {}
  try {
    const value = app.ui?.settings?.getSettingValue?.(id);
    if (value !== undefined) return value;
  } catch {}
  return defaults[id];
}

function injectCSS() {
  if (document.getElementById("reaper-resource-monitor-css")) return;
  const style = document.createElement("style");
  style.id = "reaper-resource-monitor-css";
  style.textContent = `
    .rl-resource-monitor{display:flex;align-items:center;gap:4px;min-width:0;padding:0 4px;font:10px/1.1 'Segoe UI',sans-serif}
    .rl-resource-item{position:relative;display:flex;align-items:center;justify-content:space-between;gap:5px;width:var(--rl-monitor-width,72px);height:var(--rl-monitor-height,26px);padding:0 6px;overflow:hidden;box-sizing:border-box;border:1px solid var(--border-color,#444);border-radius:5px;background:var(--comfy-input-bg,#222);color:var(--input-text,#ddd)}
    .rl-resource-fill{position:absolute;inset:0 auto 0 0;width:0;opacity:1;transition:width .35s ease;background:var(--rl-meter,#f66744);pointer-events:none}
    .rl-resource-label,.rl-resource-value{position:relative;z-index:1;white-space:nowrap}.rl-resource-label{font-weight:600;color:#fff}.rl-resource-value{font-variant-numeric:tabular-nums;color:#fff}
    .rl-resource-error{width:auto;max-width:220px;color:#ff9f86}.rl-resource-monitor[data-disabled='true']{display:none}
    @media(max-width:900px){.rl-resource-item{width:62px;padding:0 4px}.rl-resource-label{font-size:9px}}
  `;
  document.head.appendChild(style);
}

function mount() {
  if (root?.isConnected) {
    removeStaleRoots(root);
    return true;
  }
  const existing = document.querySelector(".rl-resource-monitor");
  if (existing) {
    root = existing;
    removeStaleRoots(root);
    return true;
  }
  root = document.createElement("div");
  root.className = "rl-resource-monitor";
  root.title = "Reaper Resource Monitor";
  const settings = app.menu?.settingsGroup?.element;
  if (settings?.parentElement) {
    settings.before(root);
    return true;
  }
  const queue = document.getElementById("queue-button");
  if (queue?.parentElement) {
    queue.insertAdjacentElement("afterend", root);
    return true;
  }
  const menu = document.querySelector(".comfyui-menu-right, .comfy-menu, header");
  if (menu) {
    menu.appendChild(root);
    return true;
  }
  root = undefined;
  return false;
}

function bytes(value) {
  if (!Number.isFinite(value) || value < 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = value;
  let unit = 0;
  while (n >= 1024 && unit < units.length - 1) { n /= 1024; unit++; }
  return `${n.toFixed(unit >= 3 ? 1 : 0)} ${units[unit]}`;
}

function metric(label, value, percent, color, title) {
  const item = document.createElement("div");
  item.className = "rl-resource-item";
  item.title = title || `${label}: ${value}`;
  item.style.setProperty("--rl-meter", color);
  const fill = document.createElement("span");
  fill.className = "rl-resource-fill";
  fill.style.width = `${Math.max(0, Math.min(100, Number(percent) || 0))}%`;
  const name = document.createElement("span");
  name.className = "rl-resource-label";
  name.textContent = label;
  const number = document.createElement("span");
  number.className = "rl-resource-value";
  number.textContent = value;
  item.append(fill, name, number);
  return item;
}

function render(data) {
  if (stopped || globalThis[INSTANCE_KEY] !== instance) return;
  if (!mount()) return;
  root.style.setProperty("--rl-monitor-width", `${Number(setting(IDS.width)) || 72}px`);
  root.style.setProperty("--rl-monitor-height", `${Number(setting(IDS.height)) || 26}px`);
  root.replaceChildren();
  if (!data?.available) {
    const error = document.createElement("div");
    error.className = "rl-resource-item rl-resource-error";
    error.textContent = data?.error || "Resource data unavailable";
    root.appendChild(error);
    return;
  }
  if (setting(IDS.cpu)) root.appendChild(metric("CPU", `${Math.round(data.cpu_percent)}%`, data.cpu_percent, "#0AA015"));
  if (setting(IDS.ram)) root.appendChild(metric("RAM", `${Math.round(data.ram_percent)}%`, data.ram_percent, "#b97f02", `${bytes(data.ram_used)} / ${bytes(data.ram_total)}`));
  for (const gpu of data.gpus || []) {
    const suffix = data.gpus.length > 1 ? gpu.index : "";
    if (setting(IDS.gpu)) root.appendChild(metric(`GPU${suffix}`, `${Math.round(gpu.utilization)}%`, gpu.utilization, "#0C86F4", gpu.name));
    if (setting(IDS.vram)) root.appendChild(metric(`VRAM${suffix}`, `${Math.round(gpu.vram_percent)}%`, gpu.vram_percent, "#8507de", `${gpu.name}: ${bytes(gpu.vram_used)} / ${bytes(gpu.vram_total)}`));
    if (setting(IDS.power) && Number.isFinite(gpu.power_watts)) {
      const powerLimit = Number.isFinite(gpu.power_limit_watts) ? gpu.power_limit_watts : null;
      root.appendChild(metric(
        `POWER${suffix}`,
        `${Math.round(gpu.power_watts)}W`,
        Number.isFinite(gpu.power_percent) ? gpu.power_percent : 0,
        "#e6b800",
        `${gpu.name}: ${gpu.power_watts.toFixed(1)} W${powerLimit ? ` / ${powerLimit.toFixed(0)} W limit` : ""}`,
      ));
    }
    if (setting(IDS.temp)) {
      const temperatureColor = gpu.temperature > 74 ? "#af0303" : "#04a208";
      root.appendChild(metric(
        `TEMP${suffix}`,
        `${Math.round(gpu.temperature)}°`,
        gpu.temperature,
        temperatureColor,
        `${gpu.name}: ${Math.round(gpu.temperature)} °C`,
      ));
    }
  }
}

async function update() {
  if (stopped || globalThis[INSTANCE_KEY] !== instance) return;
  const rate = Number(setting(IDS.rate));
  if (!(rate > 0)) {
    if (root) root.dataset.disabled = "true";
    return;
  }
  if (root) root.dataset.disabled = "false";
  try {
    const response = await api.fetchApi("/reaper/api/resources", { cache: "no-store" });
    const data = await response.json();
    if (stopped || globalThis[INSTANCE_KEY] !== instance) return;
    render(data);
  } catch (error) {
    render({ available: false, error: `Monitor unavailable: ${error.message}` });
  } finally {
    clearTimeout(timer);
    if (!stopped && Number(setting(IDS.rate)) > 0) timer = setTimeout(update, Math.max(250, rate * 1000));
  }
}

function restart() {
  if (globalThis[INSTANCE_KEY] !== instance) return;
  clearTimeout(timer);
  stopped = false;
  update();
}

function scheduleRestart() {
  setTimeout(restart, 0);
}

const configurationCategory = (item) => ["Reaper", "Resource Monitor - Configuration", item];
const hardwareCategory = (item) => ["Reaper", "Resource Monitor - Hardware", item];
const toggle = (id, name, tooltip, item) => ({ id, name, type: "boolean", defaultValue: true, category: hardwareCategory(item), tooltip, onChange: scheduleRestart });

const monitorSettings = [
  { id: IDS.width, name: "Pixel Width", type: "slider", defaultValue: 72,
    attrs: { min: 50, max: 120, step: 1 }, category: configurationCategory("width"),
    tooltip: "Width of each resource meter in the menu.", onChange: scheduleRestart },
  { id: IDS.height, name: "Pixel Height", type: "slider", defaultValue: 26,
    attrs: { min: 18, max: 50, step: 1 }, category: configurationCategory("height"),
    tooltip: "Height of each resource meter in the menu.", onChange: scheduleRestart },
  { id: IDS.rate, name: "Refresh per second", type: "slider", defaultValue: 1,
    attrs: { min: 0, max: 5, step: 0.25 }, category: configurationCategory("refresh"),
    tooltip: "Seconds between updates. Set to 0 to disable the monitor.", onChange: scheduleRestart },
  toggle(IDS.cpu, "CPU Usage", "Toggle total CPU utilization in the menu.", "cpu"),
  toggle(IDS.ram, "RAM Usage", "Toggle system memory utilization in the menu.", "ram"),
  toggle(IDS.gpu, "GPU Usage", "Toggle NVIDIA GPU utilization when NVML is available.", "gpu"),
  toggle(IDS.vram, "VRAM Usage", "Toggle NVIDIA GPU memory utilization.", "vram"),
  toggle(IDS.power, "GPU Power Usage", "Toggle NVIDIA GPU board power in watts.", "power"),
  toggle(IDS.temp, "GPU Temperature", "Toggle NVIDIA GPU temperature in Celsius.", "temperature"),
];

function registerSettings() {
  for (const definition of monitorSettings) {
    try { app.ui?.settings?.addSetting?.(definition); } catch (error) {
      console.debug("Reaper Resource Monitor setting already registered", definition.id, error);
    }
  }
}

app.registerExtension({
  name: "Reaper.ResourceMonitor",
  setup() {
    if (globalThis[INSTANCE_KEY] !== instance) return;
    injectCSS();
    registerSettings();
    removeStaleRoots(root?.isConnected ? root : null);
    let attempts = 0;
    const waitForMenu = () => {
      if (mount() || attempts++ > 40) restart();
      else setTimeout(waitForMenu, 250);
    };
    waitForMenu();
  },
});

window.addEventListener("beforeunload", dispose, { once: true });
