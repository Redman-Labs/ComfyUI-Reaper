const helpByClass = new Map();

export function registerNodeHelp(comfyClass, definition) {
  if (comfyClass && definition) helpByClass.set(comfyClass, definition);
}

export function getNodeHelp(comfyClass) {
  return helpByClass.get(comfyClass) ?? null;
}
