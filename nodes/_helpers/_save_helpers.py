"""Shared helpers for Reaper nodes that save images:
  - _expand_date_tokens: expand VHS-style %date:fmt% in filename_prefix
  - _safe_prefix:        validate filename_prefix supporting subfolder/file syntax
  - _build_pnginfo:      build a PngInfo embedding workflow + prompt for re-import
Used by node_preview.py (Python entry) and server_routes.py (HTTP routes).
"""

import json
import math
import os
import re
import time

from PIL.PngImagePlugin import PngInfo

# Honour ComfyUI's global --disable-metadata flag (same as core SaveImage).
# Wrapped so these helpers still import on a build that lacks it, and so the
# unit harness can run them with no ComfyUI on sys.path at all.
try:
    from comfy.cli_args import args as _comfy_cli_args
except Exception:
    _comfy_cli_args = None


def _metadata_disabled():
    """True when ComfyUI was launched with --disable-metadata.

    Read LIVE on every call rather than cached at import: `args` is populated
    during startup and import order between us and comfy is not guaranteed, so
    a value snapshotted at import time could be the pre-parse default.

    Fails OPEN (returns False) when the flag or the whole module is missing, so
    a build without it keeps today's behaviour instead of silently losing every
    embedded workflow.
    """
    return bool(getattr(_comfy_cli_args, "disable_metadata", False))


def _json_safe(obj):
    """Recursively replace non-finite floats (NaN / Infinity) with None.

    PROMPT contains `is_changed: [NaN]` for any node whose IS_CHANGED returns
    nan (e.g. Preview Image Reaper). Python's json.dumps writes that as the
    bare token `NaN`, which is invalid JSON - so the embedded PNG metadata
    chunk can't be parsed by strict readers, and the same value over the
    ComfyUI websocket breaks the frontend JSON.parse. Sanitize first.
    """
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


# ---- date-token expansion (VHS-compatible %date:fmt% syntax) ----

# Match %date:FMT% where FMT is one or more non-% characters.
# Native ComfyUI tokens (%year%, %month%, %day%, %hour%, %minute%,
# %second%, %width%, %height%) are NOT touched here - they are expanded
# later by folder_paths.get_save_image_path.
_DATE_TOKEN_RE = re.compile(r"%date:([^%]+)%")

# Date field codes, matching ComfyUI's NATIVE %date:...% (its frontend
# formatUtil.formatDate) EXACTLY, so the same filename pattern behaves identically
# here and in the built-in Save Image. Tokens are CASE-SENSITIVE, single OR
# doubled, and zero-padded to the token length:
#     d/dd  day        M/MM  month       h/hh  HOUR (24-hour, like getHours)
#     m/mm  minute     s/ss  second      yy    2-digit year   yyyy  4-digit year
# H/HH is ALSO accepted as an hour alias - Reaper used HH before native lower-
# case hh was supported, so keep it working. Anything else (incl. a lone 'yyy')
# passes through literally, again matching native ComfyUI. (The earlier code used
# UPPERCASE HH only, so a native 'hh' came out literal - GitHub-style report.)
_DATE_FIELD_RE = re.compile(r"dd?|MM?|hh?|HH?|mm?|ss?|yyy?y?")


def _expand_date_tokens(s):
    """Expand %date:FMT% tokens using ComfyUI-native codes (see _DATE_FIELD_RE).

    Examples (assuming 2026-05-10 14:32:07):
        %date:yyyy-MM-dd%          -> 2026-05-10
        %date:yyyy/MM/dd%          -> 2026/05/10  (3 nested folders)
        %date:yyyy-MM-dd hh-mm-ss% -> 2026-05-10 14-32-07

    Native ComfyUI tokens (%year%, %month%, etc.) are left alone for
    folder_paths.get_save_image_path to handle. Returns the input
    unchanged if it doesn't contain '%date:'.
    """
    if not isinstance(s, str) or "%date:" not in s:
        return s
    now = time.localtime()
    fields = {
        "d": now.tm_mday,
        "M": now.tm_mon,
        "h": now.tm_hour,   # 24-hour, matching ComfyUI's getHours()
        "H": now.tm_hour,   # alias so an older HH pattern still works
        "m": now.tm_min,
        "s": now.tm_sec,
    }

    def _field(m):
        tok = m.group(0)
        if tok == "yy":
            return ("%04d" % now.tm_year)[-2:]
        if tok == "yyyy":
            return "%04d" % now.tm_year
        c = tok[0]
        if c in fields:
            return str(fields[c]).zfill(len(tok))
        return tok  # e.g. a lone 'yyy' -> literal, like native ComfyUI

    def _sub(match):
        try:
            return _DATE_FIELD_RE.sub(_field, match.group(1))
        except Exception:
            # Leave the token untouched on any error so the user sees their
            # input verbatim and can fix it.
            return match.group(0)

    return _DATE_TOKEN_RE.sub(_sub, s)


