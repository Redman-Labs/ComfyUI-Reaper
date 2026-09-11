// Shared signal for live switching between classic and Nodes 2.0 renderers.
const listeners = new Set();
let timer = null;
let last = null;

function currentMode() {
  return !!globalThis.LiteGraph?.vueNodesMode;
}

function tick() {
  const current = currentMode();
  if (current === last) return;
  last = current;
  for (const callback of [...listeners]) {
    try {
      callback(current);
    } catch (error) {
      console.warn("[Reaper] renderer-change handler failed", error);
    }
  }
}

export function onRendererChange(callback) {
  if (typeof callback !== "function") return () => {};
  listeners.add(callback);
  if (timer == null) {
    last = currentMode();
    timer = setInterval(tick, 300);
  }
  return () => {
    listeners.delete(callback);
    if (!listeners.size && timer != null) {
      clearInterval(timer);
      timer = null;
      last = null;
    }
  };
}
