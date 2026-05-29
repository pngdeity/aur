#!/usr/bin/env python3
"""Format resolved PKGBUILD data as Pkl module text.

Pure formatter — receives already-coerced data from pkgbuild_loader
and produces valid Pkl output.  Has no knowledge of PKGBUILD semantics.

Public API:
    write_pkl_module(vars_: dict[str, Any], funcs: dict[str, str]) -> str

Returns a complete Pkl ``output { value = new schema.Package { ... } }`` module
string suitable for ``pkl eval``.
"""

from __future__ import annotations

from typing import Any

# ── Pkl utility helpers ────────────────────────────────────────────────────

_LIFECYCLE_FUNC_KEYS: set[str] = {"verify", "pkgverFunc", "prepare", "build", "check", "packageFunc"}


def _is_multiline(s: str) -> bool:
    return "\n" in s


def _is_empty_value(val: Any) -> bool:
    """Return True if val represents a missing/empty field that should be skipped."""
    if val is None:
        return True
    if isinstance(val, list) and not val:
        return True
    return False


# ── Pkl string literals ────────────────────────────────────────────────────


def _pkl_string(s: str) -> str:
    """Emit a Pkl string literal: single-line -> "quoted", multi-line -> triple-quoted."""
    multiline = _is_multiline(s)
    # Always escape backslashes — Pkl interprets \(...) as interpolation in all string types.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    if multiline:
        return '"""\n' + escaped + '\n"""'
    return f'"{escaped}"'


def _pkl_raw_string(s: str) -> str:
    """Emit a Pkl custom string literal using #""# delimiters.

    Pkl #""# strings do not process backslash escapes — this preserves
    literal backslashes in function bodies (e.g., ``sed 's/\\//g'``).
    """
    s = s.replace('"#', '"\\#')  # escape the delimiter sequence
    multiline = "\n" in s
    if multiline:
        return '#"""\n' + s + '\n"""#'
    return '#"' + s + '"#'


# ── Pkl value emission ─────────────────────────────────────────────────────


def _join_listing_items(items: list[str], indent: str = "") -> str:
    """Join listing items with proper Pkl formatting, indenting each line."""
    result_lines: list[str] = []
    for item in items:
        for line in item.split("\n"):
            result_lines.append(f"{indent}{line}" if line else "")
    return "\n".join(result_lines)


def _pkl_object(obj: dict[str, Any], indent: str = "", *, class_name: str) -> str:
    """Emit a Pkl object (e.g. ``new schema.SourceEntry { ... }``)."""
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
            class_name = "schema.SourceEntry" if "url" in val[0] else "schema.OptDependsEntry"
            items = [_pkl_object(elem, inner_indent, class_name=class_name) for elem in val]
            body = _join_listing_items(items)
            return f"new {{\n{body}\n{indent}}}"
        # Plain string list — use inline or multiline new { ... }
        items = [f"{inner_indent}{_pkl_string(e)}" for e in val]
        if len(items) == 1:
            return f"new {{ {items[0].strip()} }}"
        return f"new {{\n" + "\n".join(items) + f"\n{indent}}}"
    raise TypeError(f"unexpected type for Pkl emission: {type(val).__name__} (value={val!r})")


# ── field ordering for output ─────────────────────────────────────────────

# NOTE: This ordering must match the field emission order in
# schemas/arch_pkg.pkl renderPKGBUILD().  If the schema adds, removes,
# or reorders a standard field, update this list to match.
_FIELD_ORDER: list[str] = [
    # identity
    "maintainer", "contributor", "pkgname", "pkgbase", "pkgver", "pkgrel", "epoch", "pkgdesc", "changelog",
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
    "verify", "pkgverFunc", "prepare", "build", "check", "packageFunc",
    # custom (hidden) variables
]


# ── field formatting ───────────────────────────────────────────────────────


def _format_field(key: str, val: Any, indent: str = "") -> str:
    """Format a single ``field = value`` line at the given indent level.

    Assumes val has already been coerced by pkgbuild_loader.load_pkgbuild():
    pkgrel is int|float, epoch is int|None, source arrays are already
    list[dict], optdepends arrays are already list[dict], booleans are
    already Python bool.
    """
    if key in _LIFECYCLE_FUNC_KEYS and isinstance(val, str):
        return f"{indent}{key} = {_pkl_raw_string(val)}"
    return f"{indent}{key} = {_pkl_value(val, indent)}"


# ── public API ─────────────────────────────────────────────────────────────


def write_pkl_module(vars_: dict[str, Any], funcs: dict[str, str]) -> str:
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
            if _is_empty_value(val):
                continue
            emitted.add(key)
            lines.append(_format_field(key, val, body_indent))

    # Emit function bodies
    func_map: dict[str, str] = {
        "verify": funcs.get("verify", ""),
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
        if _is_empty_value(val):
            continue
        lines.append(_format_field(key, val, body_indent))

    # Emit hidden _-prefixed variables (without "hidden" keyword — already in class def)
    hidden_vars = [k for k in sorted(vars_) if k.startswith("_") and k not in emitted]
    for key in hidden_vars:
        val = vars_[key]
        if _is_empty_value(val):
            continue
        lines.append(_format_field(key, val, body_indent))

    lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"
