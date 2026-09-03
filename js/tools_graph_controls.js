import { app } from "/scripts/app.js";

const IDS = {
  muter: "ReaperFastMuter",
  bypasser: "ReaperFastBypasser",
  repeater: "ReaperMuteBypassRepeater",
  collector: "ReaperNodeCollector",
  reroute: "ReaperReroute",
};
const CONTROL_TYPES = new Set(Object.values(IDS));
const MODE_ACTIVE = 0;
const MODE_MUTE = 2;
const MODE_BYPASS = 4;

function graphOf(node) {
  return node.graph || app.canvas?.getCurrentGraph?.() || app.graph;
}

function linkById(graph, id) {
  return graph?.links?.[id] || graph?.links?.get?.(id) || graph?._links?.get?.(id) || null;
}

function originFor(node, inputIndex) {
  const graph = graphOf(node);
  const input = node.inputs?.[inputIndex];
  const link = input?.link != null ? linkById(graph, input.link) : null;
  return link ? graph?.getNodeById?.(link.origin_id) : null;
}

function targetsFor(node, outputIndex = 0) {
  const graph = graphOf(node);
  const ids = node.outputs?.[outputIndex]?.links || [];
  return ids.map((id) => linkById(graph, id))
    .filter(Boolean)
    .map((link) => graph?.getNodeById?.(link.target_id))
    .filter(Boolean);
}

function upstreamNodes(node, seen = new Set()) {
  if (!node || seen.has(node.id)) return [];
  seen.add(node.id);
  const found = [];
  for (let i = 0; i < (node.inputs?.length || 0); i++) {
    const origin = originFor(node, i);
    if (!origin) continue;
    if (origin.comfyClass === IDS.collector || origin.comfyClass === IDS.reroute ||
        origin.type === IDS.collector || origin.type === IDS.reroute) {
      found.push(...upstreamNodes(origin, seen));
    } else {
      found.push(origin);
    }
  }
  return [...new Map(found.map((item) => [item.id, item])).values()];
}

function renameAndGrowInputs(node) {
  if (!node.inputs?.length) node.addInput("", "*");
  for (let i = node.inputs.length - 2; i >= 0; i--) {
    if (node.inputs[i].link == null) node.removeInput(i);
  }
  node.inputs.forEach((input, index) => {
    const origin = originFor(node, index);
    const label = origin ? (origin.title || origin.type || "Node") : "";
    // V3 inputs carry a display label separately from the internal name. Both
    // must be updated or the first schema-created slot continues to say "node".
    input.name = label;
    input.label = label;
  });
  const last = node.inputs[node.inputs.length - 1];
  if (last?.link != null) node.addInput("", "*");
}

function notifyDownstream(node) {
  for (const target of targetsFor(node)) target._reaperRefreshConnections?.();
}

function markVirtual(node) {
  node.isVirtualNode = true;
  node.serialize_widgets = true;
  node.properties ||= {};
}

function installDynamicInputs(node, refresh) {
  let timer = null;
  const stabilize = () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (!node.graph) return;
      renameAndGrowInputs(node);
      refresh?.();
      notifyDownstream(node);
      node.graph.setDirtyCanvas?.(true, true);
    }, 20);
  };
  node._reaperRefreshConnections = stabilize;
  const previous = node.onConnectionsChange;
  node.onConnectionsChange = function () {
    previous?.apply(this, arguments);
    stabilize();
  };
  stabilize();
}

function installModeController(node, offMode) {
  markVirtual(node);
  node.properties.toggleRestriction ||= "default";
  const widgetByNode = new Map();

  const setTarget = (target, enabled, skipRestriction = false) => {
    if (!target) return;
    if (!skipRestriction && enabled && node.properties.toggleRestriction?.includes(" one")) {
      for (const [other, widget] of widgetByNode) {
        if (other !== target) {
          other.mode = offMode;
          widget.value = false;
        }
      }
    }
    if (!skipRestriction && !enabled && node.properties.toggleRestriction === "always one") {
      const enabledCount = [...widgetByNode.values()].filter((w) => w.value).length;
      if (enabledCount <= 1) return;
    }
    target.mode = enabled ? MODE_ACTIVE : offMode;
    const widget = widgetByNode.get(target);
    if (widget) widget.value = enabled;
  };

  const refresh = () => {
    const targets = upstreamNodes(node);
    const previousWidgets = node.widgets || [];
    node.widgets = [];
    widgetByNode.clear();
    for (const target of targets) {
      let widget = previousWidgets.find((w) => w._reaperTargetId === target.id);
      const enabled = target.mode === MODE_ACTIVE;
      if (!widget) {
        widget = node.addWidget("toggle", `Enable ${target.title}`, enabled, (value) => {
          setTarget(target, !!value);
          graphOf(node)?.setDirtyCanvas?.(true, true);
        }, { on: "yes", off: "no" });
      } else {
        widget.name = `Enable ${target.title}`;
        widget.value = enabled;
        widget.callback = (value) => setTarget(target, !!value);
        node.widgets.push(widget);
      }
      widget._reaperTargetId = target.id;
      widgetByNode.set(target, widget);
    }
    node.setSize?.([Math.max(node.size?.[0] || 220, 220), node.computeSize?.()[1] || node.size?.[1]]);
  };

  node._reaperModeAction = (action) => {
    for (const [target, widget] of widgetByNode) {
      const enabled = action === "Enable all" ? true
        : action === "Toggle all" ? !widget.value : false;
      setTarget(target, enabled, true);
    }
    graphOf(node)?.setDirtyCanvas?.(true, true);
  };
  installDynamicInputs(node, refresh);
}

