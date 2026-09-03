// ╔═══════════════════════════════════════════════════════════════╗
// ║  Reaper Shared — Label Editor CSS Injection                ║
// ╚═══════════════════════════════════════════════════════════════╝

let _labelCssInjected = false;
export function injectLabelCSS() {
  if (_labelCssInjected) return;
  _labelCssInjected = true;
  const style = document.createElement("style");
  style.textContent = `
.rl-lbl-body {
    max-height: 400px; overflow-y: auto; padding-right: 8px;
}
.rl-lbl-body::-webkit-scrollbar { width: 6px; }
.rl-lbl-body::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); border-radius: 10px; }
.rl-lbl-body::-webkit-scrollbar-thumb { background: #555; border-radius: 10px; }
.rl-lbl-body::-webkit-scrollbar-thumb:hover { background: #888; }
.rl-lbl-body { scrollbar-width: thin; scrollbar-color: #555 rgba(0,0,0,0.1); }
.rl-lbl-overlay {
    position: fixed; inset: 0; z-index: 99999; background: rgba(0,0,0,0.55);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Segoe UI', system-ui, sans-serif;
}
.rl-lbl-panel {
    background: #171718; border: 1px solid #333; border-radius: 10px;
    width: 660px; max-height: 90vh; overflow-y: auto;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6); position: relative;
}
.rl-lbl-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 18px; border-bottom: 1px solid #2a2a2a;
}
.rl-lbl-header span { color: #fff; font-size: 15px; font-weight: 600; }
.rl-lbl-close {
    background: none; border: none; color: #666; font-size: 20px;
    cursor: pointer; padding: 0 4px; line-height: 1;
}
.rl-lbl-close:hover { color: #fff; }
.rl-lbl-body { padding: 16px 18px; }
.rl-lbl-field { margin-bottom: 14px; }
.rl-lbl-field > .rl-lbl-lbl {
    display: block; color: #777; font-size: 10px; margin-bottom: 5px;
    text-transform: uppercase; letter-spacing: 0.6px;
}
.rl-lbl-field textarea {
    width: 100%; box-sizing: border-box; background: #222; border: 1px solid #333;
    border-radius: 5px; color: #ddd; padding: 8px 10px; font-size: 13px;
    font-family: inherit; outline: none; resize: vertical; min-height: 56px;
}
.rl-lbl-field textarea:focus { border-color: #f66744; }
.rl-lbl-preview {
    margin-bottom: 14px; background: #111; border-radius: 6px; padding: 12px;
    min-height: 36px; display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.rl-lbl-preview canvas { max-width: 100%; height: auto; }
.rl-lbl-btns { display: flex; gap: 4px; flex-wrap: wrap; }
.rl-lbl-btn {
    padding: 5px 12px; border: 1px solid #444; border-radius: 4px;
    background: #2a2c2e; color: #999; font-size: 12px; cursor: pointer; transition: all 0.15s;
}
.rl-lbl-btn:hover { border-color: #666; color: #ccc; }
.rl-lbl-btn.active { background: #f66744; border-color: #f66744; color: #fff; }
.rl-lbl-bold { font-weight: bold; min-width: 32px; text-align: center; }
.rl-lbl-range-wrap { display: flex; align-items: center; gap: 8px; }
.rl-lbl-range-wrap input[type="range"] { flex: 1; accent-color: #f66744; }
.rl-lbl-range-wrap .rl-lbl-val { color: #999; font-size: 12px; min-width: 32px; text-align: right; }
.rl-lbl-row { display: flex; gap: 12px; align-items: flex-end; }
.rl-lbl-row > .rl-lbl-field { flex: 1; margin-bottom: 0; }
.rl-lbl-swatches { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }
.rl-lbl-swatch {
    width: 24px; height: 24px; border-radius: 4px; cursor: pointer;
    border: 2px solid transparent; transition: border-color 0.15s; box-sizing: border-box;
}
.rl-lbl-swatch:hover { border-color: #888; }
.rl-lbl-swatch.active { border-color: #fff; }
.rl-lbl-swatch-transp {
    width: 24px; height: 24px; border-radius: 4px; cursor: pointer;
    border: 2px solid transparent; box-sizing: border-box;
    background: repeating-conic-gradient(#555 0% 25%, #333 0% 50%) 50%/10px 10px;
}
.rl-lbl-swatch-transp:hover { border-color: #888; }
.rl-lbl-swatch-transp.active { border-color: #fff; }
.rl-lbl-color-row { display: flex; align-items: center; gap: 6px; }
.rl-lbl-color-row input[type="color"] {
    width: 30px; height: 26px; padding: 0; border: 1px solid #444;
    border-radius: 4px; background: #222; cursor: pointer;
}
.rl-lbl-color-row .rl-lbl-hex {
    width: 76px; background: #222; border: 1px solid #333; border-radius: 4px;
    color: #ddd; padding: 4px 6px; font-size: 11px; font-family: monospace; outline: none;
}
.rl-lbl-color-row .rl-lbl-hex:focus { border-color: #f66744; }
.rl-lbl-footer {
    display: flex; justify-content: flex-end; gap: 8px;
    padding: 12px 18px; border-top: 1px solid #2a2a2a;
}
.rl-lbl-footer button {
    padding: 8px 20px; border: none; border-radius: 5px;
    font-size: 13px; cursor: pointer; font-weight: 500;
}
.rl-lbl-btn-cancel { background: #2a2a2a; color: #ccc; }
.rl-lbl-btn-cancel:hover { background: #363636; }
.rl-lbl-btn-save { background: #f66744; color: #fff; }
.rl-lbl-btn-save:hover { opacity: 0.9; }
.rl-lbl-align-icon { display: flex; flex-direction: column; gap: 2px; width: 14px; align-items: flex-start; }
.rl-lbl-align-icon span { display: block; height: 2px; background: currentColor; border-radius: 1px; }
.rl-lbl-align-left .rl-lbl-align-icon span:nth-child(1) { width: 14px; }
.rl-lbl-align-left .rl-lbl-align-icon span:nth-child(2) { width: 10px; }
.rl-lbl-align-left .rl-lbl-align-icon span:nth-child(3) { width: 12px; }
.rl-lbl-align-center .rl-lbl-align-icon { align-items: center; }
.rl-lbl-align-center .rl-lbl-align-icon span:nth-child(1) { width: 14px; }
.rl-lbl-align-center .rl-lbl-align-icon span:nth-child(2) { width: 10px; }
.rl-lbl-align-center .rl-lbl-align-icon span:nth-child(3) { width: 12px; }
.rl-lbl-align-right .rl-lbl-align-icon { align-items: flex-end; }
.rl-lbl-align-right .rl-lbl-align-icon span:nth-child(1) { width: 14px; }
.rl-lbl-align-right .rl-lbl-align-icon span:nth-child(2) { width: 10px; }
.rl-lbl-align-right .rl-lbl-align-icon span:nth-child(3) { width: 12px; }
.rl-lbl-help-overlay {
    position: absolute; inset: 0; background: #171718; border-radius: 10px;
    padding: 28px; overflow-y: auto; color: #ccc; font-size: 13px; line-height: 1.7; z-index: 10;
}
.rl-lbl-help-overlay h3 { color: #f66744; margin: 0 0 12px 0; font-size: 16px; }
.rl-lbl-help-overlay p { margin: 0 0 8px 0; }
.rl-lbl-help-overlay kbd {
    background: #333; border: 1px solid #555; border-radius: 3px;
    padding: 1px 5px; font-size: 11px; font-family: monospace; color: #ddd;
}
.rl-lbl-help-close {
    position: absolute; top: 12px; right: 16px;
    background: none; border: none; color: #666; font-size: 20px; cursor: pointer;
}
.rl-lbl-help-close:hover { color: #fff; }
.rl-lbl-btn-help { background: #2a2a2a; color: #999; font-size: 12px; padding: 8px 14px; }
.rl-lbl-btn-help:hover { background: #363636; color: #ccc; }
`;
  document.head.appendChild(style);
}
