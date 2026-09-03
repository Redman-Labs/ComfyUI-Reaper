"""HTTP endpoints used by Reaper frontend save controls."""

import base64
import io as bytes_io
import json
import math
import os
import subprocess
import sys
import threading
import re
import uuid
from pathlib import Path
from typing import Any

import folder_paths
from aiohttp import web
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from server import PromptServer
from spellchecker import SpellChecker

from .resource_monitor import resource_snapshot

from .nodes._helpers._save_helpers import _next_counter, _resolve_save_folder
from .nodes._helpers._lora_helpers import (
    build_lora_info as _lora_build_info,
    file_sha256 as _lora_file_sha256,
    find_preview_path as _lora_find_preview,
    parse_civitai_modelversion as _lora_parse_civitai,
    save_sidecar_cache as _lora_save_sidecar,
    delete_sidecar_cache as _lora_delete_sidecar,
    sanitize_civitai_key as _civitai_sanitize_key,
    mask_civitai_key as _civitai_mask_key,
    civitai_hosts as _civitai_hosts,
    read_civitai_account as _civitai_read_account,
    write_civitai_account as _civitai_write_account,
    get_custom_triggers as _lora_get_custom,
    set_custom_triggers as _lora_set_custom,
    find_custom_preview as _lora_find_custom_preview,
    custom_preview_path as _lora_custom_preview_path,
    custom_preview_version as _lora_custom_preview_version,
    write_custom_preview as _lora_write_custom_preview,
    delete_custom_preview as _lora_delete_custom_preview,
)
from .nodes._helpers._path_guard import (
    comfy_roots as _red_comfy_roots,
    folder_allowed as _red_folder_allowed,
    is_path_under as _is_path_under,
    remember_folder as _red_remember_folder,
    denied_message as _red_denied_message,
    prescreen as _red_prescreen,
    prescreen_folder_field as _red_prescreen_field,
    rel_is_rooted as _red_rel_is_rooted,
    remembered_folders as _red_remembered_folders,
)

_SAVE_DIALOG_LOCK = threading.Lock()
_SPELLCHECKER = SpellChecker(language="en")
_SPELL_WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_REAPER_ASSETS = (Path(__file__).resolve().parent / "assets").resolve()
_I16_MODES = ("I;16", "I;16B", "I;16L", "I;16N")


@PromptServer.instance.routes.get("/reaper/api/asset")
async def serve_reaper_asset(request):
    """Serve a bundled Reaper asset using an extensionless API route."""
    relative = request.query.get("path", "")
    parts = Path(relative.replace("\\", "/")).parts
    if not relative or Path(relative).is_absolute() or ".." in parts:
        return web.Response(status=400)
    candidate = (_REAPER_ASSETS / Path(*parts)).resolve()
    try:
        candidate.relative_to(_REAPER_ASSETS)
    except ValueError:
        return web.Response(status=403)
    if not candidate.is_file():
        return web.Response(status=404)
    return web.FileResponse(candidate)


def _inpaint_asset_path(filename: str) -> Path:
    directory = Path(folder_paths.get_input_directory()) / "reaper"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / filename


def _inpaint_project_id(value: Any) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", str(value or ""))[:96]
    return cleaned or uuid.uuid4().hex


async def _inpaint_payload(request):
    try:
        data = await request.json()
    except Exception:
        return None
    return data if isinstance(data, dict) else None


@PromptServer.instance.routes.post("/reaper/api/inpaint/upload_src")
async def upload_inpaint_source(request):
    data = await _inpaint_payload(request)
    if data is None:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    image = _decode_image(data.get("image", ""))
    if image is None:
        return web.json_response({"error": "Invalid image data"}, status=400)
    filename = f"inpaint_src_{_inpaint_project_id(data.get('project_id'))}.png"
    try:
        image.convert("RGB").save(_inpaint_asset_path(filename), "PNG")
    except Exception as exc:
        return web.json_response({"error": f"Failed to process image: {exc}"}, status=400)
    return web.json_response({"status": "success", "path": f"reaper/{filename}"})


@PromptServer.instance.routes.post("/reaper/api/inpaint/save_mask")
async def save_inpaint_mask(request):
    data = await _inpaint_payload(request)
    if data is None:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    image = _decode_image(data.get("mask", ""))
    if image is None:
        return web.json_response({"error": "Invalid mask data"}, status=400)
    filename = f"inpaint_mask_{_inpaint_project_id(data.get('project_id'))}.png"
    try:
        image.convert("L").save(_inpaint_asset_path(filename), "PNG")
    except Exception as exc:
        return web.json_response({"error": f"Failed to process mask: {exc}"}, status=400)
    return web.json_response({"status": "success", "path": f"reaper/{filename}"})


