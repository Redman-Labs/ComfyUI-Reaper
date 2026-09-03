// ╔═══════════════════════════════════════════════════════════════╗
// ║  SetNode (Reaper) / GetNode (Reaper) - wireless "named variable" node pair     ║
// ╚═══════════════════════════════════════════════════════════════╝
//
// Reaper's own wireless "named variable" node pair, in a PRIVATE namespace:
// classes ReaperSetNode / ReaperGetNode with their own registry
// (js/set_get/scope.mjs) that only ever scans Reaper Set/Get. It coexists with
// any other pack's Set/Get-style nodes in one workflow with zero interference.
//
// Both are pure-frontend VIRTUAL nodes (isVirtualNode = true): no Python, never
// in the prompt. Resolution at submission goes straight through to the real
// source via getInputLink (same-graph) + resolveVirtualOutput (subgraph). Works
// in both Classic and Nodes 2.0, and inside subgraphs (native path verified on
// frontend 1.47.10+).

import { app } from "/scripts/app.js";
import { registerReaperSetNode } from "./set_node.mjs";
import { registerReaperGetNode } from "./get_node.mjs";
import { startValuePoll } from "./value_preview.mjs";
import { SETTING_ID, recolorAllGets } from "./colors.mjs";
import "./help.mjs"; // registers help for both nodes (convention #16)

app.registerExtension({
  name: "Reaper.SetGet",
  settings: [
    {
      id: SETTING_ID,
      name: "Get matches its Set's color",
      type: "boolean",
      defaultValue: true,
      tooltip: "Makes each Get node use the color of its selected Set node.",
      category: ["Reaper", "Set and Get"],
      onChange: () => recolorAllGets(),
    },
  ],
  // Register the frontend classes after ComfyUI has loaded their V3 backend
  // metadata definitions. The custom classes provide the virtual-node behavior.
  registerCustomNodes() {
    registerReaperSetNode();
    registerReaperGetNode();
  },
  setup() {
    startValuePoll();
  },
});
