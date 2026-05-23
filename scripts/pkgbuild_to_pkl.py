#!/usr/bin/env python3
"""Convert an Arch Linux PKGBUILD into a Pkl amending module.

Usage:
    python3 scripts/pkgbuild_to_pkl.py packages/opendoas/PKGBUILD > /tmp/opendoas.pkl

Spawns a bash subprocess to source the PKGBUILD, resolve all variable
references, and produce ``declare -p`` / ``declare -f`` output.  Parses
that output into Python data structures and emits a Pkl module that
``amends "schemas/arch_pkg.pkl"``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from textwrap import dedent
from typing import Any


# ── standard PKGBUILD(5) variable names, in field-order per §5.4 ──────────
_VAR_NAMES = [
    # identity & versioning
    "pkgname", "pkgver", "pkgrel", "epoch", "pkgdesc", "changelog",
    # architecture & metadata
    "arch", "url", "license", "groups",
    # package relationships
    "depends", "makedepends", "checkdepends", "optdepends",
    "provides", "conflicts", "replaces",
    # source & integrity
    "source", "source_x86_64", "source_aarch64",
    "sha256sums", "sha512sums", "sha224sums", "sha384sums",
    "b2sums", "sha512sums_x86_64", "sha512sums_aarch64",
    "validpgpkeys", "noextract",
    # install & config
    "install", "backup", "options",
]

# PKGBUILD lifecycle function names
_FUNC_NAMES = ["pkgver", "prepare", "build", "check", "package"]

# PKGBUILD → Pkl field-name mapping (Pkl reserved-word avoidance)
_FUNC_FIELD_MAP: dict[str, str] = {
    "pkgver": "pkgverFunc",
    "package": "packageFunc",
}

# ── bash-string unescaping ────────────────────────────────────────────────


def _unescape_double_quoted(s: str) -> str:
    """Unescape a Bash double-quoted string value (without the outer ")."""
    result: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nc = s[i + 1]
            escape_map = {
                '"': '"',
                "$": "$",
                "\\": "\\",
                "`": "`",
                "!": "!",
                "\n": "",   # escaped newline → nothing (line continuation)
            }
            if nc in escape_map:
                result.append(escape_map[nc])
                i += 2
                continue
        result.append(c)
        i += 1
    return "".join(result)


def _unescape_ansi_c(s: str) -> str:
    """Unescape a Bash $'…' ANSI-C quoted string."""
    result: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nc = s[i + 1]
            ansi_map = {
                "n": "\n",
                "t": "\t",
                "r": "\r",
                "a": "\a",
                "b": "\b",
                "f": "\f",
                "v": "\v",
                "\\": "\\",
                "'": "'",
                '"': '"',
                "e": "\x1b",
                "E": "\x1b",
            }
            if nc in ansi_map:
                result.append(ansi_map[nc])
                i += 2
                continue
            if nc == "x" and i + 3 < len(s):          # \xHH
                try:
                    result.append(chr(int(s[i + 2 : i + 4], 16)))
                    i += 4
                    continue
                except (ValueError, IndexError):
                    pass
            if nc == "0":                            # \0NNN octal
                j = i + 1
                while j < len(s) and s[j].isdigit():
                    j += 1
                try:
                    result.append(chr(int(s[i + 1 : j], 8)))
                    i = j
                    continue
                except (ValueError, IndexError):
                    pass
        result.append(c)
        i += 1
    return "".join(result)


def unescape_bash_string(raw: str) -> str:
    """Unescape a full Bash-quoted value (e.g. ``"hello"`` or ``$'line\\n'``)."""
    raw = raw.strip()
    if raw.startswith("$'") and raw.endswith("'"):
        return _unescape_ansi_c(raw[2:-1])
    if raw.startswith('"') and raw.endswith('"'):
        return _unescape_double_quoted(raw[1:-1])
    return raw


# ── declare -p parsers ────────────────────────────────────────────────────

# Matches: declare -- varname="value"
_RE_SCALAR = re.compile(r'^declare\s+(?:--|-r)\s+(\w+)="(.*)"')
# Matches: declare -a varname=([0]="v0" [1]="v1")
_RE_ARRAY = re.compile(r'^declare\s+-a\s+(\w+)=\((.*)\)')
# Matches: declare -A varname=(["k1"]="v1" ["k2"]="v2")
_RE_ASSOC = re.compile(r'^declare\s+-A\s+(\w+)=\((.*)\)')
# Matches an individual array/assoc element: [K]="V"  or  ["K"]="V"
# Handles escaped quotes inside values like [0]="foo\"bar"
_RE_ELEM = re.compile(r'\[(?:(\d+)|"([^"]*)")\]="((?:[^"\\]|\\.)*)"')


def _parse_array_elements(body: str) -> list[str]:
    """Extract element values from the body of a Bash indexed array."""
    elems: list[str] = []
    for m in _RE_ELEM.finditer(body):
        elems.append(unescape_bash_string('"' + m.group(3) + '"'))
    return elems


def _parse_assoc_elements(body: str) -> list[str]:
    """Extract key-value pairs from the body of a Bash associative array.

    Returns a flat list alternating key, value: ``["k1", "v1", "k2", "v2"]``.
    """
    pairs: list[str] = []
    for m in _RE_ELEM.finditer(body):
        key = m.group(1) if m.group(1) is not None else m.group(2)
        val = unescape_bash_string('"' + m.group(3) + '"')
        pairs.append(key)
        pairs.append(val)
    return pairs


def parse_declare(lines: list[str]) -> dict[str, Any]:
    """Parse ``declare -p`` lines into a Python dict.

    * Scalars → ``str``
    * Indexed arrays → ``list[str]`` (empty lists are skipped)
    * Associative arrays → ``list[str]`` (flat key-value pairs; empty skipped)
    * Empty strings are skipped.
    """
    vars_: dict[str, Any] = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # indexed array
        m = _RE_ARRAY.match(line)
        if m:
            name, body = m.group(1), m.group(2)
            elements = _parse_array_elements(body)
            if elements:
                vars_[name] = elements
            continue

        # associative array
        m = _RE_ASSOC.match(line)
        if m:
            name, body = m.group(1), m.group(2)
            pairs = _parse_assoc_elements(body)
            if pairs:
                vars_[name] = pairs
            continue

        # scalar
        m = _RE_SCALAR.match(line)
        if m:
            name, raw_val = m.group(1), m.group(2)
            val = unescape_bash_string('"' + raw_val + '"')
            if val:   # skip empty strings
                vars_[name] = val
            continue

    return vars_


# ── declare -f parsers ────────────────────────────────────────────────────


def parse_functions(text: str) -> dict[str, str]:
    """Extract function bodies from ``declare -f`` output.

    Returns a dict mapping function *name* → *body text* (indent stripped).
    """
    funcs: dict[str, str] = {}
    # Match from =FUNC_BEGIN=name= through =FUNC_END=name=
    pattern = re.compile(
        r'=FUNC_BEGIN=(\w+)=\n'
        r'(.*?)'
        r'=FUNC_END=\1=',
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        name = m.group(1)
        raw_body = m.group(2)
        # Strip the wrapper: lines are "name ()\n{\n  body...\n}"
        lines = raw_body.split("\n")
        # First line is "name ()", second is "{", last is "}"
        # Find body start and end
        body_start = -1
        body_end = -1
        for i, ln in enumerate(lines):
            if ln.strip() == "{" and body_start < 0:
                body_start = i
            elif ln.strip() == "}" and body_start >= 0:
                body_end = i
                break

        if body_start >= 0 and body_end > body_start:
            body = lines[body_start + 1 : body_end]
            # Dedent – bash indents by 4 spaces
            dedented = _dedent_body(body)
            funcs[name] = dedented
        elif len(lines) >= 3:
            # Fallback: skip first 2 lines (signature + `{`), drop last line (`}`)
            body = lines[2:-1]
            dedented = _dedent_body(body)
            funcs[name] = dedented

    return funcs


def _dedent_body(lines: list[str]) -> str:
    """Strip common leading whitespace from a list of body lines."""
    if not lines:
        return ""
    # Remove empty leading/trailing lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    # Find common indent
    common = min((len(ln) - len(ln.lstrip(" "))) for ln in lines if ln.strip())
    out = "\n".join(ln[common:] if ln.strip() else "" for ln in lines)
    return out.strip()


# ── source array → SourceEntry list ───────────────────────────────────────


def parse_source_entries(sources: list[str]) -> list[dict[str, str]]:
    """Convert raw source array elements into SourceEntry dicts.

    * ``"filename::url"`` → filename / url split
    * plain filename → url == filename
    """
    entries: list[dict[str, str]] = []
    for src in sources:
        if "::" in src:
            fname, url = src.split("::", 1)
        else:
            fname = src
            url = src
        entries.append({"filename": fname, "url": url})
    return entries


# ── optdepends → OptDependsEntry list ─────────────────────────────────────


def parse_optdepends(entries: list[str]) -> list[dict[str, str]]:
    """Split ``"name: description"`` entries into OptDependsEntry dicts."""
    result: list[dict[str, str]] = []
    for entry in entries:
        if ": " in entry:
            name, desc = entry.split(": ", 1)
        else:
            name = entry
            desc = ""
        result.append({"name": name, "desc": desc})
    return result


_BOOL_MAP: dict[str, bool] = {"true": True, "false": False}

# Fields known to be boolean per the schema
_KNOWN_BOOL_FIELDS: set[str] = {
    "_deploy_aur", "_demote_upstream_maintainer", "_auto_merge_build",
    "_use_common_gemini_settings",
}

# ── Pkl emitter ───────────────────────────────────────────────────────


def _is_multiline(s: str) -> bool:
    return "\n" in s


def _pkl_string(s: str) -> str:
    """Emit a Pkl string literal: single-line -> "quoted", multi-line -> triple-quoted."""
    multiline = _is_multiline(s)
    # Always escape backslashes — Pkl interprets \(...) as interpolation in all string types.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    if multiline:
        return '"""\n' + escaped + '\n"""'
    return f'"{escaped}"'


def _pkl_value(val: Any, indent: str = "") -> str:
    """Emit an arbitrary Python value as a Pkl expression."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return repr(val)
    if isinstance(val, str):
        return _pkl_string(val)
    if isinstance(val, list):
        if not val:
            return "null"
        inner_indent = indent + "    "
        # Determine if this is a list of dicts (SourceEntry / OptDependsEntry)
        if isinstance(val[0], dict):
            items = [_pkl_object(elem, inner_indent) for elem in val]
            body = _join_listing_items(items)
            return f"new {{\n{body}\n{indent}}}"
        # Plain string list — use inline or multiline new { ... }
        items = [f"{inner_indent}{_pkl_string(e)}" for e in val]
        if len(items) == 1:
            return f"new {{ {items[0].strip()} }}"
        return f"new {{\n" + "\n".join(items) + f"\n{indent}}}"
    return _pkl_string(str(val))


def _pkl_object(obj: dict[str, Any], indent: str = "") -> str:
    """Emit a Pkl object (e.g. ``new schema.SourceEntry { ... }``)."""
    class_name = "schema.SourceEntry" if "url" in obj else "schema.OptDependsEntry"
    parts: list[str] = []
    inner_indent = indent + "    "
    for k, v in obj.items():
        if v is None:
            continue
        if isinstance(v, str):
            parts.append(f"{inner_indent}{k} = {_pkl_string(v)}")
        elif isinstance(v, bool):
            parts.append(f"{inner_indent}{k} = {_pkl_value(v)}")
        elif isinstance(v, (int, float)):
            parts.append(f"{inner_indent}{k} = {_pkl_value(v)}")
        else:
            parts.append(f"{inner_indent}{k} = {_pkl_value(v)}")
    inner = "\n".join(parts)
    return f"{indent}new {class_name} {{\n{inner}\n{indent}}}"


def _join_listing_items(items: list[str], indent: str = "") -> str:
    """Join listing items with proper Pkl formatting, indenting each line."""
    result_lines: list[str] = []
    for item in items:
        for line in item.split("\n"):
            result_lines.append(f"{indent}{line}" if line else "")
    return "\n".join(result_lines)


def pkgrel_value(raw: str) -> int | float:
    """Convert pkgrel string to int or float."""
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except (ValueError, TypeError):
        return int(raw) if raw.isdigit() else raw  # type: ignore[return-value]


# ── field ordering for output ─────────────────────────────────────────────

_FIELD_ORDER: list[str] = [
    # identity
    "pkgname", "pkgver", "pkgrel", "epoch", "pkgdesc", "changelog",
    # architecture & metadata
    "arch", "url", "license", "groups",
    # relationships
    "depends", "makedepends", "checkdepends", "optdepends",
    "provides", "conflicts", "replaces",
    # source & integrity
    "source", "source_x86_64", "source_aarch64",
    "sha256sums", "sha512sums", "sha224sums", "sha384sums",
    "b2sums", "sha512sums_x86_64", "sha512sums_aarch64",
    "validpgpkeys", "noextract",
    # install & config
    "install", "backup", "options",
    # lifecycle functions
    "pkgverFunc", "prepare", "build", "check", "packageFunc",
    # custom (hidden) variables
]


def emit_pkl(vars_: dict[str, Any], funcs: dict[str, str]) -> str:
    """Build a complete Pkl import+output.value module string."""
    lines: list[str] = []
    comment: str = f"{vars_.get('pkgname', 'unknown')} — {vars_.get('pkgdesc', '')}"
    if len(comment) > 79:
        comment = comment[:76] + "..."
    lines.append("// " + comment)
    lines.append("// Auto-generated from PKGBUILD. Do not edit manually.")
    lines.append('import "../../schemas/arch_pkg.pkl" as schema')
    lines.append("")
    lines.append("output {")
    lines.append("    value = new schema.Package {")

    body_indent = "        "  # 8 spaces

    # Sort fields by _FIELD_ORDER; anything not in the list goes at the end
    emitted = set()

    # Emit variable fields in order
    for key in _FIELD_ORDER:
        if key in vars_:
            val = vars_[key]
            if val is None or val == "" or val == []:
                continue
            emitted.add(key)
            lines.append(_format_field(key, val, body_indent))

    # Emit function bodies
    func_map: dict[str, str] = {
        "pkgverFunc": funcs.get("pkgver", ""),
        "prepare": funcs.get("prepare", ""),
        "build": funcs.get("build", ""),
        "check": funcs.get("check", ""),
        "packageFunc": funcs.get("package", ""),
    }
    for fname, fbody in func_map.items():
        if fbody:
            lines.append(_format_field(fname, fbody, body_indent))

    # Emit remaining vars (custom _-prefixed, etc.)
    remaining = [k for k in vars_ if k not in emitted and not k.startswith("_")]
    for key in sorted(remaining):
        val = vars_[key]
        if val is None or val == "" or val == []:
            continue
        lines.append(_format_field(key, val, body_indent))

    # Emit hidden _-prefixed variables (without "hidden" keyword — already in class def)
    hidden_vars = [k for k in sorted(vars_) if k.startswith("_") and k not in emitted]
    for key in hidden_vars:
        val = vars_[key]
        if val is None or val == "" or val == []:
            continue
        lines.append(_format_field(key, val, body_indent))

    lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_field(key: str, val: Any, indent: str = "") -> str:
    """Format a single ``field = value`` line at the given indent level."""
    # Convert known boolean string values
    if key in _KNOWN_BOOL_FIELDS and isinstance(val, str) and val.lower() in _BOOL_MAP:
        val = _BOOL_MAP[val.lower()]

    if key == "pkgrel":
        val = pkgrel_value(str(val))
    elif key == "epoch":
        try:
            val = int(val)
        except (ValueError, TypeError):
            pass
    elif key == "source" and isinstance(val, list):
        entries = parse_source_entries(val)
        return f"{indent}source = {_pkl_value(entries, indent)}"
    elif key in ("source_x86_64", "source_aarch64") and isinstance(val, list):
        entries = parse_source_entries(val)
        return f"{indent}{key} = {_pkl_value(entries, indent)}"
    elif key == "optdepends" and isinstance(val, list):
        entries = parse_optdepends(val)
        return f"{indent}optdepends = {_pkl_value(entries, indent)}"
    elif key == "options" and isinstance(val, list):
        return f"{indent}options = {_pkl_value(val, indent)}"

    return f"{indent}{key} = {_pkl_value(val, indent)}"


# ── bash subprocess ───────────────────────────────────────────────────────

_BASH_SCRIPT_TEMPLATE = """\
source "{pkgbuild_path}"

# Emit declare -p for all standard PKGBUILD variables
for var in {var_names}; do
    if declare -p "$var" >/dev/null 2>&1; then
        declare -p "$var"
    fi
done

# Also capture any _-prefixed custom variables
for var in $(compgen -v 2>/dev/null); do
    case "$var" in
        _) continue ;;  # bash internal $_
        _*) declare -p "$var" 2>/dev/null || true ;;
    esac