# ---- prefix sanitization ----

# DENYLIST, not allowlist (June-2026 Korean filename_prefix report): only the
# characters Windows forbids in file/folder names (< > : " | ? *) plus ASCII
# control chars are replaced with '_'. Everything else - non-Latin scripts
# (Korean, Japanese, ...), accented letters, spaces, dots - passes through
# verbatim, matching native ComfyUI SaveImage (which does no character
# filtering at all; folder_paths.get_save_image_path only enforces that the
# final path stays inside output/). The old [^A-Za-z0-9_\-%] allowlist
# dissolved an all-Korean prefix to nothing -> "Preview" fallback in the
# output root. Sanitization, not rejection: wiring an upstream filename like
# "Bunny Cubes - Copy.png" just works instead of failing the save.
# '/' (separator) and '\\' (normalized to '/') are handled before splitting;
# '%' stays legal so native tokens like %year% survive for final expansion.
# scripts/save_prefix_check.py locks this behavior - keep it green.
_DISALLOWED_CHAR_RE = re.compile(r'[<>:"|?*\x00-\x1f\x7f]')
_MULTI_UNDERSCORE_RE = re.compile(r"_+")
_PREFIX_MAX_LEN = 256       # input cap (reject obvious garbage early)
_PREFIX_OUTPUT_MAX = 100    # output cap so pasted paragraphs / multi-line
                            # text don't blow past Windows MAX_PATH

# Names Windows reserves for devices - a folder/file with one of these names
# (bare or with any extension, any case) can't be created normally and would
# hard-error the save mid-run. Suffixed with '_' instead.
_WIN_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def _sanitize_segment(seg):
    """Neutralize Windows-illegal chars to '_', tidy edges, guard reserved names.

    Caller must reject '..' before calling. Returns "" if nothing usable
    survives (e.g. segment was all dots / whitespace / illegal chars).
    Trailing dots/spaces are stripped because Windows itself silently strips
    them at create time - stripping here keeps the reported path identical
    to what actually lands on disk.
    """
    cleaned = _DISALLOWED_CHAR_RE.sub("_", seg)
    cleaned = _MULTI_UNDERSCORE_RE.sub("_", cleaned)
    # Loop until stable: edge whitespace, edge underscores, and trailing
    # dots/spaces can shadow each other (e.g. "test._" needs two passes).
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = cleaned.strip().strip("_").rstrip(". ")
    if cleaned and cleaned.split(".", 1)[0].upper() in _WIN_RESERVED_NAMES:
        cleaned += "_"
    return cleaned


