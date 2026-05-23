#!/usr/bin/env python3
"""Load and resolve a PKGBUILD file.

Spawns a bash subprocess to source the PKGBUILD, captures resolved variables
and function bodies, extracts ``# Maintainer:`` / ``# Contributor:`` comments,
and coerces all values to their emission-ready types.

Public API:
    load_pkgbuild(path: str) -> tuple[dict[str, Any], dict[str, str]]

Returns (vars_, funcs) where:
    vars_ values have been coerced to their final types:
        pkgrel                        — int | float
        epoch                         — int | None
        source*                       — list[dict]  (parsed from "filename::url")
        optdepends                    — list[dict]  (parsed from "name: desc")
        _deploy_aur, _demote_... etc. — bool        (parsed from "true"/"false")
        All other arrays              — list[str]
        All other scalars             — str

    funcs maps lowercase function name -> body text:
        "verify", "pkgver", "prepare", "build", "check", "package"

Maintainer and contributor lines from ``#`` comments are merged into vars_ as
``"maintainer"`` (str) and ``"contributor"`` (list[str]).
"""

from __future__ import annotations

import re
import subprocess
import sys

from typing import Any


# ── standard PKGBUILD(5) variable names, in field-order per §5.4 ──────────
_VAR_NAMES = [
    # identity & versioning
    "pkgname", "pkgbase", "pkgver", "pkgrel", "epoch", "pkgdesc", "changelog",
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
_FUNC_NAMES = ["verify", "pkgver", "prepare", "build", "check", "package"]


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


# ── boolean coercion ──────────────────────────────────────────────────────

_BOOL_MAP: dict[str, bool] = {"true": True, "false": False}

# Fields known to be boolean per the schema
_KNOWN_BOOL_FIELDS: set[str] = {
    "_deploy_aur", "_demote_upstream_maintainer", "_auto_merge_build",
    "_use_common_gemini_settings",
}


# ── pkgrel value coercion ─────────────────────────────────────────────────


def pkgrel_value(raw: str) -> int | float:
    """Convert pkgrel string to int or float."""
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except (ValueError, TypeError):
        raise ValueError(f"pkgrel value is not a valid number: {raw!r}")


# ── maintainer / contributor extraction ────────────────────────────────────


_RE_MAINTAINER = re.compile(r"^#\s*Maintainer:\s*(.+)$")
_RE_CONTRIBUTOR = re.compile(r"^#\s*Contributor:\s*(.+)$")


def parse_maintainer_contributor(pkgbuild_path: str) -> dict[str, Any]:
    """Extract # Maintainer: / # Contributor: lines from PKGBUILD source.

    If multiple ``# Maintainer:`` lines exist, the **last** one wins.  Earlier
    maintainer lines are silently discarded — this is intentional: the last
    maintainer declared is the current one.  All ``# Contributor:`` lines are
    collected in order of appearance.
    """
    maintainer = None
    contributors: list[str] = []
    with open(pkgbuild_path) as f:
        for line in f:
            m = _RE_MAINTAINER.match(line)
            if m:
                maintainer = m.group(1).strip()
            m = _RE_CONTRIBUTOR.match(line)
            if m:
                contributors.append(m.group(1).strip())
    result: dict[str, Any] = {}
    if maintainer:
        result["maintainer"] = maintainer
    if contributors:
        result["contributor"] = contributors
    return result


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


# ── public API ─────────────────────────────────────────────────────────────


def load_pkgbuild(path: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Load and fully resolve a PKGBUILD file.
    
    Returns (vars_, funcs) where all vars_ values are coerced to
    their emission-ready types.  See module docstring for the contract.
    """
    vars_, funcs = source_pkgbuild(path)

    # Merge maintainer/contributor from source comments
    mc = parse_maintainer_contributor(path)
    for k, v in mc.items():
        vars_[k] = v

    # Coerce pkgrel to int or float
    if "pkgrel" in vars_:
        vars_["pkgrel"] = pkgrel_value(str(vars_["pkgrel"]))

    # Coerce epoch to int (or leave as-is if not parseable)
    if "epoch" in vars_:
        try:
            vars_["epoch"] = int(vars_["epoch"])
        except (ValueError, TypeError):
            pass

    # Transform source arrays — "filename::url" -> {filename, url} dicts
    for key in ("source", "source_x86_64", "source_aarch64"):
        if key in vars_ and isinstance(vars_[key], list):
            vars_[key] = parse_source_entries(vars_[key])

    # Transform optdepends — "name: desc" -> {name, desc} dicts
    if "optdepends" in vars_ and isinstance(vars_["optdepends"], list):
        vars_["optdepends"] = parse_optdepends(vars_["optdepends"])

    # Convert known boolean strings to Python bools
    for key in _KNOWN_BOOL_FIELDS:
        if key in vars_ and isinstance(vars_[key], str):
            v = vars_[key].lower()
            if v in _BOOL_MAP:
                vars_[key] = _BOOL_MAP[v]

    return vars_, funcs