@PromptServer.instance.routes.post("/reaper/api/spellcheck")
async def spellcheck_text(request):
    """Return character ranges for misspelled English words."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)
    text = data.get("text", "")
    if not isinstance(text, str):
        return web.json_response({"error": "text must be a string"}, status=400)
    # Keep the request bounded so a malformed client cannot monopolize the
    # server with an arbitrarily large dictionary lookup.
    text = text[:200_000]
    tokens = []
    normalized = []
    for match in _SPELL_WORD_RE.finditer(text):
        word = match.group(0)
        candidate = word.lower().replace("’", "'")
        if len(candidate) <= 1 or word.isupper():
            continue
        tokens.append((match.start(), match.end(), word, candidate))
        normalized.append(candidate)
    unknown = _SPELLCHECKER.unknown(normalized)
    errors = [
        {"start": start, "end": end, "word": word}
        for start, end, word, candidate in tokens
        if candidate in unknown
    ]
    return web.json_response({"errors": errors})


def _native_save_folder_dialog(start: str) -> str:
    if not _SAVE_DIALOG_LOCK.acquire(blocking=False):
        return ""
    try:
        # ComfyUI's embedded Python does not include tkinter. Use the native
        # Windows Forms picker owned by an invisible topmost window so it opens
        # in front of the browser instead of behind it.
        if sys.platform == "win32":
            script = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                "$r='';"
                "$o=New-Object System.Windows.Forms.Form;"
                "$o.TopMost=$true;$o.ShowInTaskbar=$false;$o.FormBorderStyle='None';"
                "$o.Width=1;$o.Height=1;$o.Opacity=0;$o.StartPosition='CenterScreen';"
                "$o.Add_Shown({$o.Activate();"
                "$d=New-Object System.Windows.Forms.FolderBrowserDialog;"
                "$d.Description='Choose a folder for saved images';"
                "$d.ShowNewFolderButton=$true;"
                "if($env:REAPER_SAVE_START){try{$d.SelectedPath=$env:REAPER_SAVE_START}catch{}};"
                "if($d.ShowDialog($o) -eq [System.Windows.Forms.DialogResult]::OK)"
                "{$script:r=$d.SelectedPath};$o.Close()});"
                "[void]$o.ShowDialog();[Console]::Out.Write($r)"
            )
            environment = dict(os.environ)
            environment["REAPER_SAVE_START"] = (
                start if start and os.path.isdir(start) else folder_paths.get_output_directory()
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", script],
                capture_output=True,
                text=True,
                timeout=300,
                env=environment,
                creationflags=0x08000000,
            )
            return (result.stdout or "").strip()

        if sys.platform == "darwin":
            result = subprocess.run(
                ["osascript", "-e", 'POSIX path of (choose folder with prompt "Choose a folder for saved images")'],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return (result.stdout or "").strip().rstrip("/") if result.returncode == 0 else ""

        result = subprocess.run(
            ["zenity", "--file-selection", "--directory", "--title=Choose a folder for saved images"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return (result.stdout or "").strip() if result.returncode == 0 else ""
    finally:
        _SAVE_DIALOG_LOCK.release()


def _decode_image(data_uri: str) -> Image.Image | None:
    try:
        encoded = data_uri.split(",", 1)[1] if "," in data_uri else data_uri
        image = Image.open(bytes_io.BytesIO(base64.b64decode(encoded)))
        image.load()
        return image
    except Exception:
        return None


@PromptServer.instance.routes.get("/reaper/api/resources")
async def get_resource_snapshot(_request):
    """Return live host/GPU statistics for the Reaper menu monitor."""
    try:
        return web.json_response(resource_snapshot())
    except Exception as error:
        return web.json_response(
            {"available": False, "error": f"resource monitor failed: {error}"},
            status=500,
        )


def _safe_prefix(value: Any) -> str:
    if not isinstance(value, str):
        return "PauseImage"
    value = value.strip().replace("\\", "/").lstrip("/")
    parts = []
    for part in value.split("/"):
        part = "".join(
            "_" if character in '<>:"|?*' or ord(character) < 32 else character
            for character in part
        ).strip(" ._")
        if part and part != "..":
            parts.append(part)
    return "/".join(parts)[:100] or "PauseImage"


def _json_safe(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _pnginfo(prompt: Any, workflow: Any) -> PngInfo:
    info = PngInfo()
    if prompt is not None:
        info.add_text("prompt", json.dumps(_json_safe(prompt), allow_nan=False))
    if workflow is not None:
        info.add_text(
            "workflow",
            json.dumps(_json_safe(workflow), allow_nan=False),
        )
    return info


@PromptServer.instance.routes.post("/reaper/api/preview/save")
async def save_pause_image(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)

    image = _decode_image(data.get("image_b64", ""))
    if image is None:
        return web.json_response({"error": "invalid image data"}, status=400)

    prefix = _safe_prefix(data.get("filename_prefix", "PauseImage"))
    try:
        output_directory = folder_paths.get_output_directory()
        folder, name, counter, subfolder, _ = folder_paths.get_save_image_path(
            prefix,
            output_directory,
            image.width,
            image.height,
        )
        os.makedirs(folder, exist_ok=True)
        filename = f"{name}_{counter:05}_.png"
        image.save(
            os.path.join(folder, filename),
            "PNG",
            pnginfo=_pnginfo(data.get("prompt"), data.get("workflow")),
        )
    except Exception as error:
        return web.json_response(
            {"error": f"save failed: {error}"},
            status=500,
        )

    return web.json_response(
        {
            "status": "success",
            "filename": filename,
            "subfolder": subfolder,
        }
    )


@PromptServer.instance.routes.post("/reaper/api/preview/prepare")
async def prepare_pause_image(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)

    image = _decode_image(data.get("image_b64", ""))
    if image is None:
        return web.json_response({"error": "invalid image data"}, status=400)

    prefix = _safe_prefix(data.get("filename_prefix", "PauseImage"))
    try:
        buffer = bytes_io.BytesIO()
        image.save(
            buffer,
            "PNG",
            pnginfo=_pnginfo(data.get("prompt"), data.get("workflow")),
        )
        output_directory = folder_paths.get_output_directory()
        _, name, counter, _, _ = folder_paths.get_save_image_path(
            prefix,
            output_directory,
            image.width,
            image.height,
        )
        suggested_filename = f"{name}_{counter:05}_.png"
    except Exception as error:
        return web.json_response(
            {"error": f"prepare failed: {error}"},
            status=500,
        )

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return web.json_response(
        {
            "image_b64": f"data:image/png;base64,{encoded}",
            "suggested_filename": suggested_filename,
        }
    )

@PromptServer.instance.routes.get("/reaper/api/save_image/pick_native")
async def save_image_pick_native(request):
    """Open the native folder picker and remember the human-approved folder."""
    import asyncio

    start = str(request.query.get("path", "") or "")
    if not (_red_prescreen_field(start) and _red_folder_allowed(start)):
        start = ""
    try:
        loop = asyncio.get_running_loop()
        path = await loop.run_in_executor(None, _native_save_folder_dialog, start)
        if path and os.path.isdir(path):
            remembered = _red_remember_folder(path)
            return web.json_response({"ok": True, "path": path, "remembered": bool(remembered)})
        return web.json_response({"ok": False, "cancelled": True})
    except Exception as error:
        return web.json_response({"ok": False, "message": str(error)})

@PromptServer.instance.routes.get("/reaper/api/save_image/file")
async def api_save_image_file(request):
    """Serve a file this server session just saved, looked up by an opaque
    token (exact-path registry in node_save_image, filled ONLY by the save
    node itself). No path arrives from the client, so there is no traversal
    surface. Powers the node's preview for files saved outside ComfyUI's
    folders, which /view cannot reach. Read-only; tokens die with the
    server process."""
    from .nodes.node_save_image import resolve_serve_token
    path = resolve_serve_token(request.query.get("t", ""))
    if not path or not os.path.isfile(path):
        return web.Response(status=404, text="unknown or expired preview token")
    # State the image type ourselves instead of leaving it to the platform's
    # mimetype table. MEASURED 2026-08-10 on this box: the same route answered
    # image/png for a .png and application/octet-stream for a .webp, even
    # though this Python's own mimetypes module knows .webp perfectly well. The
    # <img> preview survives either way because browsers sniff images, but the
    # node's "Open" button does window.open on this URL, and octet-stream makes
    # the browser DOWNLOAD the file instead of showing it.
    _CT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    ct = _CT.get(os.path.splitext(path)[1].lower())
    return web.FileResponse(path, headers={"Content-Type": ct} if ct else None)

@PromptServer.instance.routes.get("/reaper/api/save_image/next_counter")
async def api_save_image_next_counter(request):
    """Next %counter% value for the node's live 'Will save as' preview.

    `name` is the resolved filename template (extension included, %counter%
    still in it, may contain '/' subfolder segments - the JS resolves dates /
    input / node-reference tokens before calling). `folder` is the raw folder
    field, resolved exactly like the node resolves it at save time. A folder
    that doesn't exist yet just means counter 1. Directory scan runs in an
    executor so a huge folder can't stall other requests.
    """
    folder_raw = request.query.get("folder", "")
    name = request.query.get("name", "")
    try:
        digits = max(1, min(8, int(request.query.get("digits", "3"))))
    except Exception:
        digits = 3

    def _scan():
        # Screen the string that will ACTUALLY be resolved: _resolve_save_folder
        # expands %VARS% and ~ BEFORE realpath, so a raw-only screen judges a
        # different value than the one that reaches the filesystem (round-3 #4).
        # Still entirely pre-resolve - expandvars/expanduser touch nothing.
        if not _red_prescreen_field(folder_raw):
            return 1, "", True
        base, _inside = _resolve_save_folder(folder_raw)
        # Containment (2026-08-03). Without this the preview was a directory
        # read-oracle on ANY path: _resolve_save_folder deliberately accepts an
        # absolute folder, and _next_counter lists it. It returns no bytes, but
        # the max-match it reports leaks whether files exist anywhere on disk.
        # The refusal returns a CONSTANT (1, "") so nothing about the folder -
        # not even whether it exists - can be inferred from the answer, and a
        # `denied` flag so the node's preview can say so instead of quietly
        # showing a number that a Run would never produce.
        if not _red_folder_allowed(base):
            return 1, "", True
        parts = [p for p in name.replace("\\", "/").split("/") if p]
        if not parts:
            return 1, "", False
        # Mirror the save-time order (node_save_image.py): %counter% in a
        # FOLDER segment resolves against existing sibling dirs FIRST, then
        # the FILE counter scans inside that resolved directory - so the
        # preview shows the exact path a Run would create.
        resolved_dirs = []
        parent = base
        for seg in parts[:-1]:
            if "%counter%" in seg:
                n = _next_counter(parent, seg)
                seg = seg.replace("%counter%", f"{n:0{digits}}")
            resolved_dirs.append(seg)
            parent = os.path.join(parent, seg)
        counter = _next_counter(parent, parts[-1])
        fname = parts[-1].replace("%counter%", f"{counter:0{digits}}")
        return counter, "/".join(resolved_dirs + [fname]), False

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        counter, resolved, denied = await loop.run_in_executor(None, _scan)
        out = {"ok": True, "counter": counter, "resolved": resolved}
        if denied:
            out["denied"] = True
            out["message"] = _red_denied_message(str(folder_raw))
        return web.json_response(out)
    except Exception as e:
        return web.json_response(
            {"ok": False, "message": str(e), "counter": 1, "resolved": ""}
        )


@PromptServer.instance.routes.post("/reaper/api/save_image/open_folder")
async def api_save_image_open_folder(request):
    """Open the OS file explorer at the node's save folder, IF that folder is
    approved. Local-install QoL; the path is resolved the same way the save
    does and must already exist as a directory.

    Containment added 2026-08-03 (ComfyUI-Manager PR #3118). This route is
    unauthenticated and was handing any absolute path to os.startfile /
    xdg-open, so any web page could pop file-manager windows on the user's
    desktop. Worse on Windows: a UNC path like \\\\attacker\\share makes the
    os.path.isdir check ALONE reach out over SMB and leak an NTLM hash, before
    startfile is even called - so the check has to come BEFORE the isdir, not
    just before the launch. The sibling /workflows/reveal route already did
    this correctly; this one is now consistent with it."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    folder_raw = str(data.get("folder", "") or "")
    if not _red_prescreen_field(folder_raw):    # expansion-aware, see round-3 #4
        return web.json_response(
            {"ok": False, "message": _red_denied_message(folder_raw), "denied": True}
        )
    path, _inside = _resolve_save_folder(folder_raw)
    if not _red_folder_allowed(path):
        return web.json_response({"ok": False, "message": _red_denied_message(path), "denied": True})
    if not os.path.isdir(path):
        return web.json_response({
            "ok": False,
            "message": "Folder does not exist yet - it is created on the first save.",
        })
    try:
        import subprocess
        import sys
        if sys.platform == "win32":
            # Plain open ONLY. The window may land behind the browser (the JS
            # status line says to check the taskbar). Do NOT re-add the
            # PowerShell bring-to-front script: its Add-Type + user32.dll
            # P/Invoke command line is flagged by Bitdefender as "Malicious
            # command line detected" and BLOCKED (real user report,
            # 2026-07-03) - antivirus heuristics can't tell it apart from
            # injector malware. os.startfile is a normal API call and safe.
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "message": str(e)})