done

echo "===FUNCTIONS==="

for func in {func_names}; do
    if declare -f "$func" >/dev/null 2>&1; then
        echo "=FUNC_BEGIN=$func="
        declare -f "$func"
        echo "=FUNC_END=$func="
    fi
done
"""


def source_pkgbuild(pkgbuild_path: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Spawn bash, source the PKGBUILD, capture all variables and functions."""
    script = _BASH_SCRIPT_TEMPLATE.format(
        pkgbuild_path=pkgbuild_path,
        var_names=" ".join(_VAR_NAMES),
        func_names=" ".join(_FUNC_NAMES),
    )

    result = subprocess.run(
        ["bash"],
        input=script,
        capture_output=True,
        text=True,
        timeout=30,
    )
    stdout = result.stdout
    stderr = result.stderr

    # Log non-fatal stderr diagnostics
    if result.returncode != 0:
        print(f"bash subprocess exited {result.returncode}: {stderr}", file=sys.stderr)
        sys.exit(1)

    # Split vars from functions
    if "===FUNCTIONS===" in stdout:
        vars_text, funcs_text = stdout.split("===FUNCTIONS===", 1)
    else:
        vars_text = stdout
        funcs_text = ""

    vars_ = parse_declare(vars_text.strip().split("\n"))
    funcs = parse_functions(funcs_text)

    return vars_, funcs


# ── main ──────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <PKGBUILD_PATH>", file=sys.stderr)
        sys.exit(1)

    pkgbuild_path = sys.argv[1]
    try:
        vars_, funcs = source_pkgbuild(pkgbuild_path)
    except subprocess.TimeoutExpired:
        print("Error: bash subprocess timed out", file=sys.stderr)
        sys.exit(1)

    output = emit_pkl(vars_, funcs)
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
