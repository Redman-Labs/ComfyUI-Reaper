"""Read generation settings out of the API prompt, for Civitai metadata.

Pure functions over the API-format prompt dict that ComfyUI hands a node as its
`prompt` hidden input. No ComfyUI / torch / PIL imports, so it unit-tests
standalone against real prompt JSON.

Harness: D:\\Claude Tests\\_civitai_walk_test.py (runs against prompts pulled
from a live /api/history, with the fetched prompts cached as fixtures).

WHY WALK THE GRAPH AT ALL: the established packs make the user WIRE steps / cfg
/ seed into the saver node, with hardcoded defaults on every field, so an
unwired field silently ships a wrong value (alexopus defaults to Steps 20 and
CFG 7.0 whatever you actually rendered with). We already receive the whole
prompt, so reading it is both zero-config and honest. The rule throughout:
**when a value cannot be determined, return None and let the caller omit the
key.** Never substitute a plausible default - a wrong number in the metadata is
worse than a missing one, because the viewer cannot tell it is wrong.

API prompt shape, for reference:
    {"12": {"class_type": "KSampler",
            "inputs": {"seed": 42, "steps": 8, "cfg": 1.0,
                       "sampler_name": "euler", "scheduler": "normal",
                       "denoise": 1.0,
                       "model": ["7", 0], "positive": ["9", 0], ...},
            "_meta": {"title": "KSampler"}}, ...}
A list value of the form [node_id, slot] is a LINK; anything else is a widget
value.
"""

import json
import re

_MAX_DEPTH = 32  # deep enough for real graphs, shallow enough to bound a cycle

# ---------------------------------------------------------------- link helpers