# ── Load Images from Folder Reaper ─────────────────────────────────────────
# These routes back the node's gallery + thumbnails. They read the user's OWN
# chosen folder on the local machine (the whole point of the node), so they are
# NOT constrained to input/. They are read-only, validate the path is a real
# directory, only touch image files, and guard the per-file thumbnail against
# path-traversal out of the chosen folder via _is_path_under.
_LIF_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif")


def _lif_is_image(name: str) -> bool:
    return name.lower().endswith(_LIF_IMAGE_EXTS)


def _lif_list_files(real, recursive):
    """Walk a folder and return its image files. Blocking (os.walk + os.stat on
    a big tree can take seconds) - run off the event loop."""
    files = []
    if recursive:
        for root, _dirs, names in os.walk(real):
            for n in names:
                if not _lif_is_image(n):
                    continue
                full = os.path.join(root, n)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                rel = os.path.relpath(full, real).replace("\\", "/")
                files.append({"file": rel, "name": n, "size": st.st_size, "mtime": st.st_mtime})
    else:
        for n in os.listdir(real):
            full = os.path.join(real, n)
            if os.path.isfile(full) and _lif_is_image(n):
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                files.append({"file": n, "name": n, "size": st.st_size, "mtime": st.st_mtime})
    return files


@PromptServer.instance.routes.get("/reaper/api/load_images_folder/list")
async def api_lif_list(request):
    """List image files in a folder. ?path=<folder>&recursive=0|1
    Returns {ok, folder, files:[{file, name, size, mtime}]} (file = path
    relative to the folder, forward-slashed)."""
    # no-store on every branch: the gallery re-lists on each open, and a browser
    # heuristically caching this JSON would serve a stale folder (same hardening
    # as the LoRA list route).
    hdrs = {"Cache-Control": "no-store"}
    folder = request.query.get("path", "")
    recursive = request.query.get("recursive", "0") == "1"
    # prescreen BEFORE isdir: on Windows, isdir on \\host\share alone opens an
    # SMB connection and leaks an NTLM hash, so a UNC value must be judged
    # lexically before any filesystem call touches it.
    if not _red_prescreen(folder):
        return web.json_response(
            {"ok": False, "message": _red_denied_message(folder), "denied": True, "files": []},
            headers=hdrs,
        )
    # Containment (2026-08-03, ComfyUI-Manager PR #3118). This route is
    # unauthenticated, so without this `?path=C:\&recursive=1` enumerated every
    # image on the host and /thumb then served them back as JPEG bytes.
    # BEFORE isdir, not after: answering "Folder not found" for an absent path
    # and "not approved" for a present one is a directory-existence oracle for
    # the whole disk. next_counter already returns a constant for exactly this
    # reason; these three routes contradicted it until the round-3 review.
    if not _red_folder_allowed(folder):
        return web.json_response(
            {"ok": False, "message": _red_denied_message(folder), "denied": True, "files": []},
            headers=hdrs,
        )
    if not folder or not os.path.isdir(folder):
        return web.json_response({"ok": False, "message": "Folder not found.", "files": []}, headers=hdrs)
    real = os.path.realpath(folder)
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        files = await loop.run_in_executor(None, _lif_list_files, real, recursive)
    except Exception as e:
        return web.json_response({"ok": False, "message": f"Could not read folder: {e}", "files": []}, headers=hdrs)
    return web.json_response({"ok": True, "folder": real, "files": files}, headers=hdrs)


def _lif_make_thumb(full):
    """Decode + downscale one image to a small JPEG. Blocking - run off the loop.

    The bit-depth branches MUST match nodes/_load_images_folder.py::_load_one
    exactly. This is the gallery the user hand-picks images in, so a thumbnail
    that disagrees with what the node will actually load is worse than a wrong
    thumbnail on its own: they are choosing from pictures that do not describe
    the output. A 16-bit greyscale file measured 253.98 (4 unique values) here
    against the loader's correct 127.66 - i.e. a white square. See
    .claude/patterns/load-image.md #21 for why convert CLAMPS and why the
    .convert("I") is required before .point().
    """
    from PIL import ImageOps
    im = Image.open(full)
    im = ImageOps.exif_transpose(im)
    if im.mode == "I":
        im = im.point(lambda px: px * (1 / 255))
    elif im.mode in _I16_MODES:
        im = im.convert("I").point(lambda px: px * (1 / 257))
    im = im.convert("RGB")
    im.thumbnail((192, 192))
    buf = bytes_io.BytesIO()
    im.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


