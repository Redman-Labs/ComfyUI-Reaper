import { app } from "/scripts/app.js";
import { createDOMPreview, feedDOMPreview } from "./dom_preview.js";


const NODE_ID = "ReaperImagePreview";


app.registerExtension({
  name: "Reaper.ImagePreview",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_ID) return;

    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = previousCreated?.apply(this, arguments);
      createDOMPreview(this, { minHeight: 200, freeResize: true });
      return result;
    };

    const previousExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (output) {
      const savedImages = output.images;
      delete output.images;
      previousExecuted?.apply(this, arguments);
      if (savedImages) output.images = savedImages;
      this.imgs = null;
      feedDOMPreview(this, output);
      const nodeOutputs = app.nodeOutputs?.[this.id];
      if (nodeOutputs?.images) delete nodeOutputs.images;
    };
  },
});