def is_link(value):
    """True for an API-format link, i.e. [node_id, slot_index]."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and isinstance(value[1], (int, float))
        and not isinstance(value[1], bool)
    )


def link_source(prompt, node_id, input_name):
    """The node id feeding `input_name`, or None if unwired / absent."""
    node = (prompt or {}).get(str(node_id))
    if not isinstance(node, dict):
        return None
    value = (node.get("inputs") or {}).get(input_name)
    return str(value[0]) if is_link(value) else None


def widget_value(prompt, node_id, input_name, default=None):
    """A widget (non-link) value, or `default` when wired/missing.

    A wired value is deliberately NOT followed here: the caller decides whether
    a primitive upstream is worth chasing, since following it blindly can pick
    up a value that is not what the sampler received.
    """
    node = (prompt or {}).get(str(node_id))
    if not isinstance(node, dict):
        return default
    value = (node.get("inputs") or {}).get(input_name)
    if value is None or is_link(value):
        return default
    return value


# Pixaroma value nodes keep their rows in a JSON state blob instead of widgets,
# and the OUTPUT SLOT of the link selects which row. Observed live 2026-07-30 on
# a workflow feeding KSampler: seed <- PixaromaSeed, and steps / cfg /
# sampler_name <- PixaromaSliders slots 0 / 1 / 2.
#   PixaromaSliders  inputs {"SlidersState": '{"version":1,"sliders":[{"type":"int","value":36},...]}'}
#   PixaromaSeed     inputs {"SeedState": '{"runSeed":1756}'}
# Each entry: state input name -> (list key or None, value key).
# A None list key means the blob holds ONE value, so the slot is ignored.
_STATE_BLOB_NODES = {
    "PixaromaSliders": ("SlidersState", "sliders", "value"),
    "PixaromaSeed": ("SeedState", None, "runSeed"),
}
# NOTE "Control Panel Pixaroma" IS PixaromaSliders - one node, two names
# (nodes/node_sliders.py: NODE_DISPLAY_NAME_MAPPINGS = {"PixaromaSliders":
# "Control Panel Pixaroma"}), so the entry above already covers it. There is no
# separate control_panel node to add.
#
# The other value nodes need NOTHING here, for two different reasons:
#   Number and WH keep their values in PLAIN WIDGETS (inputs.value /
#     inputs.width / inputs.height), so resolve_input's same-named and
#     "value"-named widget fallbacks already read them.
#   Portrait Landscape and Switch WH hold no value of their own - they only
#     select or reorder values arriving from elsewhere, so the walker must keep
#     following, which it does.
# Resolution and Sizes DO keep a state blob, but as a single width/height pair
# rather than a slot-indexed list, so they would need a different shape here.
# They are deliberately absent until verified against a live graphToPrompt: a
# wrong slot mapping records a real number that is simply the WRONG one, which
# is worse than a missing key because nobody can tell it is wrong.


_SEED_MAX = 0xFFFFFFFFFFFFFFFF


def _sliders_value(row):
    """Mirror of node_sliders.PixaromaSliders._value_of.

    MUST stay a mirror, not an approximation: the blob holds the RAW row value
    and the node transforms it before emitting, so reading the blob straight
    records a number the sampler never saw. A Control Panel row adopts the type
    of whatever it is wired into, so a float row re-wired to `steps` keeps its
    fractional value until the slider is next moved - that produced
    "Steps: 7.6" in metadata while the sampler ran 8.
    """
    if not isinstance(row, dict):
        return None
    kind = str(row.get("type") or "auto").lower()
    if kind in ("combo", "text"):
        v = row.get("value")
        return v if isinstance(v, str) else (None if v is None else str(v))
    try:
        value = float(row.get("value", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        value = 0.0
    if value != value or value in (float("inf"), float("-inf")):
        value = 0.0
    value = max(-1e12, min(1e12, value))
    if kind == "toggle":
        on = bool(round(value))
        if str(row.get("out") or "auto").lower() == "int":
            return 1 if on else 0
        return 1 if on else 0  # a bool is not a metadata value; emit the int form
    if kind in ("int", "seed"):
        return int(round(value))
    return float(value)


def _seed_value(state):
    """Mirror of node_seed.PixaromaSeed.get_seed (runSeed, else seed, else 0)."""
    try:
        s = int(state.get("runSeed", state.get("seed", 0)))
    except (TypeError, ValueError):
        return 0
    if s < 0:
        return 0
    if s > _SEED_MAX:
        return s % (_SEED_MAX + 1)
    return s


def _from_state_blob(prompt, node_id, slot):
    """Value a Pixaroma state-blob node emits on `slot`, or None.

    Applies the same normalisation the node itself applies, so the metadata
    records what the sampler actually received.
    """
    ct = class_of(prompt, node_id)
    spec = _STATE_BLOB_NODES.get(ct)
    if not spec:
        return None
    state_key, list_key, _value_key = spec
    raw = widget_value(prompt, node_id, state_key)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        state = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(state, dict):
        return None
    if list_key is None:
        return _seed_value(state)
    rows = state.get(list_key)
    if not isinstance(rows, list):
        return None
    try:
        idx = int(slot)
    except (TypeError, ValueError):
        return None
    # A negative index would silently wrap to the LAST row. Not reachable from
    # the frontend (API slots are non-negative) but it would be a wrong value.
    if idx < 0 or idx >= len(rows):
        return None
    return _sliders_value(rows[idx])


def resolve_input(prompt, node_id, input_name, _depth=0):
    """The VALUE of an input, following a wire when there is one.

    widget_value() alone is not enough: a real workflow often drives steps / cfg
    / seed / sampler_name from another node (a core Primitive, or our Sliders /
    Seed / Control Panel), in which case the sampler's own input is a LINK and
    the number lives upstream. Observed live: with Sliders and Seed wired in,
    reading widgets only would have returned nothing for steps, cfg, seed AND
    sampler_name, and since "Steps: " is the ONLY thing that makes Civitai parse
    the metadata at all, the whole feature would have silently done nothing.

    Resolution order at each hop:
      1. a plain widget value on this node                -> use it
      2. a Pixaroma state blob, indexed by the link SLOT  -> use it
      3. a widget of the SAME NAME on the upstream node   -> use it
      4. a single obvious value widget (value / Value / int / float / number)
      5. keep following, bounded, so a chain of reroutes still resolves
    Returns None when nothing usable is found. Never invents a value.
    """
    node = (prompt or {}).get(str(node_id))
    if not isinstance(node, dict) or _depth > 8:
        return None
    value = (node.get("inputs") or {}).get(input_name)
    if value is not None and not is_link(value):
        return value
    if not is_link(value):
        return None
    src_id, slot = str(value[0]), value[1]

    blob = _from_state_blob(prompt, src_id, slot)
    if blob is not None:
        return blob

    same = widget_value(prompt, src_id, input_name)
    if same is not None:
        return same

    for key in ("value", "Value", "int", "float", "number", "seed", "text"):
        v = widget_value(prompt, src_id, key)
        if v is not None:
            return v

    # A reroute / passthrough: try the same-named input one hop further up.
    return resolve_input(prompt, src_id, input_name, _depth + 1)


def class_of(prompt, node_id):
    node = (prompt or {}).get(str(node_id))
    return str(node.get("class_type", "")) if isinstance(node, dict) else ""


def walk_back(prompt, start_id, match, follow=None, max_depth=_MAX_DEPTH):
    """Breadth-first search upstream for the first node `match` accepts.

    match(class_type, node_id) -> bool
    follow(class_type, input_name) -> bool, gating which inputs to traverse;
        default follows every wired input.
    Returns the node id or None. Visited set + depth cap, so a cyclic or
    pathological prompt cannot hang a save.
    """
    if not prompt or start_id is None:
        return None
    seen = {str(start_id)}
    frontier = [(str(start_id), 0)]
    while frontier:
        nxt = []
        for node_id, depth in frontier:
            if depth > max_depth:
                continue
            ct = class_of(prompt, node_id)
            if depth and match(ct, node_id):
                return node_id
            node = prompt.get(node_id)
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for name, value in inputs.items():
                if not is_link(value):
                    continue
                if follow and not follow(ct, name):
                    continue
                src = str(value[0])
                if src in seen:
                    continue
                seen.add(src)
                nxt.append((src, depth + 1))
        frontier = nxt
    return None


# ------------------------------------------------------------------- samplers

_SAMPLER_RE = re.compile(r"sampler", re.I)
# Classes that carry the settings themselves rather than delegating to helpers.
_INLINE_SAMPLERS = ("KSampler", "KSamplerAdvanced")
# KSamplerSelect matches /sampler/i but is a PICKER: it only returns a SAMPLER
# object for another node to use, and carries no steps/cfg/seed. It must never be
# mistaken for the sampler that ran.
#
# SamplerCustom / SamplerCustomAdvanced are deliberately NOT in this list: they
# ARE the sampler in the modern custom-sampling chain, and read_sampler() below
# exists precisely to follow their sampler / sigmas / guider / noise inputs out
# to the helper nodes that hold the values. An earlier version of this tuple
# listed SamplerCustomAdvanced here, which made find_sampler refuse the only
# node read_sampler knew how to interpret. Caught by the harness fixture, not by
# reading the code, which is why that fixture exists.
_NOT_THE_SAMPLER = ("KSamplerSelect",)


def find_sampler(prompt, save_node_id):
    """The sampler node that produced the image this save node received.

    Walks back from the save node through whatever sits between (VAEDecode,
    resize, overlay, compare...), so it does not care about the chain shape.
    Picks the FIRST sampler found breadth-first, which is the nearest one
    upstream and therefore the one that made this image - the right answer in a
    multi-pass workflow, where a later refiner is nearer than the base pass.
    """
    def match(ct, _id):
        if ct in _NOT_THE_SAMPLER:
            return False
        return bool(_SAMPLER_RE.search(ct))
    return walk_back(prompt, save_node_id, match)


def read_sampler(prompt, sampler_id):
    """Settings of a sampler node as a dict of value-or-None.

    Handles the inline KSampler family directly, and for the SamplerCustom
    family follows `sampler` -> KSamplerSelect and `sigmas` -> a scheduler node
    to recover the names, since those live on separate nodes there.
    """
    # Always return the FULL key set, even with no sampler, so a caller can read
    # any key without a KeyError guard. Missing means None, never absent.
    if sampler_id is None:
        return {"steps": None, "cfg": None, "seed": None, "denoise": None,
                "sampler_name": None, "scheduler": None, "class_type": ""}
    ct = class_of(prompt, sampler_id)
    # resolve_input, NOT widget_value: any of these can be driven by a wire from
    # a Primitive or from Sliders / Seed / Control Panel Pixaroma, and reading
    # widgets only returns None for every one of them (verified on a live graph).
    out = {
        "steps": resolve_input(prompt, sampler_id, "steps"),
        "cfg": resolve_input(prompt, sampler_id, "cfg"),
        "seed": resolve_input(prompt, sampler_id, "seed"),
        "denoise": resolve_input(prompt, sampler_id, "denoise"),
        "sampler_name": resolve_input(prompt, sampler_id, "sampler_name"),
        "scheduler": resolve_input(prompt, sampler_id, "scheduler"),
        "class_type": ct,
    }
    # KSamplerAdvanced names the seed differently and has no denoise.
    if out["seed"] is None:
        out["seed"] = resolve_input(prompt, sampler_id, "noise_seed")

    if out["sampler_name"] is None:
        picker = link_source(prompt, sampler_id, "sampler")
        if picker:
            out["sampler_name"] = widget_value(prompt, picker, "sampler_name")
    if out["scheduler"] is None:
        sigmas = link_source(prompt, sampler_id, "sigmas")
        if sigmas:
            out["scheduler"] = widget_value(prompt, sigmas, "scheduler")
            if out["steps"] is None:
                out["steps"] = widget_value(prompt, sigmas, "steps")
            if out["denoise"] is None:
                out["denoise"] = widget_value(prompt, sigmas, "denoise")
    if out["cfg"] is None:
        guider = link_source(prompt, sampler_id, "guider")
        if guider:
            out["cfg"] = widget_value(prompt, guider, "cfg")
    if out["seed"] is None:
        noise = link_source(prompt, sampler_id, "noise")
        if noise:
            out["seed"] = widget_value(prompt, noise, "noise_seed")
    return out


# ------------------------------------------------------- checkpoint and LoRAs

# Input names that hold a model file, in the order we prefer them.
_CKPT_KEYS = ("ckpt_name", "unet_name", "model_name", "model_path")
_CKPT_CLASS_RE = re.compile(r"(checkpoint|unet|diffusion)", re.I)


def find_checkpoint(prompt, from_id):
    """(node_id, filename) of the checkpoint/UNet feeding `from_id`, or (None, None).

    Follows only model-carrying inputs so it cannot wander into the CLIP or VAE
    branch and return the wrong file.
    """
    def follow(_ct, name):
        # "guider" is REQUIRED, not optional: SamplerCustom / SamplerCustomAdvanced
        # reach the model through a guider node, so without it the filtered walk
        # returns nothing on EVERY custom-sampling graph and falls through to the
        # unfiltered retry below - which then happily picks a checkpoint that was
        # only loaded for its CLIP or VAE, and hashes that file. Reproduced on a
        # Flux graph: it recorded an unrelated SD1.5 checkpoint as the model.
        return name in ("model", "unet", "base_model", "guider")

    def match(ct, node_id):
        if not _CKPT_CLASS_RE.search(ct):
            return False
        return any(widget_value(prompt, node_id, k) for k in _CKPT_KEYS)

    node_id = walk_back(prompt, from_id, match, follow=follow)
    if node_id is None:
        # Some chains route the model through inputs we did not follow; retry
        # without the filter rather than give up. NOTE this retry can only ever
        # GUESS - it may reach a checkpoint loaded for its CLIP or VAE - so the
        # follow-list above must stay complete enough that it rarely runs.
        node_id = walk_back(prompt, from_id, match)
    if node_id is None:
        return None, None, None
    for k in _CKPT_KEYS:
        v = widget_value(prompt, node_id, k)
        if isinstance(v, str) and v:
            # Return the WIDGET NAME too: it says which model tree the name came
            # from (ckpt_name -> checkpoints, unet_name -> diffusion_models), and
            # discarding it meant the resolver tried "checkpoints" first for
            # everything, so a name present in BOTH trees hashed the wrong file.
            return node_id, v, k
    return node_id, None, None


_LORA_CLASSES = ("LoraLoader", "LoraLoaderModelOnly")
_STATE_LORA_CLASSES = ("ReaperLoraLoader", "PixaromaLoraLoader")
# Civitai's own parser skips a LoRA whose strength is effectively zero; match
# that so a disabled LoRA is not advertised as used.
_ZERO = 0.001


def collect_loras(prompt, from_id):
    """[(lora_filename, strength)] for every active LoRA feeding `from_id`.

    Nearest-first. Skips strengths within +/-0.001 of zero, matching Civitai's
    own parser. Reaper's multi-LoRA loader keeps its stack in a state blob rather
    than widgets, so it is NOT read here: the caller passes those rows in
    separately (its own JS/py already knows them).
    """
    found = []
    if not prompt or from_id is None:
        return found
    seen = {str(from_id)}
    frontier = [(str(from_id), 0)]
    while frontier:
        nxt = []
        for node_id, depth in frontier:
            if depth > _MAX_DEPTH:
                continue
            ct = class_of(prompt, node_id)
            if depth and ct in _LORA_CLASSES:
                name = resolve_input(prompt, node_id, "lora_name")
                # resolve_input, NOT widget_value: a wired strength (from Control
                # Panel Pixaroma, a Primitive, anything) reads as None through
                # widget_value and used to fall back to 1.0 - so a LoRA the user
                # had turned DOWN TO ZERO was advertised at full strength, and the
                # zero-skip below could never fire because the guess was 1.0.
                strength = resolve_input(prompt, node_id, "strength_model")
                if strength is None:
                    strength = resolve_input(prompt, node_id, "strength")
                try:
                    s = float(strength) if strength is not None else None
                except (TypeError, ValueError):
                    s = None
                # Undeterminable strength -> omit the row rather than invent 1.0.
                # The hash still reaches Civitai through collect_resources, which
                # keys off the name; only the weight is lost, which is honest.
                if isinstance(name, str) and name and s is not None and not (-_ZERO < s < _ZERO):
                    found.append((name, s))
            node = prompt.get(node_id)
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for iname, value in inputs.items():
                if not is_link(value):
                    continue
                src = str(value[0])
                if src in seen:
                    continue
                seen.add(src)
                nxt.append((src, depth + 1))
        frontier = nxt
    return found


def find_state_loras(prompt, from_id):
    """Node ids of supported state-based LoRA loaders feeding `from_id`.

    Its rows live in a state blob, not widgets, so the caller has to unpack them
    itself; this only reports WHERE they are.
    """
    ids = []
    seen = {str(from_id)} if from_id is not None else set()
    frontier = [(str(from_id), 0)] if from_id is not None else []
    while frontier:
        nxt = []
        for node_id, depth in frontier:
            if depth > _MAX_DEPTH:
                continue
            if depth and class_of(prompt, node_id) in _STATE_LORA_CLASSES:
                ids.append(node_id)
            node = (prompt or {}).get(node_id)
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for _n, value in inputs.items():
                if is_link(value) and str(value[0]) not in seen:
                    seen.add(str(value[0]))
                    nxt.append((str(value[0]), depth + 1))
        frontier = nxt
    return ids


# ------------------------------------------------------------- prompt text

# Mirrors the intent of _prompt_reader_helpers._TEXT_KEYS: every input name that
# can carry prompt text on a conditioning node.
_TEXT_KEYS = ("text", "text_g", "text_l", "prompt", "string", "value",
              "positive", "text_positive")


def read_text(prompt, cond_id, avoid=(), max_depth=_MAX_DEPTH):
    """First prompt string found upstream of a conditioning input, or None.

    Follows conditioning chains (Combine / Concat / SetArea and friends) and
    primitive string wires, which is why it does not just read one widget.

    `avoid` names inputs the walk must NOT traverse. This is load-bearing, not a
    nicety: nodes like ControlNetApplyAdvanced carry BOTH conditioning sides, so
    when the positive text arrives by wire (one hop further away) the negative
    node's literal is nearer and wins - the image then ships with its NEGATIVE
    prompt recorded as the positive, which nobody looking at it can detect.
    Reproduced before this guard existed. Refusing the opposite branch is purely
    subtractive: the worst case becomes an omitted prompt, never a swapped one.
    """
    if not prompt or cond_id is None:
        return None
    avoid = tuple(avoid or ())
    seen = {str(cond_id)}
    frontier = [(str(cond_id), 0)]
    while frontier:
        nxt = []
        for node_id, depth in frontier:
            if depth > max_depth:
                continue
            node = prompt.get(node_id)
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for key in _TEXT_KEYS:
                v = inputs.get(key)
                if isinstance(v, str) and v.strip():
                    return v
            for name, value in inputs.items():
                if name in avoid:
                    continue
                if is_link(value) and str(value[0]) not in seen:
                    seen.add(str(value[0]))
                    nxt.append((str(value[0]), depth + 1))
        frontier = nxt
    return None


def read_prompts(prompt, sampler_id):
    """(positive_text, negative_text), either of which may be None."""
    pos = link_source(prompt, sampler_id, "positive")
    neg = link_source(prompt, sampler_id, "negative")
    if pos is None and neg is None:
        # SamplerCustom routes conditioning through a guider node.
        guider = link_source(prompt, sampler_id, "guider")
        if guider:
            pos = link_source(prompt, guider, "positive")
            neg = link_source(prompt, guider, "negative")
            # BasicGuider (the standard Flux shape) has NEITHER: its single
            # conditioning input carries the positive, one hop further out.
            # Without this the most common modern workflow recorded no prompt.
            if pos is None and neg is None:
                pos = link_source(prompt, guider, "conditioning")
    # Each side refuses to cross into the other, so a node carrying both (e.g.
    # ControlNetApplyAdvanced) cannot leak the negative into the positive.
    return (read_text(prompt, pos, avoid=("negative",)),
            read_text(prompt, neg, avoid=("positive",)))


# ------------------------------------------------------------------ top level

def describe(prompt, save_node_id):
    """Everything the Civitai metadata needs, as value-or-None.

    Returns a dict: sampler_id, class_type, steps, cfg, seed, denoise,
    sampler_name, scheduler, positive, negative, checkpoint, checkpoint_id,
    loras (list of (name, strength)), state_lora_ids.

    Nothing is defaulted. The caller drops every None key, which is exactly what
    A1111 does with an unset value, so the emitted string stays truthful.
    """
    sampler_id = find_sampler(prompt, save_node_id)
    info = read_sampler(prompt, sampler_id)
    pos, neg = read_prompts(prompt, sampler_id)
    ckpt_id, ckpt, ckpt_key = find_checkpoint(prompt, sampler_id if sampler_id else save_node_id)
    info.update({
        "sampler_id": sampler_id,
        "positive": pos,
        "negative": neg,
        "checkpoint": ckpt,
        "checkpoint_id": ckpt_id,
        "checkpoint_key": ckpt_key,   # which widget supplied it -> which folder
        "loras": collect_loras(prompt, sampler_id if sampler_id else save_node_id),
        "state_lora_ids": find_state_loras(prompt, sampler_id if sampler_id else save_node_id),
    })
    return info