def _safe_prefix(s):
    """Return sanitized prefix string, or None if input is unrecoverable.

    Pipeline: expand %date:FMT% tokens, then per segment replace only
    Windows-illegal chars (< > : " | ? * and control chars) with '_',
    collapse repeated '_', strip edge whitespace/underscores/trailing
    dots, and suffix Windows-reserved device names (CON, NUL, ...) with
    '_'. Everything else - non-Latin scripts, accents, spaces - passes
    through verbatim, like native SaveImage. Segments separated by '/'.

    Empty segments (e.g. trailing slashes, doubled slashes) are silently
    dropped — so 'teasda......////' becomes 'teasda' rather than failing.
    Returns None only for truly unrecoverable input: non-string, empty
    after strip, length > 256, leading '/', any segment that's literally
    '..' (path traversal), or nothing usable left after sanitization.
    Backslashes are normalized to forward slashes (Windows convenience).

    Caller decides what to do with None:
      - Backend node:  `_safe_prefix(s) or "Preview"` (don't crash workflow)
      - Server routes: `if not prefix: return 400` (surface error to JS)
    """
    if not isinstance(s, str):
        return None
    s = _expand_date_tokens(s)
    s = s.strip().replace("\\", "/")
    if not s or len(s) > _PREFIX_MAX_LEN:
        return None
    if s.startswith("/"):
        return None
    parts = s.split("/")
    if any(p == ".." for p in parts):
        return None
    cleaned_parts = [_sanitize_segment(p) for p in parts if p]
    cleaned_parts = [p for p in cleaned_parts if p]
    if not cleaned_parts:
        return None
    result = "/".join(cleaned_parts)
    if len(result) > _PREFIX_OUTPUT_MAX:
        result = result[:_PREFIX_OUTPUT_MAX].rstrip("/_-")
        if not result:
            return None
    return result


# ---- arbitrary-folder saving (Save Image Reaper) ----

def _resolve_save_folder(raw):
    """Resolve the user's folder field to an absolute directory path.

    Empty -> ComfyUI's output directory. Env vars (%USERPROFILE%, $HOME) and
    '~' are expanded; surrounding quotes are stripped (Explorer's "Copy as
    path" pastes them). A RELATIVE path is treated as a subfolder of the
    output directory. Returns (abs_path, inside_output) where inside_output
    is True when the resolved folder sits under output/ (so callers can emit
    ui.images for the Assets panel and serve previews via /view).

    folder_paths is imported lazily so this module stays importable in
    unit-test environments without ComfyUI.
    """
    import folder_paths
    out_dir = os.path.realpath(folder_paths.get_output_directory())
    # tolerate a non-string folder from hand-edited/imported workflow JSON
    s = (raw if isinstance(raw, str) else "").strip().strip('"').strip("'")
    if not s:
        return out_dir, True
    s = os.path.expandvars(os.path.expanduser(s))
    if not os.path.isabs(s):
        s = os.path.join(out_dir, s)
    real = os.path.realpath(s)
    try:
        inside = os.path.commonpath([real, out_dir]) == out_dir
    except ValueError:  # different drives on Windows
        inside = False
    return real, inside


_COUNTER_TOKEN = "%counter%"


def _next_counter(dir_path, name_template):
    """Next %counter% value for name_template inside dir_path (max found + 1).

    name_template is a FINAL file name (extension included) with %counter%
    still in it, everything else already resolved. Scan is case-insensitive
    (Windows filesystems are). Missing/unreadable dir or no token -> 1.
    Files are never overwritten: the caller claims the name with O_EXCL and
    bumps on collision, so this is just the fast starting point.
    """
    if _COUNTER_TOKEN not in name_template:
        return 1
    pre, _, post = name_template.partition(_COUNTER_TOKEN)
    post = post.replace(_COUNTER_TOKEN, "")  # collapse accidental repeats
    try:
        names = os.listdir(dir_path)
    except OSError:
        return 1
    rx = re.compile(
        "^" + re.escape(pre) + r"(\d+)" + re.escape(post) + "$", re.IGNORECASE
    )
    mx = 0
    for n in names:
        m = rx.match(n)
        if m:
            try:
                mx = max(mx, int(m.group(1)))
            except ValueError:
                pass
    return mx + 1


# ---- stale-preview stripping ----