function installRepeater(node) {
  markVirtual(node);
  const propagate = (mode) => {
    for (const target of upstreamNodes(node)) target.mode = mode;
    graphOf(node)?.setDirtyCanvas?.(true, true);
  };
  const modeDescriptor = Object.getOwnPropertyDescriptor(node, "mode");
  let currentMode = node.mode ?? MODE_ACTIVE;
  try {
    Object.defineProperty(node, "mode", {
      configurable: true,
      get: () => currentMode,
      set: (value) => {
        currentMode = value;
        propagate(value);
      },
    });
  } catch {
    void modeDescriptor;
  }
  installDynamicInputs(node, () => propagate(currentMode));
}

function installCollector(node) {
  markVirtual(node);
  if (node.outputs?.[0]) {
    node.outputs[0].name = "Output";
    node.outputs[0].label = "Output";
  }
  node._reaperCollectedNodes = () => upstreamNodes(node);
  installDynamicInputs(node);
}

function sourceSlotType(node) {
  const graph = graphOf(node);
  const link = node.inputs?.[0]?.link != null ? linkById(graph, node.inputs[0].link) : null;
  if (!link) return "*";
  const origin = graph?.getNodeById?.(link.origin_id);
  return origin?.outputs?.[link.origin_slot]?.type || link.type || "*";
}

function updateRerouteType(node, seen = new Set()) {
  if (!node || seen.has(node.id)) return;
  seen.add(node.id);
  const type = sourceSlotType(node);
  if (node.inputs?.[0]) node.inputs[0].type = type;
  if (node.outputs?.[0]) node.outputs[0].type = type;
  for (const target of targetsFor(node)) {
    if (target.comfyClass === IDS.reroute || target.type === IDS.reroute) {
      updateRerouteType(target, seen);
    }
  }
  graphOf(node)?.setDirtyCanvas?.(true, true);
}

function installReroute(node) {
  markVirtual(node);
  node.properties.resizable ??= false;
  node.properties.layout ||= "Left/Right";
  node.setSize?.([Math.max(40, node.size?.[0] || 40), Math.max(30, node.size?.[1] || 30)]);
  const previous = node.onConnectionsChange;
  node.onConnectionsChange = function () {
    previous?.apply(this, arguments);
    setTimeout(() => updateRerouteType(this), 0);
  };
  setTimeout(() => updateRerouteType(node), 0);
}

app.registerExtension({
  name: "Reaper.Tools.GraphControls",

  loadedGraphNode(node) {
    if (CONTROL_TYPES.has(node.comfyClass || node.type)) {
      setTimeout(() => node._reaperRefreshConnections?.(), 0);
    }
  },

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!CONTROL_TYPES.has(nodeData.name)) return;
    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      previousCreated?.apply(this, arguments);
      if (nodeData.name === IDS.muter) installModeController(this, MODE_MUTE);
      else if (nodeData.name === IDS.bypasser) installModeController(this, MODE_BYPASS);
      else if (nodeData.name === IDS.repeater) installRepeater(this);
      else if (nodeData.name === IDS.collector) installCollector(this);
      else if (nodeData.name === IDS.reroute) installReroute(this);
    };

    const previousMenu = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function (canvas, options) {
      previousMenu?.apply(this, arguments);
      if (nodeData.name === IDS.muter || nodeData.name === IDS.bypasser) {
        const offLabel = nodeData.name === IDS.muter ? "Mute all" : "Bypass all";
        options.unshift(
          { content: offLabel, callback: () => this._reaperModeAction?.(offLabel) },
          { content: "Enable all", callback: () => this._reaperModeAction?.("Enable all") },
          { content: "Toggle all", callback: () => this._reaperModeAction?.("Toggle all") },
          null,
        );
      }
      if (nodeData.name === IDS.reroute) {
        options.unshift({
          content: this.properties?.resizable ? "Use compact size" : "Allow resizing",
          callback: () => {
            this.properties.resizable = !this.properties.resizable;
            this.resizable = this.properties.resizable;
            if (!this.resizable) this.setSize?.([40, 30]);
          },
        });
      }
    };
  },
});