@PromptServer.instance.routes.get("/reaper/api/load_images_folder/thumb")
async def api_lif_thumb(request):
    """Serve a small JPEG thumbnail for one image. ?path=<folder>&file=<rel>"""
    folder = request.query.get("path", "")
    rel = request.query.get("file", "")
    if not _red_prescreen(folder):      # before isdir - see the list route
        return web.Response(status=403)
    # The _is_path_under below only proves the file sits inside the folder the
    # CALLER named, which is no containment at all while `folder` is arbitrary
    # (2026-08-03, ComfyUI-Manager PR #3118: this served any image-extension
    # file on the host back as a JPEG). Root the folder first, then keep the
    # existing per-file check so `rel` still cannot climb out of it.
    # Ordered BEFORE isdir so 403-vs-404 is not an existence oracle (round-3).
    if not _red_folder_allowed(folder):
        return web.Response(status=403)
    # `rel` is attacker-controlled too, and os.path.join DISCARDS `folder` when
    # rel is absolute/UNC - so realpath would fire SMB before the check below.
    if _red_rel_is_rooted(rel):
        return web.Response(status=403)
    if not folder or not rel or not os.path.isdir(folder):
        return web.Response(status=404)
    full = os.path.realpath(os.path.join(folder, rel))
    if (
        not _is_path_under(full, folder)
        or not os.path.isfile(full)
        or not _lif_is_image(os.path.basename(full))
    ):
        return web.Response(status=403)
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        # PIL decode/resize/encode can be slow for big images - keep it off the
        # aiohttp event loop so other ComfyUI requests don't stall.
        body = await loop.run_in_executor(None, _lif_make_thumb, full)
        return web.Response(
            body=body,
            content_type="image/jpeg",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception:
        return web.Response(status=404)


@PromptServer.instance.routes.get("/reaper/api/load_images_folder/browse")
async def api_lif_browse(request):
    """Navigate the server filesystem for the in-app folder picker, WITHIN the
    approved folders only. ?path=<dir> (empty = list the approved roots).
    Returns {ok, path, parent, dirs:[{name, path, images}]}; images = -1 means
    'not counted' (skipped for folders with many sub-folders, to stay fast).

    Containment added 2026-08-03 (ComfyUI-Manager PR #3118): this used to walk
    anything, so an unauthenticated caller could map the whole disk (and reach
    UNC paths, which on Windows leaks an NTLM hash just by being stat'd).

    The empty-path branch used to enumerate drive letters; it now lists the
    approved roots instead. That is both the containment AND a better landing
    screen - the user sees "output", "D:\\MyArt" rather than every drive. To add
    somewhere new they use the Browse button, which opens the real OS dialog and
    approves whatever they pick (see nodes/_path_guard)."""
    path = request.query.get("path", "")
    try:
        if not path:
            dirs = []
            seen = set()
            for d in list(_red_comfy_roots()) + list(_red_remembered_folders()):
                try:
                    if not d or not os.path.isdir(d):
                        continue
                    key = os.path.normcase(os.path.realpath(d))
                    if key in seen:
                        continue
                    seen.add(key)
                except OSError:
                    continue
                dirs.append({"name": os.path.basename(d.rstrip("\\/")) or d,
                             "path": d, "images": -1})
            return web.json_response({"ok": True, "path": "", "parent": None, "dirs": dirs})

        if not _red_prescreen(path):    # before isdir - see the list route
            return web.json_response(
                {"ok": False, "message": _red_denied_message(path), "denied": True, "dirs": []}
            )
        # allowed-check BEFORE isdir, so the reply cannot distinguish "absent"
        # from "present but not yours" for any path on the disk (round-3).
        if not _red_folder_allowed(path):
            return web.json_response(
                {"ok": False, "message": _red_denied_message(path), "denied": True, "dirs": []}
            )
        if not os.path.isdir(path):
            return web.json_response({"ok": False, "message": "Folder not found.", "dirs": []})
        real = os.path.realpath(path)
        parent = os.path.dirname(real)
        if parent == real:  # already at a drive / filesystem root
            parent = ""
        # Do not offer an "up" that would just be refused: once we are at the
        # top of an approved root, Up returns to the roots list ("") instead.
        if parent and not _red_folder_allowed(parent):
            parent = ""

        subdirs = []
        try:
            for n in sorted(os.listdir(real), key=str.lower):
                full = os.path.join(real, n)
                if os.path.isdir(full):
                    subdirs.append((n, full))
        except OSError as e:
            return web.json_response({"ok": False, "message": f"Could not read folder: {e}", "dirs": []})

        # Only tally per-folder image counts when cheap (few sub-folders), so
        # browsing into e.g. C:\Windows doesn't stat hundreds of directories.
        do_count = len(subdirs) <= 60
        dirs = []
        for n, full in subdirs:
            cnt = -1
            if do_count:
                try:
                    cnt = sum(1 for fn in os.listdir(full) if _lif_is_image(fn))
                except OSError:
                    cnt = -1
            dirs.append({"name": n, "path": full, "images": cnt})
        return web.json_response({"ok": True, "path": real, "parent": parent, "dirs": dirs})
    except Exception as e:
        return web.json_response({"ok": False, "message": str(e), "dirs": []})


# Native OS folder picker. The ComfyUI server runs on the user's own machine for
# local installs, so it can pop a REAL folder dialog and return the chosen path -
# no image copying, like a desktop app. Cross-platform with NO extra Python deps:
# Windows = PowerShell + WinForms (the embedded Python lacks tkinter); macOS =
# osascript; Linux = zenity / kdialog. Each fails fast on a headless/remote host
# so the frontend falls back to the in-app browser. Never hangs (subprocess
# timeout); a module lock allows only one dialog at a time.
import threading as _threading

_LIF_DIALOG_LOCK = _threading.Lock()


def _lif_dialog_available():
    """True if SOME native folder dialog tool exists for this platform."""
    import sys
    import shutil
    if sys.platform == "win32":
        return shutil.which("powershell") is not None
    if sys.platform == "darwin":
        return shutil.which("osascript") is not None
    return shutil.which("zenity") is not None or shutil.which("kdialog") is not None


def _lif_dialog_windows(start_path):
    import subprocess
    # Show an invisible TopMost owner form, then open the folder dialog inside its
    # Shown event so it inherits the foreground (fixes "opens behind the browser").
    # Start path goes through an env var to avoid quoting issues.
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$r='';"
        "$o=New-Object System.Windows.Forms.Form;"
        "$o.TopMost=$true;$o.ShowInTaskbar=$false;$o.FormBorderStyle='None';"
        "$o.Width=1;$o.Height=1;$o.Opacity=0;$o.StartPosition='CenterScreen';"
        "$o.Add_Shown({"
        "$o.Activate();"
        "$d=New-Object System.Windows.Forms.FolderBrowserDialog;"
        "$d.Description='Choose a folder of images';$d.ShowNewFolderButton=$false;"
        "if($env:LIF_START){try{$d.SelectedPath=$env:LIF_START}catch{}};"
        "if($d.ShowDialog($o) -eq [System.Windows.Forms.DialogResult]::OK){$script:r=$d.SelectedPath};"
        "$o.Close()"
        "});"
        "[void]$o.ShowDialog();"
        "[Console]::Out.Write($r)"
    )
    env = dict(os.environ)
    env["LIF_START"] = start_path or ""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", ps],
        capture_output=True, text=True, timeout=300, env=env,
        creationflags=0x08000000,  # CREATE_NO_WINDOW (no console flash)
    )
    return (out.stdout or "").strip()


