// Outpaint Stitch Reaper - shared bits for the slider face + color settings.
//
// The node has two native INT widgets (feather, color_match) that hold the VALUE.
// The custom sliders read and write their `.value`, so the widgets stay the value
// store. BUT the natives are HIDDEN (sliders.mjs `hideNativeWidget` sets
// `hidden` + `canvasOnly`) so the pretty slider replaces their face AND so a real
// input dot can sit on each slider row - which means the value NO LONGER reaches
// Python by itself. Two load-bearing pieces make it work, do NOT remove them in a
// refactor: (1) sliders.mjs `hideNativeWidget` hides the natives (+ flags them
// `redSweepable` so XY Plot can still sweep them); (2) index.js installs an
// `app.graphToPrompt` hook that injects each slider's `.value` into
// `entry.inputs` when the input is unwired (and defers to a queue-driver sweep).
// This file only adds the accent-color plumbing.

import { app } from "/scripts/app.js";
import { globalAccent } from "../shared/node_settings.mjs";
import { BRAND } from "../shared/utils.mjs";

export const CLASS = "ReaperOutpaintStitch";
export { BRAND };
export const ACCENT_SETTING = "Reaper.OutpaintStitch.AccentColor";
export const ACCENT_PROP = "outpaintStitchAccent";

// The color the sliders paint with: this node's own choice, else the user's
// global default, else the Reaper orange. Nobody is forced into the brand
// (node UI convention: users recolor nodes, so no fixed accent).
export function accentOf(node) {
  const own = node?.properties?.[ACCENT_PROP];
  if (own && typeof own === "string" && own.trim()) return own.trim();
  try {
    const v = app.ui?.settings?.getSettingValue?.(ACCENT_SETTING);
    if (typeof v === "string" && v.trim()) return v.trim();
  } catch {}
  return globalAccent() || BRAND;   // then the master Reaper default
}

// Written ONLY when the user actually picks a color (never on the load path),
// so a clean saved workflow never opens "modified" from an added property key
// (Vue Compat #18). Clearing (falsy) removes the key -> follow the global default.
export function setAccent(node, hex) {
  if (!node.properties) node.properties = {};
  if (hex) node.properties[ACCENT_PROP] = hex;
  else delete node.properties[ACCENT_PROP];
}

// The native INT widget behind a slider name (feather / color_match).
export function widgetOf(node, name) {
  return node.widgets?.find((w) => w.name === name) || null;
}
