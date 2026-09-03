import { app } from "/scripts/app.js";


const CATEGORY_TITLE_COLORS = new Map([
  ["Reaper/Face Utils", "#07857b"],
  ["Reaper/Flow Control", "#141413"],
  ["Reaper/Image Utils", "#064a90"],
  ["Reaper/In-Outpainting Utils", "#2c2c2c"],
  ["Reaper/Latent Utils", "#ff2ef2"],
  ["Reaper/Mask Utils", "#02a80a"],
  ["Reaper/Model Utils", "#5a16d9"],
  ["Reaper/Pass Throughs", "#2c2c2c"],
  ["Reaper/Prompt & Text", "#d9830b"],
  ["Reaper/Switches", "#2c2c2c"],
  ["Reaper/Tools", "#2c2c2c"],
  ["Reaper/VAE Utils", "#b82b2b"],
]);


app.registerExtension({
  name: "Reaper.CategoryDefaultColors",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    // GLOBAL_NAME may also change the category's brand prefix (for example,
    // Reaper/Model Utils -> Reaper/Model Utils). Resolve that prefix back to the
    // canonical Reaper key so category colors remain global-name independent.
    const category = String(nodeData.category || "");
    const canonicalCategory = category.includes("/")
      ? `Reaper/${category.slice(category.indexOf("/") + 1)}`
      : category;
    const titleColor = CATEGORY_TITLE_COLORS.get(category)
      || CATEGORY_TITLE_COLORS.get(canonicalCategory);
    if (!titleColor) return;

    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      previousCreated?.apply(this, arguments);
      this.color = titleColor;
    };
  },
});