def _lif_dialog_macos(start_path):
    import subprocess
    import re
    script = 'POSIX path of (choose folder with prompt "Choose a folder of images")'
    # Only seed the start location when it's a real dir whose path has no chars
    # that could break out of the AppleScript string literal (?path= is supplied
    # by the caller, so treat it as untrusted).
    if start_path and os.path.isdir(start_path) and re.match(r'^[^"\\\x00-\x1f]+$', start_path):
        script = (
            'POSIX path of (choose folder with prompt "Choose a folder of images" '
            f'default location POSIX file "{start_path}")'
        )
    try:
        out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=300)
        return (out.stdout or "").strip().rstrip("/") if out.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _lif_dialog_linux(start_path):
    import shutil
    import subprocess
    start = start_path if (start_path and os.path.isdir(start_path)) else os.path.expanduser("~")
    if shutil.which("zenity"):
        try:
            out = subprocess.run(
                ["zenity", "--file-selection", "--directory",
                 "--title=Choose a folder of images", f"--filename={start}/"],
                capture_output=True, text=True, timeout=300,
            )
            return (out.stdout or "").strip() if out.returncode == 0 else ""
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    if shutil.which("kdialog"):
        try:
            out = subprocess.run(
                ["kdialog", "--getexistingdirectory", start, "--title", "Choose a folder of images"],
                capture_output=True, text=True, timeout=300,
            )
            return (out.stdout or "").strip() if out.returncode == 0 else ""
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return ""


def _lif_native_folder_dialog(start_path=""):
    """Open the native OS folder picker; return the chosen path, "" (cancelled),
    or None (busy - a dialog is already open). Runs in a thread (caller uses
    run_in_executor); only one at a time via the module lock."""
    if not _LIF_DIALOG_LOCK.acquire(blocking=False):
        return None  # a dialog is already open elsewhere -> caller falls back
    try:
        import sys
        if sys.platform == "win32":
            return _lif_dialog_windows(start_path)
        if sys.platform == "darwin":
            return _lif_dialog_macos(start_path)
        return _lif_dialog_linux(start_path)
    except Exception as e:
        print(f"[ReaperLoadImagesFolder] native folder dialog failed: {e}")
        return ""
    finally:
        try:
            _LIF_DIALOG_LOCK.release()
        except Exception:
            pass


@PromptServer.instance.routes.get("/reaper/api/load_images_folder/pick_native")
async def api_lif_pick_native(request):
    """Pop the native OS folder dialog on the ComfyUI host; return the chosen path.
    {ok:true, path} on pick; {ok:false, cancelled} on cancel; {ok:false,
    unavailable} when no native dialog tool exists (so the UI falls back)."""
    if not _lif_dialog_available():
        return web.json_response({"ok": False, "unavailable": True})
    start = request.query.get("path", "")
    # ⚠ THE START PATH MUST ALREADY BE APPROVED. Not merely screened.
    #
    # The whole trust model rests on "an attacker can make this dialog appear
    # but cannot choose the folder". That is FALSE if they control where it
    # opens: `start` becomes $d.SelectedPath (line ~1870) and FolderBrowserDialog
    # RETURNS SelectedPath when the user clicks OK without navigating. So
    #   GET /pick_native?path=\\attacker\drop
    # pops a plausible "Choose a folder of images" box already sitting on the
    # attacker's share, and one OK click allowlists it permanently - after which
    # Save Image can write every render there. `?path=C:\Users\<name>` does the
    # same for the whole home directory.
    #
    # Restricting the start to an already-approved folder costs nothing: the
    # dialog simply opens at its default and the user navigates to the new
    # folder themselves, which is the flow anyway. Both real callers pass either
    # "" or a folder that is already approved.
    # (Round-3 review. The round-2 fix here only screened for UNC, which stopped
    # the credential leak but not the far worse click-to-approve.)
    if not (_red_prescreen(start) and _red_folder_allowed(start)):
        start = ""
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        path = await loop.run_in_executor(None, _lif_native_folder_dialog, start)
        if path is None:
            return web.json_response({"ok": False, "busy": True})
        if path and os.path.isdir(path):
            # THE approval point for the whole allowlist (see nodes/_path_guard).
            # A folder that came back from the native OS dialog was chosen by a
            # human at the keyboard: an attacker can make this dialog APPEAR,
            # but the selection and the OK click happen in the operating system,
            # outside anything a request can influence. That is the only
            # authorisation signal available to us, so this is the ONLY place
            # allowed to call remember_folder. Do not call it from a route that
            # takes the folder from the request body - that would let an
            # attacker approve their own target and make the guard decorative.
            # Surface whether it actually persisted. If the write fails (read-only
            # user dir, AV lock, or a damaged config we refuse to clobber) and we
            # still answer plain ok, the node stores the folder, every Run then
            # says "click Browse and pick this folder once" - which they just did
            # - and there is no way out. Round-3 review finding 5.
            remembered = _red_remember_folder(path)
            return web.json_response({"ok": True, "path": path, "remembered": bool(remembered)})
        return web.json_response({"ok": False, "cancelled": True})
    except Exception as e:
        return web.json_response({"ok": False, "message": str(e)})

def _looks_like_image(data):
    if not isinstance(data, (bytes, bytearray)):
        return False
    data = bytes(data)
    if data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a", b"BM")):
        return True
    if len(data) < 12:
        return False
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return data[4:8] == b"ftyp" and data[8:12] in (
        b"avif", b"avis", b"heic", b"heix", b"hevc", b"mif1", b"msf1",
    )

_wf_looks_like_image = _looks_like_image
# ── LoRA Loader Reaper ─────────────────────────────────────────────────────
# Back the multi-LoRA loader: the file list, the offline info + trigger-word
# readout, preview thumbnails, and the OPTIONAL (user-clicked) Civitai lookup.
# Everything except /civitai is fully offline. Every route realpath-guards to the
# configured loras directories so a crafted ?name= can't read outside them.

def _lora_dirs():
    try:
        return list(folder_paths.get_folder_paths("loras"))
    except Exception:
        return []


# Civitai API hosts. `.com` is the real home; `.red` is Civitai's UNRESTRICTED
# domain and serves the same API on separate DNS, so it doubles as the backup when
# a network or ISP blocks civitai.com by name (verified 2026-07-25: byte-identical
# response for a public model). Which one is asked FIRST is the user's choice - see
# civitai_hosts() in _lora_helpers.py. `.green` is deliberately absent: its API
# 301-redirects straight back to civitai.com, so it is a redundant hop rather than
# an independent route.


def _civitai_account_file():
    """Where the Civitai key lives: <ComfyUI user dir>/reaper/civitai.json.

    Deliberately OUTSIDE this plugin's folder, which is a git repo - a key sitting
    in the working tree is one `git add -A` away from being published, and a
    Manager reinstall would wipe it. ComfyUI's user directory is the same place
    core keeps its own per-install settings, so it survives updates and is already
    excluded from anything shared."""
    base = None
    try:
        base = folder_paths.get_user_directory()
    except Exception:
        base = None
    if not base:
        # Very old ComfyUI without get_user_directory: fall back to a sibling of
        # this plugin rather than refusing to store anything at all.
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user")
    d = os.path.join(base, "reaper")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return os.path.join(d, "civitai.json")


def _civitai_account():
    return _civitai_read_account(_civitai_account_file())


def _civitai_public_account(acc):
    """The ONLY shape the browser is ever given. The key itself never leaves the
    server: `configured` says whether there is one and `hint` shows its last four
    characters so the user can tell which key is loaded."""
    return {
        "ok": True,
        "configured": bool(acc.get("key")),
        "hint": _civitai_mask_key(acc.get("key")),
        "host": acc.get("host", "com"),
        "adultThumbs": bool(acc.get("adult_thumbs")),
    }


