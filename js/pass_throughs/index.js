import { app } from "/scripts/app.js";

const NODE_IDS = new Set([
  "ReaperAnyPasser",
  "ReaperAnyPasserPurge",
  "ReaperAudioPasser",
  "ReaperBooleanPasser",
  "ReaperClipPasser",
  "ReaperConditioningPasser",
  "ReaperControlNetPasser",
  "ReaperFloatPasser",
  "ReaperImagePasser",
  "ReaperIntPasser",
  "ReaperLatentPasser",
  "ReaperMaskPasser",
  "ReaperModelPasser",
  "ReaperStringPasser",
  "ReaperVAEPasser",
]);

const ANY_NODE_IDS = new Set(["ReaperAnyPasser", "ReaperAnyPasserPurge"]);
const TITLE_COLOR = "#a15b20";

function installAnyTypeMirroring(node) {
  const previousAdded = node.onAdded;
  const previousConnectionsChange = node.onConnectionsChange;

  node.onAdded = function () {
    previousAdded?.apply(this, arguments);
    if (this.inputs?.[0]) this.inputs[0].type = "*";
    if (this.outputs?.[0]) this.outputs[0].type = "*";
  };

  node.onConnectionsChange = function (side, slot, connected, link) {
    previousConnectionsChange?.apply(this, arguments);
    if (!link || slot !== 0) return;
    const input = this.inputs?.[0];
    const output = this.outputs?.[0];
    if (!input || !output) return;

    if (connected) {
      const type = side === LiteGraph.INPUT
        ? this.graph?.getNodeById(link.origin_id)?.outputs?.[link.origin_slot]?.type
        : link.type;
      if (type) input.type = output.type = type;
    } else if (input.link == null && (!output.links || output.links.length === 0)) {
      input.type = output.type = "*";
    }
    this.computeSize?.();
  };
}

app.registerExtension({
  name: "Reaper.PassThroughs",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!NODE_IDS.has(nodeData.name)) return;
    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      previousCreated?.apply(this, arguments);
      this.color = TITLE_COLOR;
      if (ANY_NODE_IDS.has(nodeData.name)) installAnyTypeMirroring(this);
    };
  },
});
