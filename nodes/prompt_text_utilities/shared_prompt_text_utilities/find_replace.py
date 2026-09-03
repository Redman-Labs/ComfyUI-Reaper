"""Shared find-and-replace engine mirrored by the frontend live preview."""
import re

# Chars of input/output stored + sent for the on-node preview. The actual STRING
# output passed downstream is NEVER capped - only the preview sample is bounded
# so it can't bloat the workflow file or the websocket payload.
_PREVIEW_CAP = 4000


def _unbounded_quant_at(src, j):
    """True if an unbounded quantifier (* + or {n,}) starts at index j."""
    if j >= len(src):
        return False
    c = src[j]
    if c == "*" or c == "+":
        return True
    return re.match(r"\{\d*,\}", src[j:]) is not None


def _is_catastrophic_regex(src):
    """Heuristic ReDoS guard - MIRROR of js/find_replace/core.mjs::isCatastrophicRegex.

    Flags a NESTED unbounded quantifier (an unbounded-quantified group whose body
    also contains an unbounded quantifier, e.g. (a+)+ (a*)* (.*)* (\\w+)+ ), which
    can backtrack exponentially. This runs server-side on every Run with NO
    timeout, so such a pattern would wedge the worker; we skip the rule + warn
    instead. Heuristic, not complete; low false-positive rate (a nested unbounded
    quantifier is always redundant, so real patterns don't use it). Must stay in
    lockstep with the JS version so the on-node preview matches the run.
    """
    stack = []  # one dict per open group; "inner" = body has an unbounded quant
    escaped = False
    in_class = False
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if c == "\\":
            escaped = True
            i += 1
            continue
        if in_class:
            if c == "]":
                in_class = False
            i += 1
            continue
        if c == "[":
            in_class = True
            i += 1
            continue
        if c == "(":
            stack.append({"inner": False})
            i += 1
            continue
        if c == ")":
            grp = stack.pop() if stack else {"inner": False}
            quant = _unbounded_quant_at(src, i + 1)
            if quant and grp["inner"]:
                return True
            if quant and stack:
                stack[-1]["inner"] = True
            i += 1
            continue
        if _unbounded_quant_at(src, i):
            if stack:
                stack[-1]["inner"] = True
            i += 1
            continue
        i += 1
    return False


def _apply_rules(text, state):
    """Apply the enabled rules in order. Returns (result, warnings)."""
    rules = state.get("rules", [])
    case_sensitive = bool(state.get("caseSensitive", False))
    whole_word = bool(state.get("wholeWord", False))
    use_regex = bool(state.get("regex", False))
    tidy = bool(state.get("tidy", True))
    warnings = []

    out = text
    if isinstance(rules, list):
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            if not rule.get("enabled", True):
                continue
            # Coerce non-string find/replace to "" (mirrors the JS readState
            # coercion) so a malformed/hand-edited state with a numeric or list
            # find/replace can't crash apply() with a TypeError/AttributeError -
            # the only exception caught below is re.error.
            find = rule.get("find", "")
            if not isinstance(find, str):
                find = ""
            if not find:
                continue
            repl = rule.get("replace", "")
            if not isinstance(repl, str):
                repl = ""
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                if use_regex:
                    if _is_catastrophic_regex(find):
                        warnings.append(
                            "Rule %d: pattern may be catastrophically slow "
                            "(nested quantifier) - simplify it" % (idx + 1)
                        )
                        continue
                    out = re.sub(find, repl, out, flags=flags)
                else:
                    pattern = re.escape(find)
                    if whole_word:
                        pattern = r"\b" + pattern + r"\b"
                    # Escape backslashes in the replacement so a literal string
                    # containing "\1" or "\g<1>" is not interpreted as a backref.
                    safe_repl = repl.replace("\\", "\\\\")
                    out = re.sub(pattern, safe_repl, out, flags=flags)
            except re.error as exc:
                warnings.append("Rule %d: invalid regex (%s)" % (idx + 1, exc))
                continue

    if tidy:
        out = _tidy(out)
    return out, warnings


def _tidy(s):
    """Conservative cleanup. Mirrors tidy() in js/find_replace/core.mjs.

    Collapses runs of spaces/tabs and fixes comma spacing. Interior newlines
    are preserved (never collapsed); the final strip() trims leading/trailing
    whitespace - including newlines - from the whole string.
    """
    # Collapse runs of spaces/tabs to a single space.
    s = re.sub(r"[ \t]+", " ", s)
    # Space(s)/tab(s) before a comma -> drop them.
    s = re.sub(r"[ \t]+,", ",", s)
    # Collapse repeated commas (optionally space/tab separated) into one.
    s = re.sub(r",(?:[ \t]*,)+", ",", s)
    # Trim trailing spaces/tabs at the end of each line.
    s = re.sub(r"[ \t]+(\r?\n)", r"\1", s)
    # Drop a leading comma left behind by a deletion.
    s = re.sub(r"^[ \t]*,[ \t]*", "", s)
    # Drop a dangling trailing comma left behind by a deletion.
    s = re.sub(r",[ \t]*$", "", s)
    return s.strip()


__all__ = ["_PREVIEW_CAP", "_apply_rules"]