@PromptServer.instance.routes.get("/reaper/api/civitai/account")
async def api_civitai_account_get(request):
    """Whether a key is configured, and the two lookup preferences. Never the key."""
    return web.json_response(_civitai_public_account(_civitai_account()),
                             headers={"Cache-Control": "no-store"})


@PromptServer.instance.routes.post("/reaper/api/civitai/account")
async def api_civitai_account_set(request):
    """Set the key and/or the preferences. An absent field is left alone; `key: ""`
    clears the key. Answers with the same public shape, so the panel repaints from
    what the server actually stored rather than from what it hoped it sent."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    acc = _civitai_account()
    if "key" in body:
        raw = body.get("key")
        if isinstance(raw, str) and raw.strip() == "":
            acc["key"] = ""
        else:
            k = _civitai_sanitize_key(raw)
            if not k:
                return web.json_response({
                    "ok": False,
                    "message": "That does not look like an API key - it should be one "
                               "run of ordinary characters with no spaces.",
                }, headers={"Cache-Control": "no-store"})
            acc["key"] = k
    if body.get("host") in ("com", "red"):
        acc["host"] = body["host"]
    if "adultThumbs" in body:
        acc["adult_thumbs"] = bool(body.get("adultThumbs"))
    if not _civitai_write_account(_civitai_account_file(), acc):
        return web.json_response({"ok": False, "message": "Could not save the settings file."},
                                 headers={"Cache-Control": "no-store"})
    return web.json_response(_civitai_public_account(acc), headers={"Cache-Control": "no-store"})


def _resolve_lora_path(name):
    """Resolve a LoRA filename (as listed, incl. any subfolder) to a real path that
    is guaranteed to live inside a configured loras directory, or None."""
    if not name or not isinstance(name, str):
        return None
    try:
        p = folder_paths.get_full_path("loras", name)
    except Exception:
        p = None
    if not p or not os.path.isfile(p):
        return None
    # Fail CLOSED: if the loras dirs can't be determined (empty / folder_paths error),
    # refuse rather than serve an unverified path.
    roots = _lora_dirs()
    if not roots or not _is_path_under(p, *roots):
        return None
    return p


@PromptServer.instance.routes.get("/reaper/api/lora/list")
async def api_lora_list(request):
    """Every LoRA filename ComfyUI knows about (names include any subfolder prefix)."""
    # no-store: this JSON carries no cache headers otherwise, and a browser
    # heuristically caching it reproduces "renamed file never appears" even
    # after our JS re-fetches. Same class as the .mjs no-cache layers above.
    hdrs = {"Cache-Control": "no-store"}
    try:
        files = list(folder_paths.get_filename_list("loras"))
    except Exception:
        # A SCAN FAILURE is not an empty folder: the frontend treats a clean []
        # as ground truth and would mark every row "missing" (a workflow-wide
        # false alarm on a transient network-drive/locked-file hiccup). Say so.
        return web.json_response({"loras": [], "error": True}, headers=hdrs)
    return web.json_response({"loras": files}, headers=hdrs)


@PromptServer.instance.routes.get("/reaper/api/lora/info")
async def api_lora_info(request):
    """Offline info + trigger words for one LoRA (the info panel). Always 200 so the
    frontend never branches on HTTP status; reads only the file header + sidecars."""
    name = request.query.get("name", "")
    path = _resolve_lora_path(name)
    if not path:
        return web.json_response({"ok": False, "message": "LoRA not found."})
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        # Header read is small but hashing/sidecar I/O is disk-bound - keep it off
        # the aiohttp event loop.
        info = await loop.run_in_executor(None, _lora_build_info, path)
    except Exception as exc:
        return web.json_response({"ok": False, "message": "Could not read: {}".format(exc)})
    # The user's own words ride along with the file's and Civitai's, so the panel
    # gets all three sources in one request and can show them the moment it opens.
    try:
        info["custom_triggers"] = _lora_get_custom(_lora_custom_file(), name)
    except Exception:
        info["custom_triggers"] = []
    # ...and so does their own preview picture. `custom_preview` drives the panel's
    # "remove" affordance; `preview_v` is the mtime that lets the browser past the
    # thumb route's hour-long cache when the picture was replaced somewhere else
    # (another node, another session) and this panel never saw it happen.
    try:
        folder = _lora_previews_dir()
        info["preview_v"] = _lora_custom_preview_version(folder, name)
        info["custom_preview"] = bool(info["preview_v"])
        if info["custom_preview"]:
            info["has_preview"] = True
    except Exception:
        info["custom_preview"] = False
        info["preview_v"] = 0
    # no-store: this answer now CARRIES the cache-buster (`preview_v`) that the
    # thumbnail URL is built from, so a heuristically cached copy would hand back
    # a stale version and defeat the very mechanism it exists for. aiohttp's
    # json_response sends no cache headers of its own - the same absent-headers
    # class that got our .mjs modules cached, and why /lora/list already says this.
    return web.json_response({"ok": True, "info": info}, headers={"Cache-Control": "no-store"})


@PromptServer.instance.routes.get("/reaper/api/lora/thumb")
async def api_lora_thumb(request):
    """Serve the LoRA's preview image, or 404.

    The user's OWN picture wins over the one beside the LoRA: this route is what
    both the panel and any future thumbnail read, so the override has to be
    honoured here rather than only where it happens to be displayed."""
    name = request.query.get("name", "")
    path = _resolve_lora_path(name)
    if not path:
        return web.Response(status=404)
    try:
        # Gated like the write and the delete: this hands bytes back to the
        # browser, so the same one guard decides what counts as ours.
        own = _lora_find_custom_preview(_lora_previews_dir(), name)
        if own and not _lora_preview_path_checked(name):
            own = None
    except Exception:
        own = None
    if own:
        return web.FileResponse(own, headers={"Cache-Control": "public, max-age=3600"})
    prev = _lora_find_preview(path)
    roots = _lora_dirs()
    if not prev or not roots or not _is_path_under(prev, *roots):
        return web.Response(status=404)
    return web.FileResponse(prev, headers={"Cache-Control": "public, max-age=3600"})


@PromptServer.instance.routes.get("/reaper/api/lora/civitai")
async def api_lora_civitai(request):
    """OPTIONAL online lookup (only when the user clicks the Civitai button).

    Fingerprints the file (SHA256), asks Civitai for an exact-file match, and caches
    the raw response next to the LoRA so future reads are instant and offline. Always
    200; `reason` tells the frontend which card to show: found / notfound / offline.
    """
    name = request.query.get("name", "")
    path = _resolve_lora_path(name)
    if not path:
        return web.json_response({"ok": False, "reason": "notfound", "message": "LoRA not found."})
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        sha = await loop.run_in_executor(None, _lora_file_sha256, path)
    except Exception as exc:
        return web.json_response({"ok": False, "reason": "offline",
                                  "message": "Could not read the file: {}".format(exc)})
    try:
        import aiohttp
    except Exception:
        return web.json_response({"ok": False, "reason": "offline",
                                  "message": "Could not reach Civitai."})
    # 30s, not 12s: Civitai's API is regularly slow under load, and a lookup that
    # gives up early reads to the user as "it doesn't work", especially on a slow
    # link. The hash is already computed by this point, so this budget is purely
    # the HTTP round trip.
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    acc = _civitai_account()
    hosts = _civitai_hosts(acc.get("host"))
    # `Accept`: an edge that sees no explicit Accept can answer with an HTML
    # challenge page instead of the API; asking for JSON makes the intent
    # unambiguous. `Accept-Encoding` is pinned to what CPython can always decode:
    # aiohttp only advertises `br` when the brotli codec is importable
    # (`_gen_default_accept_encoding`), so on a stock install this is ALREADY the
    # effective value - measured, gzip/deflate, and Civitai returned no
    # compression at all - but pinning it means an install that happens to carry
    # brotli cannot be handed a `br` body by an edge and then fail to decode it.
    #
    # We deliberately do NOT send a browser User-Agent. It was suggested as a way
    # past Cloudflare, but measured against both hosts it changed nothing, and
    # impersonating Chrome to get through bot protection is not something this
    # plugin should do. The API key likewise stays in the Authorization header
    # and is NEVER put in the query string: a `?token=` lands in proxy and server
    # logs, which is the whole reason invariant 16 keeps it out of URLs.
    headers = {
        "User-Agent": "ComfyUI-Reaper",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }
    if acc.get("key"):
        # Sanitised on the way in AND on the way out of the file, so this cannot
        # carry a newline into the header. Never logged, never echoed to the page.
        headers["Authorization"] = "Bearer {}".format(acc["key"])
    data = None
    last_note = "Could not reach Civitai."
    # A refusal aimed at the KEY is the most actionable thing we can report, so it is
    # kept aside rather than being overwritten by whatever the second host happens to
    # say afterwards (a timeout there would otherwise bury it).
    key_note = None
    for i, host in enumerate(hosts):
        last = i == len(hosts) - 1
        url = "https://{}/api/v1/model-versions/by-hash/{}".format(host, sha)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 404:
                        # A 404 is only definitive on the LAST host. It used to end the
                        # search immediately, on the reasoning that both hosts serve one
                        # catalogue - true for a public model, but NOT for an adult-rated
                        # one: the main host hides it behind exactly this 404 while the
                        # unrestricted host returns it. That made a whole class of LoRAs
                        # report "not on Civitai" no matter how many times you asked.
                        # Costs one extra round trip in the genuinely-absent case, on a
                        # lookup the user clicked and which already spent longer hashing.
                        if not last:
                            last_note = "Not found on {}.".format(host)
                            continue
                        return web.json_response({"ok": True, "found": False, "reason": "notfound"})
                    if resp.status in (401, 403):
                        # NEVER returns from inside the loop, exactly like the 404 branch
                        # above. A 401/403 is the most HOST-SPECIFIC failure there is - a
                        # Cloudflare, corporate or ISP block page answers 403 for one
                        # domain while the other domain answers fine - and the backup host
                        # exists for precisely that. Returning here cost the user the
                        # backup, which was a regression against the previous release.
                        #
                        # Having a key saved does NOT make it safe to stop early either: a
                        # 403 does not say it is about the key, so blaming the key would
                        # send someone with a perfectly good one to go and check it while
                        # the host that would have worked was never asked. That is the
                        # same mistake aimed at the people most likely to hit it, since
                        # they are the ones who added a key BECAUSE lookups were failing.
                        if acc.get("key"):
                            key_note = ("Civitai refused the API key ({}). Check it in the node "
                                        "settings.".format(resp.status))
                            last_note = key_note
                        else:
                            # Name the likelier cause FIRST. A network-level block covers
                            # both civitai names, so by the time every host has refused,
                            # "your network" is the better guess than "buy a key".
                            last_note = ("Civitai refused the request ({}). Your network may be "
                                         "blocking Civitai, or this model may need an API key - "
                                         "add one in the node settings.".format(resp.status))
                        continue
                    if resp.status != 200:
                        # Rate limit / maintenance / gateway error: transient, so fall
                        # through to the backup host before giving up.
                        last_note = "Civitai returned {}.".format(resp.status)
                        continue
                    # Captured BEFORE parsing so a non-JSON reply can name what
                    # actually came back.
                    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
                    # Read the WHOLE body, in a loop, with the memory cap kept.
                    #
                    # ⚠️ DO NOT go back to `await resp.content.read(N)` with a POSITIVE
                    # N. That does NOT mean "read up to N bytes of the body" - aiohttp's
                    # StreamReader.read only loops to EOF when n < 0; with a positive n
                    # it waits for the FIRST data to arrive and then returns
                    # `_read_nowait(n)`, which drains only what is buffered AT THAT
                    # MOMENT. On any reply that spans more than one chunk it returns the
                    # first chunk and silently drops the rest, so json.loads fails on
                    # truncated JSON while Content-Type still says application/json -
                    # which is precisely the "Civitai replied with application/json
                    # instead of data" report. Measured: 4096 of 32726 bytes, 5 times out
                    # of 5, against a server chunking at 4KB. It is invisible on a fast
                    # link (the whole reply lands in one buffer), which is why this
                    # survived two rounds of "cannot reproduce" and got misattributed to
                    # brotli. Harness: D:\Claude Tests\_civitai_partial_read_test.py.
                    #
                    # iter_chunked keeps the cap that a bare read()/text() would lose.
                    chunks = []
                    total = 0
                    async for chunk in resp.content.iter_chunked(65536):
                        total += len(chunk)
                        if total > 4 * 1024 * 1024:
                            return web.json_response({"ok": False, "reason": "offline",
                                                      "message": "Civitai response too large."})
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    try:
                        data = json.loads(body)
                    except Exception:
                        # A 200 that is not JSON is a block / sign-in page from the
                        # network or its protection layer, NOT Civitai saying no.
                        # Naming the content type is what makes the next bug report
                        # diagnosable instead of a guess - reports of this arrive
                        # blaming compression, which the measurements rule out.
                        # `continue`, never return: the other host is exactly the
                        # backup for a per-domain block (invariant 16).
                        data = None
                        last_note = ("Civitai replied with {} instead of data - most likely a "
                                     "block or sign-in page from your network or its protection "
                                     "layer.".format(ctype or "an unknown format"))
                        continue
                    break
        except Exception as exc:
            # Keep WHY it failed: a timeout, a DNS/TLS/proxy refusal and a block
            # page all used to collapse into one generic line, which defeats the
            # point of showing the user a reason at all.
            kind = type(exc).__name__
            if "Timeout" in kind or "Cancelled" in kind:
                last_note = "Civitai timed out."
            elif "ContentEncoding" in kind or "Decompress" in kind:
                # Kept DISTINCT from the block-page line above on purpose: the two
                # were being conflated in bug reports, and the fix for each is
                # completely different. This one should now be unreachable (we pin
                # Accept-Encoding to gzip/deflate), so if it ever shows up it is
                # genuinely worth hearing about.
                last_note = ("Civitai sent a compressed reply this install cannot read ({}). "
                             "Please report this.".format(kind))
            elif "JSON" in kind or "Decode" in kind or "Value" in kind:
                last_note = "Civitai sent an unreadable reply (a login or block page?)."
            else:
                last_note = "Could not reach Civitai ({}).".format(kind)
            continue
    if data is None:
        # A key refusal outranks whatever the later host said: "check your key" is
        # something the user can act on, a trailing timeout is not.
        return web.json_response({"ok": False, "reason": "offline",
                                  "message": key_note or last_note})
    parsed = _lora_parse_civitai(data, allow_adult=bool(acc.get("adult_thumbs")))
    # Civitai answered 200 with a usable record -> FOUND, even when this version
    # happens to carry no trainedWords and no model.name (plenty do not; e.g.
    # COOLKIDS_MERGE_V2.5 has an empty trainedWords list). Requiring those two
    # threw away genuine hits AND skipped the sidecar write below, so every later
    # click re-hashed the whole file and re-fetched it.
    if not parsed:
        return web.json_response({"ok": True, "found": False, "reason": "notfound"})
    await loop.run_in_executor(None, _lora_save_sidecar, path, data)
    return web.json_response({"ok": True, "found": True, "info": parsed})


def _lora_custom_file():
    """Where the user's own trigger words live: <ComfyUI user dir>/reaper/lora_triggers.json.

    ONE file for every LoRA, in the same folder as the Civitai account (and for the
    same reasons): outside this plugin's git working tree, so it survives an update
    or a Manager reinstall. Deliberately NOT a sidecar beside each .safetensors -
    that would write into the models folder, which is often a read-only or network
    drive, and risks colliding with a user's own <base>.json."""
    base = None
    try:
        base = folder_paths.get_user_directory()
    except Exception:
        base = None
    if not base:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user")
    d = os.path.join(base, "reaper")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return os.path.join(d, "lora_triggers.json")


