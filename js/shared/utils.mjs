export const DEFAULT_BRAND = "#f66744";
export const BRAND_SETTING = "Reaper.DefaultStyle";
export const BRAND_CSS = `var(--reaper-brand, ${DEFAULT_BRAND})`;

export let BRAND = DEFAULT_BRAND;

export function setBrandColor(value) {
  const color = typeof value === "string" && value.trim() ? value.trim() : DEFAULT_BRAND;
  BRAND = color;
  document.documentElement?.style?.setProperty("--reaper-brand", color);
}

export function hideJsonWidget(widgets, widgetName) {
  const widget = (widgets || []).find((candidate) => candidate.name === widgetName);
  if (!widget) return widget;
  widget.hidden = true;
  widget.computeSize = () => [0, -4];
  if (!widget.options) widget.options = {};
  widget.options.canvasOnly = true;
  const hideElement = () => {
    const element = widget.element || widget.inputEl;
    if (element) element.style.display = "none";
  };
  hideElement();
  requestAnimationFrame(hideElement);
  return widget;
}

export function createDummyWidget(titleText, subtitleText, instructionText) {
  const container = document.createElement("div");
  container.style.cssText = `
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    gap:4px; padding:20px; background:#121212; border-radius:8px;
    width:100%; height:100%; color:#fff; font-family:sans-serif;
    text-align:center; box-sizing:border-box;
  `;

  const logo = document.createElement("img");
  logo.src = redAsset("reaper_logo.svg");
  logo.alt = "Reaper";
  logo.style.cssText = "width:45px;height:auto;margin-bottom:10px;";
  container.appendChild(logo);

  const title = document.createElement("div");
  title.textContent = titleText;
  title.style.cssText = "font-size:22px;font-weight:700;line-height:1.2;";
  container.appendChild(title);

  const subtitle = document.createElement("div");
  subtitle.textContent = subtitleText;
  subtitle.style.cssText = `font-size:20px;font-weight:700;color:${BRAND_CSS};line-height:1.2;`;
  container.appendChild(subtitle);

  const instruction = document.createElement("div");
  instruction.textContent = instructionText;
  instruction.style.cssText = "white-space:pre-line;color:#777;font-size:11px;margin-top:12px;line-height:1.4;";
  container.appendChild(instruction);
  return container;
}

export function installFocusTrap(overlay) {
  const trap = document.createElement("textarea");
  trap.dataset.reaperTrap = "1";
  trap.setAttribute("aria-hidden", "true");
  trap.style.cssText =
    "position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;z-index:-1;";
  overlay.appendChild(trap);
  trap.focus();
  const refocus = (event) => {
    const target = event.target;
    const tag = target?.tagName;
    if (target?.isContentEditable || target?.closest?.('[contenteditable="true"]')) return;
    if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
      requestAnimationFrame(() => trap.focus());
    }
  };
  overlay.addEventListener("mouseup", refocus);
  return trap;
}

export async function downloadDataURL(dataURL, suggestedName = "reaper_export.png") {
  if (!dataURL) return;
  const mimeMatch = dataURL.match(/^data:([^;]+);/);
  const mime = mimeMatch ? mimeMatch[1] : "image/png";
  const ext = mime === "image/jpeg" ? "jpg" : "png";
  const name = suggestedName.endsWith(`.${ext}`)
    ? suggestedName
    : `${suggestedName}.${ext}`;

  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: name,
        types: [{ description: "Image", accept: { [mime]: [`.${ext}`] } }],
      });
      const blob = await (await fetch(dataURL)).blob();
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    } catch (error) {
      if (error?.name === "AbortError") return;
      console.warn("[Reaper] showSaveFilePicker failed, falling back:", error);
    }
  }
  const anchor = document.createElement("a");
  anchor.href = dataURL;
  anchor.download = name;
  anchor.click();
}
import { redAsset } from "./api_url.mjs";
