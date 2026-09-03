import { app } from "/scripts/app.js";
import {
  BRAND_SETTING,
  DEFAULT_BRAND,
  setBrandColor,
} from "../shared/utils.mjs";

function savedBrand(fallback = DEFAULT_BRAND) {
  try {
    const value = app.ui?.settings?.getSettingValue?.(BRAND_SETTING);
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

function applySavedBrand(fallback) {
  setBrandColor(savedBrand(fallback));
  app.graph?.setDirtyCanvas?.(true, true);
  app.canvas?.setDirty?.(true, true);
}

app.registerExtension({
  name: "Reaper.DefaultStyle",

  settings: [
    {
      id: BRAND_SETTING,
      name: "Default Style",
      type: "color",
      defaultValue: DEFAULT_BRAND,
      tooltip:
        "Default accent color used by Reaper node buttons, highlights, and canvas controls.",
      category: ["Reaper", "Default Style"],
      // ComfyUI writes the setting after onChange begins, so read it next tick.
      onChange: (value) => { setTimeout(() => applySavedBrand(value), 0); },
    },
  ],

  setup() {
    applySavedBrand();
  },
});
