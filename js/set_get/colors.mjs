// ╔═══════════════════════════════════════════════════════════════╗
// ║  SetNode (Reaper) / GetNode (Reaper) - Get mirrors its Set's color            ║
// ╚═══════════════════════════════════════════════════════════════╝
//
// You color a Set however you like (right-click -> Colors). A Get that reads
// that Set then takes the SAME color, so a matching pair is easy to spot, and
// the Get follows along if you recolor the Set later. The Get's dropdown also
// tags each name with that Set's color. Turn the setting off to leave Gets on
// their own color.

import { app } from "/scripts/app.js";
import { isGraphLoading } from "../shared/graph_loading.mjs";
import { GET_TYPE, allLiveGraphs, findSetterByName } from "./scope.mjs";

export const SETTING_ID = "Reaper.SetGet.ColorMatch";
export const BRAND_BODY = "#2a2a2a";
export const CATEGORY_TITLE_COLOR = "#2c2c2c";

export function isColorMatchOn() {
  const v = app.ui?.settings?.getSettingValue?.(SETTING_ID);
  return v == null ? true : !!v;
}

// The color a Get should show = the color of the Set it reads (whatever the
// user picked for that Set), or brand-dark when there is no Set in scope.
export function setColorFor(getNode) {
  const node = findSetterByName(getNode.graph, getNode.widgets?.[0]?.value)?.node;
  return {
    color: node?.color ?? CATEGORY_TITLE_COLOR,
    bgcolor: node?.bgcolor ?? BRAND_BODY,
  };
}

// Make a Get mirror its Set's color. Skipped during a load (the saved color
// is restored by configure) and when the setting is off, and it only writes on
// a real change so it never spams redraws or dirties a workflow.
export function inheritSetColor(getNode) {
  if (!getNode || !isColorMatchOn()) return;
  // A manually-colored Get (pinned via the color picker) opts out of mirroring so
  // its color isn't reverted every frame; "Reset colors" clears the flag.
  if (getNode.flags?.redSGManual) return;
  try {
    if (isGraphLoading()) return;
  } catch {
    /* ignore */
  }
  const { color, bgcolor } = setColorFor(getNode);
  if (getNode.color !== color || getNode.bgcolor !== bgcolor) {
    getNode.color = color;
    getNode.bgcolor = bgcolor;
    getNode.setDirtyCanvas?.(true, true);
  }
}

// Re-mirror every Get in the workflow (called when the setting is toggled).
export function recolorAllGets() {
  const graph = app.canvas?.graph || app.graph;
  for (const g of allLiveGraphs(graph)) {
    for (const n of g._nodes || []) {
      if (n.type === GET_TYPE) inheritSetColor(n);
    }
  }
  app.canvas?.setDirty(true, true);
}

// Exposed for the color picker (js/node_colors). A Get mirrors its Set's color
// every frame (inheritSetColor in onDrawForeground), so coloring a Get directly
// just flashes and reverts. The picker calls this to PIN the Get it colors: while
// pinned, inheritSetColor leaves it alone, so only the nodes the user selected get
// the color and it sticks. "Reset colors" clears the pin so the Get re-mirrors its
// Set. No-op on non-Get nodes. The flag lives on node.flags (serializes).
export function markManualColor(node, on) {
  if (!node || node.type !== GET_TYPE) return;
  node.flags = node.flags || {};
  if (on) node.flags.redSGManual = true;
  else delete node.flags.redSGManual;
}
try {
  window.ReaperSetGet = window.ReaperSetGet || {};
  window.ReaperSetGet.markManualColor = markManualColor;
} catch { /* ignore */ }
