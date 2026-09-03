// Shared one-shot submission and execution-order state for Reaper pause
// gates. ComfyUI can place visually sequential gates on separate output
// branches, so graph ancestry alone is not always enough to identify a gate
// that the user has already completed.

let activeSubmission = null;
let reachedCounter = 0;
const reachedOrder = new Map();

function nodeKey(family, nodeId) {
  return `${family}:${String(nodeId)}`;
}

function tailId(value) {
  const id = String(value);
  return id.includes(":") ? id.slice(id.lastIndexOf(":") + 1) : id;
}

function promptIdMatchesNode(promptId, nodeId) {
  return String(promptId) === String(nodeId) || tailId(promptId) === String(nodeId);
}

function isLink(value) {
  return Array.isArray(value)
    && value.length === 2
    && (typeof value[0] === "string" || typeof value[0] === "number")
    && typeof value[1] === "number";
}

function findActivePromptId(output, nodeId) {
  for (const id of Object.keys(output || {})) {
    if (promptIdMatchesNode(id, nodeId)) return String(id);
  }
  return null;
}

function buildConsumers(output) {
  const consumers = new Map();
  for (const id of Object.keys(output || {})) {
    for (const value of Object.values(output[id]?.inputs || {})) {
      if (!isLink(value)) continue;
      const origin = String(value[0]);
      if (!consumers.has(origin)) consumers.set(origin, new Set());
      consumers.get(origin).add(String(id));
    }
  }
  return consumers;
}

function isUpstreamOf(consumers, startId, targetId) {
  const target = String(targetId);
  const seen = new Set();
  const stack = [String(startId)];
  while (stack.length) {
    const next = consumers.get(stack.pop());
    if (!next) continue;
    for (const id of next) {
      if (id === target) return true;
      if (!seen.has(id)) {
        seen.add(id);
        stack.push(id);
      }
    }
  }
  return false;
}

export function markPauseReached(node, family) {
  if (node?.id == null) return;
  reachedOrder.set(nodeKey(family, node.id), ++reachedCounter);
}

export function beginPauseSubmission(node, family, mode) {
  const submission = {
    nodeId: String(node?.id ?? ""),
    family,
    mode,
    token: Symbol("reaper-pause-submission"),
  };
  activeSubmission = submission;
  return submission;
}

export function endPauseSubmission(submission) {
  if (activeSubmission?.token === submission?.token) activeSubmission = null;
}

export function coordinatePauseMode(output, promptId, family, fallbackMode) {
  const active = activeSubmission;
  if (!active) return fallbackMode;
  if (promptIdMatchesNode(promptId, active.nodeId) && family === active.family) {
    return fallbackMode;
  }

  const targetId = findActivePromptId(output, active.nodeId);
  if (!targetId) return fallbackMode;

  const consumers = buildConsumers(output);
  if (isUpstreamOf(consumers, promptId, targetId)) return "continue";
  if (isUpstreamOf(consumers, targetId, promptId)) return fallbackMode;

  // Separate output branches have no ancestry relationship. In that case,
  // advance a gate only when it was reached before the currently clicked gate.
  const currentReached = reachedOrder.get(nodeKey(family, tailId(promptId)));
  const targetReached = reachedOrder.get(nodeKey(active.family, active.nodeId));
  if (currentReached && targetReached && currentReached < targetReached) {
    return "continue";
  }
  return fallbackMode;
}