def _lora_previews_dir():
    """Where a user-picked LoRA preview lives: <ComfyUI user dir>/reaper/lora_previews.

    Same folder and the same reasoning as the trigger store above - NOT beside the
    .safetensors. A models folder is often read-only or a network share, and writing
    a <base>.preview.png there would overwrite whatever a Civitai helper already put
    next to the LoRA. Kept separate, ours simply WINS, and deleting it puts the
    automatic picture back."""
    return os.path.join(os.path.dirname(_lora_custom_file()), "lora_previews")


def _lora_preview_path_checked(name):
    """The on-disk path for one of our LoRA preview files, or None if it is not
    one we could have written. Every route that writes, reads or deletes one
    gates on this.

    Mirrors `_wf_cover_path` deliberately. The filename is a sha1 WE generate and
    the helper already regex-checks its shape, so nothing the caller sent ever
    reaches the join - but the containment check goes through the pack's ONE
    guard because that is what a reader will look for, and because
    `nodes/_path_guard.py` says a check is imported, never re-rolled. Belt as
    well as braces."""
    folder = _lora_previews_dir()
    path = _lora_custom_preview_path(folder, name)
    if not path:
        return None
    return path if _is_path_under(path, folder) else None


# A downscaled jpeg of a preview picture. The browser resizes to 512px before
# uploading, so anything near this is already something we did not send.
_LORA_PREVIEW_MAX_BYTES = 4 * 1024 * 1024


