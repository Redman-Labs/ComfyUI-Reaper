import { app } from "/scripts/app.js";


const IMAGE_MASK_NODE_IDS = new Set([
  "ReaperColorCorrection",
  "ReaperColorMatch",
  "Reaper_CropImageToMask",
  "ReaperCompareAdvanced",
  "ReaperCompareSimple",
  "ReaperImageFilterAdjustment",
  "ReaperImagePreview",
  "ReaperImageUpscale",
  "ReaperLoadImage",
  "ReaperLoadImageInfo",
  "ReaperMaskToImage",
  "MaskToRectangle",
  "ReaperPauseImage",
  "ReaperPauseImageCompare",
  "Reaper_ResizeImageToPixels",
  "ReaperResizeImageMask",
  "ReaperSaveImage",
]);

const DEFAULT_TITLE_COLOR = "#070cdc";


app.registerExtension({
  name: "Reaper.ImageMaskDefaultColor",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!IMAGE_MASK_NODE_IDS.has(nodeData.name)) return;

    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      previousCreated?.apply(this, arguments);
      this.color = DEFAULT_TITLE_COLOR;
    };
  },
});