def strip_stale_preview(extra, node_type, prop_key):
    """Return a copy of extra_pnginfo with `prop_key` removed from every
    `node_type` node's properties.

    WHY (reported 2026-08-10 against Save Image): ComfyUI freezes the workflow
    into the file at QUEUE time, which is BEFORE that file exists. So the node's
    memory of its last result is still the PREVIOUS run's. Measured on a real
    pair: the workflow inside image_..._001.webp names image_..._001.png, the run
    before it. Drag that file into ComfyUI and the node confidently shows a
    different picture. It corrects itself on the next Run, which is exactly what
    made it look like a glitch rather than a bug.

    Core's own SaveImage shows NOTHING in that situation, so leaving ours to show
    the wrong thing is worse than core. Removing the key just means the node comes
    up empty until the first run.

    Only the EMBEDDED copy loses it. The browser keeps its own
    node.properties[prop_key], which is what a workflow-tab switch restores from,
    and the saved .json workflow is written from the browser too - so both of
    those are untouched and keep working exactly as before.

    ⚠️ MUST COPY, NEVER MUTATE. ComfyUI hands the SAME extra_pnginfo object to
    every node in a run (`extra_data.get('extra_pnginfo')` in execution.py), so
    stripping in place would silently edit what a SECOND save node embeds in its
    own file. That bug would look identical in review and only show up for
    someone with two save nodes.

    Parameterised (2026-08-10) so Save Image and Save Video share ONE copy rather
    than each carrying its own near-identical version.
    """
    if not isinstance(extra, dict):
        return extra
    wf = extra.get("workflow")
    if not isinstance(wf, dict) or not isinstance(wf.get("nodes"), list):
        return extra
    hit = False
    new_nodes = []
    for n in wf["nodes"]:
        if (
            isinstance(n, dict)
            and n.get("type") == node_type
            and isinstance(n.get("properties"), dict)
            and prop_key in n["properties"]
        ):
            n = dict(n)
            n["properties"] = {k: v for k, v in n["properties"].items() if k != prop_key}
            hit = True
        new_nodes.append(n)
    if not hit:
        return extra
    # shallow copies all the way down to the list we changed - enough to leave
    # the caller's object untouched, without deep-copying a whole graph per save
    new_wf = dict(wf)
    new_wf["nodes"] = new_nodes
    new_extra = dict(extra)
    new_extra["workflow"] = new_wf
    return new_extra


# ---- workflow metadata embedding ----

def _build_pnginfo(prompt=None, workflow=None, extra_pnginfo=None, parameters=None):
    """Return a PngInfo object embedding workflow + prompt as tEXt chunks,
    matching the byte format ComfyUI's built-in SaveImage writes.

    Two calling conventions, supported simultaneously:
      Route side (called from JS): pass `prompt=` and `workflow=` (both
        JSON-serialisable dicts from app.graphToPrompt()).
      Node side (called by ComfyUI): pass `prompt=` (PROMPT hidden input)
        and `extra_pnginfo=` (EXTRA_PNGINFO hidden input — a dict whose
        "workflow" key holds the workflow). Each key in extra_pnginfo
        becomes its own tEXt chunk.

    Any argument may be None / missing — its chunk is then skipped.
    Unserialisable extras are silently dropped (best-effort).

    Returns an EMPTY PngInfo when ComfyUI was launched with --disable-metadata.
    This is the single choke point for every Reaper PNG (Save Image, Preview
    Image, and all four /reaper save routes), so gating it here is what makes
    the flag actually hold. Empty rather than None so no caller can trip over a
    missing object; PIL writes no tEXt chunks for an empty PngInfo. If you ever
    add an `add_text` call OUTSIDE this function you have bypassed the flag —
    build it here instead (the harness pins that: `only _save_helpers.py
    constructs a PngInfo`).
    """
    pnginfo = PngInfo()
    if _metadata_disabled():
        return pnginfo
    if prompt is not None:
        try:
            pnginfo.add_text("prompt", json.dumps(_json_safe(prompt)))
        except Exception:
            pass
    if workflow is not None:
        try:
            pnginfo.add_text("workflow", json.dumps(_json_safe(workflow)))
        except Exception:
            pass
    if isinstance(extra_pnginfo, dict):
        for k, v in extra_pnginfo.items():
            try:
                pnginfo.add_text(k, json.dumps(_json_safe(v)))
            except Exception:
                pass
    # A1111-style generation settings, read by Civitai and by every A1111-family
    # tool. Written RAW, NOT json.dumps'd: the value is plain text, and quoting
    # it would make Civitai's parser see a leading quote instead of the prompt.
    # The chunk name must be exactly "parameters" (case sensitive).
    if isinstance(parameters, str) and parameters.strip():
        try:
            pnginfo.add_text("parameters", parameters)
        except Exception:
            pass
    return pnginfo