@PromptServer.instance.routes.post("/reaper/api/lora/preview")
async def api_lora_preview_set(request):
    """Store the user's own preview picture for one LoRA. POST {name, dataUrl}.

    Same shape as the workflow-cover upload, and the same rules: the size is
    checked BEFORE decoding (base64 expands by a third, so decoding first would
    let an oversized payload set the memory it takes to reject it), and the bytes
    have to LOOK like a picture - this file is served straight back to a browser
    as an image, so one that is not would simply never render and read as the
    feature being broken. Always 200."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    # `body or {}` is NOT enough: request.json() ignores Content-Type, so a body of
    # `[1]` / `"x"` / `5` / `true` parses to a truthy NON-dict and reaches .get,
    # raising AttributeError out of the handler and 500-ing an unauthenticated
    # route. The falsy non-dicts ([], "", 0, null) are why that survived testing.
    if not isinstance(body, dict):
        body = {}
    name = str(body.get("name", "") or "")
    data_url = str(body.get("dataUrl", "") or "")
    path = _resolve_lora_path(name)
    roots = _lora_dirs()
    if not path or not roots or not _is_path_under(path, *roots):
        return web.json_response({"ok": False, "message": "LoRA not found."})
    if "," not in data_url:
        return web.json_response({"ok": False, "message": "Nothing to save."})
    payload = data_url.split(",", 1)[1]
    if len(payload) > _LORA_PREVIEW_MAX_BYTES * 4 // 3 + 8:
        return web.json_response({"ok": False, "message": "That picture is too large."})
    try:
        raw = base64.b64decode(payload)
    except Exception:
        return web.json_response({"ok": False, "message": "That picture could not be read."})
    if not raw or len(raw) > _LORA_PREVIEW_MAX_BYTES:
        return web.json_response({"ok": False, "message": "That picture is too large."})
    if not _wf_looks_like_image(raw):
        return web.json_response(
            {"ok": False, "message": "That file is not a picture the browser can show."})
    if not _lora_preview_path_checked(name):
        return web.json_response({"ok": False, "message": "Bad preview path."})

    import asyncio
    loop = asyncio.get_event_loop()
    folder = _lora_previews_dir()
    try:
        written = await loop.run_in_executor(
            None, _lora_write_custom_preview, folder, name, raw
        )
    except Exception as exc:
        return web.json_response({"ok": False, "message": "Could not save: {}".format(exc)})
    if not written:
        return web.json_response({"ok": False, "message": "Could not save that picture."})
    return web.json_response({"ok": True, "v": _lora_custom_preview_version(folder, name)})


@PromptServer.instance.routes.post("/reaper/api/lora/preview_delete")
async def api_lora_preview_delete(request):
    """Remove the user's own preview so the automatic picture comes back. POST {name}.

    The filename is derived from the LoRA name and checked against the one shape we
    could have written before it reaches os.remove, so a hand-edited request cannot
    aim this at anything else. Always 200."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):      # see api_lora_preview_set - a truthy non-dict 500s it
        body = {}
    name = str(body.get("name", "") or "") or request.query.get("name", "")
    path = _resolve_lora_path(name)
    roots = _lora_dirs()
    if not path or not roots or not _is_path_under(path, *roots):
        return web.json_response({"ok": False, "message": "LoRA not found."})
    if not _lora_preview_path_checked(name):
        return web.json_response({"ok": False, "message": "Bad preview path."})
    try:
        removed = _lora_delete_custom_preview(_lora_previews_dir(), name)
    except Exception as exc:
        return web.json_response({"ok": False, "message": "Could not remove: {}".format(exc)})
    return web.json_response({"ok": True, "removed": bool(removed)})


@PromptServer.instance.routes.post("/reaper/api/lora/custom_triggers")
async def api_lora_custom_triggers(request):
    """Save the user's own trigger words for one LoRA. POST {name, words}.

    The name is a STORE KEY, never a filesystem path - it is normalised by
    custom_trigger_key and used as a dict key, so it cannot reach the disk. We
    still resolve it against the loras dirs first so the store only ever gains
    entries for LoRAs that actually exist (a typo'd or hostile name is refused
    rather than silently accumulating). Always 200."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    name = data.get("name", "") or request.query.get("name", "")
    words = data.get("words", [])
    path = _resolve_lora_path(name)
    roots = _lora_dirs()
    if not path or not roots or not _is_path_under(path, *roots):
        return web.json_response({"ok": False, "message": "LoRA not found."})
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        stored = await loop.run_in_executor(
            None, _lora_set_custom, _lora_custom_file(), name, words
        )
    except Exception as exc:
        return web.json_response({"ok": False, "message": "Could not save: {}".format(exc)})
    return web.json_response({"ok": True, "words": stored})


@PromptServer.instance.routes.post("/reaper/api/lora/civitai_delete")
async def api_lora_civitai_delete(request):
    """Delete the cached Civitai sidecar (<base>.civitai.info) next to the LoRA, so the
    info reverts to the file's own words. POST {name}. Path-guarded to the loras dirs;
    always 200."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    name = data.get("name", "") or request.query.get("name", "")
    path = _resolve_lora_path(name)
    roots = _lora_dirs()
    if not path or not roots or not _is_path_under(path, *roots):
        return web.json_response({"ok": False, "message": "LoRA not found."})
    import asyncio
    loop = asyncio.get_event_loop()
    ok = await loop.run_in_executor(None, _lora_delete_sidecar, path)
    return web.json_response({"ok": bool(ok)})

