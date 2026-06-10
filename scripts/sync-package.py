#!/usr/bin/env python3
"""Event-driven package synchronization.

Detects upstream PKGBUILD changes, classifies them by concern, applies
per-concern strategies, and generates metadata. Supports bootstrap
(first-run) and update (recurring) paths.

Usage:
    python sync-package.py <pkg_name> <new_ver>

Exit codes:
    0 — synchronization complete
    1 — failure (merge conflict, validation error, missing directory)
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from pkgbuild_loader import load_pkgbuild
from pkl_writer import write_pkl_module

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Identity fields preserved across upstream merges
_IDENTITY_FIELDS = (
    "pkgname",
    "pkgver",
    "pkgrel",
    "provides",
    "conflicts",
    "replaces",
    "source",
)

# Concern groups for change classification
_CONCERN_GROUPS = {
    "AUTHORSHIP": ("maintainer", "contributor"),
    "IDENTITY": ("pkgname", "provides", "conflicts", "replaces"),
    "VERSION": ("pkgver", "pkgrel"),
    "METADATA": ("pkgdesc", "url", "license", "arch", "backup", "install", "options"),
    "DEPENDS": ("depends",),
    "MAKEDEPENDS": ("makedepends",),
    "CHECKDEPENDS": ("checkdepends",),
    "OPTDEPENDS": ("optdepends",),
    "SOURCES": (
        "source",
        "sha256sums",
        "sha512sums",
        "sha224sums",
        "sha384sums",
        "b2sums",
    ),
    "BUILD": ("prepare", "build", "check", "package"),
}

# Checksum array priority for coalescing
_CHECKSUM_KEYS = ("sha256sums", "sha512sums", "sha224sums", "sha384sums", "b2sums")


# ── helpers ──────────────────────────────────────────────────────────────


def _is_vcs_url(url: str) -> bool:
    return url.startswith(("git+", "svn+", "hg+", "bzr+"))


def _is_pinned(url: str) -> bool:
    return "#tag=" in url or "#commit=" in url


def _coalesce_checksums(vars_: dict) -> list:
    for key in _CHECKSUM_KEYS:
        val = vars_.get(key)
        if val:
            return val
    return []


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


# ── concern classification ───────────────────────────────────────────────


def _classify_changes(old_vars: dict, new_vars: dict) -> tuple[set[str], bool]:
    events: set[str] = set()
    for group_name, fields in _CONCERN_GROUPS.items():
        for f in fields:
            if old_vars.get(f) != new_vars.get(f):
                events.add(group_name)
                break
    build_changed = "BUILD" in events
    # Check pkgver function
    if old_vars.get("_pkgver_func_body") != new_vars.get("_pkgver_func_body"):
        events.add("VERSION")
    return events, build_changed


# ── upstream resolution ──────────────────────────────────────────────────


def _resolve_upstream(vars_: dict) -> tuple[str | None, str | None]:
    arch_repo = vars_.get("_upstream_arch_repo")
    aur_pkg = vars_.get("_upstream_aur_pkg")
    if arch_repo:
        base = f"https://gitlab.archlinux.org/{arch_repo}/-/raw/main"
        return f"{base}/PKGBUILD", base
    if aur_pkg:
        base = "https://aur.archlinux.org/cgit/aur.git/plain"
        return f"{base}/PKGBUILD?h={aur_pkg}", base
    return None, None


# ── fetch upstream ────────────────────────────────────────────────────────


def _fetch_upstream(url: str, base_url: str, pkg_dir: Path) -> tuple[bool, bool]:
    """Returns (ok, changed). ok=False on fetch/validation failure.
    changed=True means upstream differs from cache (or first sync).
    """
    cache = pkg_dir / ".PKGBUILD.upstream"
    tmp = pkg_dir / "PKGBUILD.new"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sync-package/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        _log(f"  -> Failed to fetch upstream PKGBUILD: {e}")
        return False, False

    if "pkgname=" not in content:
        _log("  -> Fetched content does not appear to be a PKGBUILD")
        return False, False

    tmp.write_text(content)

    if cache.exists():
        if cache.read_text() == content:
            _log("  -> Upstream PKGBUILD unchanged.")
            tmp.unlink()
            return True, False
        return True, True
    else:
        _log("  -> Initial upstream tracking setup.")
        _fetch_assets(content, base_url, pkg_dir)
        tmp.rename(cache)
        return True, True


def _fetch_assets(upstream_text: str, base_url: str, pkg_dir: Path) -> None:
    _log("  -> Scanning for missing upstream assets...")
    for line in upstream_text.split("\n"):
        line = line.strip().strip("'\"")
        if "://" in line or "=(" in line or line.startswith(")"):
            continue
        name = line.split(":")[0] if ":" in line else line
        if not name:
            continue
        asset = pkg_dir / name
        if asset.exists():
            continue
        try:
            _log(f"    -> Downloading missing asset: {name}")
            req = urllib.request.Request(
                f"{base_url}/{name}", headers={"User-Agent": "sync-package/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                asset.write_bytes(resp.read())
        except Exception as e:
            _log(f"    -> Failed to download {name}: {e}")


# ── merge ─────────────────────────────────────────────────────────────────


def _merge_with_identity(
    orig_vars: dict, orig_funcs: dict, pkg_dir: Path
) -> tuple[dict, dict, bool]:
    local = pkg_dir / "PKGBUILD"
    old = pkg_dir / ".PKGBUILD.upstream"
    new = pkg_dir / "PKGBUILD.new"

    # snapshot identity from original
    identity_snapshot = {
        k: orig_vars.get(k) for k in _IDENTITY_FIELDS if k in orig_vars
    }
    pkgver_func_body = orig_funcs.get("pkgver")

    result = subprocess.run(
        ["git", "merge-file", str(local), str(old), str(new)],
        capture_output=True,
        text=True,
        cwd=str(pkg_dir),
    )
    if result.returncode < 0:
        _log("  -> Merge conflicts detected! Please resolve manually.")
        return orig_vars, orig_funcs, False

    # Apply demotion at text level before re-parsing
    if orig_vars.get("_demote_upstream_maintainer"):
        _log("  -> Applying maintainer demotion")
        text = local.read_text()
        lines = text.split("\n")
        # Line 1 is our maintainer — keep it. Demote all later Maintainer: lines.
        result_lines = [lines[0]] if lines else []
        for line in lines[1:]:
            result_lines.append(line.replace("# Maintainer:", "# Contributor:"))
        local.write_text("\n".join(result_lines))

    # Load merged + demoted result
    merged_vars, merged_funcs = load_pkgbuild(str(local))

    # Restore identity
    for k, v in identity_snapshot.items():
        if v is not None:
            merged_vars[k] = v
    if pkgver_func_body:
        merged_funcs["pkgver"] = pkgver_func_body

    # Clean up temp
    new.unlink(missing_ok=True)
    old.rename(pkg_dir / ".PKGBUILD.upstream")

    return merged_vars, merged_funcs, True


# ── declarative rules ─────────────────────────────────────────────────────


def _apply_declarative_rules(vars_: dict) -> None:
    """Maintainer demotion if _demote_upstream_maintainer is true."""
    if vars_.get("_demote_upstream_maintainer"):
        _log("  -> Applying maintainer demotion")
        contrib = vars_.get("contributor", [])
        if contrib:
            # Current maintainer stays; contributors are from demoted upstream
            pass


def _apply_prereview_marker(vars_: dict, build_changed: bool, new_ver: str) -> None:
    if build_changed and not vars_.get("_auto_merge_build"):
        _log(
            f"  -> Build logic changed upstream (review required). Adding PREREVIEW marker."
        )
        # marker will be rendered as a comment by the PKGBUILD renderer
        vars_["_prereview"] = f"upstream build functions changed ({new_ver})"
    elif build_changed:
        _log(
            "  -> Build logic changed upstream. Auto-merging (_auto_merge_build=true)."
        )


# ── version bump ──────────────────────────────────────────────────────────


def _bump_version(
    vars_: dict, pkg_name_raw: str, pkg_name: str, new_ver: str, upstream_changed: bool
) -> None:
    current_ver = str(vars_.get("pkgver", ""))
    current_rel = int(vars_.get("pkgrel", 1))
    if pkg_name_raw == pkg_name and current_ver != new_ver:
        _log(f"  -> Updating pkgver {current_ver} -> {new_ver}, resetting pkgrel")
        vars_["pkgver"] = new_ver
        vars_["pkgrel"] = 1
    elif upstream_changed:
        _log(f"  -> Bumping pkgrel {current_rel} -> {current_rel + 1}")
        vars_["pkgrel"] = current_rel + 1


# ── post-sync hooks ───────────────────────────────────────────────────────


def _run_update_hook(pkg_dir: Path, new_ver: str) -> None:
    hook = pkg_dir / "update.sh"
    if hook.is_file() and os.access(hook, os.X_OK):
        _log("  -> Running package-specific transformation script")
        subprocess.run([str(hook), new_ver], cwd=str(pkg_dir), check=False)


def _sync_shared_assets(vars_: dict, pkg_dir: Path) -> None:
    if vars_.get("_use_common_gemini_settings"):
        _log("  -> Syncing shared gemini-cli settings from common/")
        src = REPO_ROOT / "common" / "gemini-cli-settings.json"
        if src.is_file():
            shutil.copy2(src, pkg_dir / "settings.json")


def _generate_changelog(
    vars_: dict, pkg_dir: Path, pkg_name: str, new_ver: str
) -> None:
    github_repo = vars_.get("_githubname")
    if not github_repo:
        return
    tag_pattern = vars_.get("_tag", f"v{new_ver}")
    tag = tag_pattern.replace("${pkgver}", new_ver)
    api_ver = vars_.get("_github_api_version", "2026-03-10")
    changelog_file = pkg_dir / f"{pkg_name}.changelog"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "generate-changelog.py"),
            github_repo,
            tag,
            str(changelog_file),
            api_ver,
        ],
        check=False,
    )
    if changelog_file.is_file() and "changelog" not in vars_:
        _log("  -> Injecting changelog variable")
        vars_["changelog"] = changelog_file.name


def _compute_checksums(vars_: dict, pkg_dir: Path) -> None:
    _log("  -> Computing checksums")
    sources = vars_.get("source", [])
    if not sources:
        return

    # Use existing checksum type or default to sha256
    checksum_key = None
    for key in _CHECKSUM_KEYS:
        if key in vars_:
            checksum_key = key
            break
    if checksum_key is None:
        checksum_key = "sha256sums"

    hashes = []
    for src in sources:
        filename = src.get("filename", "")
        url = src.get("url", "")
        if _is_vcs_url(url) and not _is_pinned(url):
            hashes.append("SKIP")
            continue

        # Local file (filename is not a URL)
        if not filename.startswith(
            ("http://", "https://", "git+", "svn+", "hg+", "bzr+")
        ):
            filepath = pkg_dir / filename
            if filepath.is_file():
                h = hashlib.sha256(filepath.read_bytes()).hexdigest()
                hashes.append(h)
                continue

        # URL source — download and hash in memory
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "sync-package/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                h = hashlib.sha256(resp.read()).hexdigest()
                hashes.append(h)
        except Exception as e:
            _log(f"    -> WARN: cannot fetch {url}: {e}")
            hashes.append("SKIP")

    vars_[checksum_key] = hashes


# ── validation & render ───────────────────────────────────────────────────


def _render_pkgbuild(vars_: dict, funcs: dict) -> str:
    """Render structured vars_ and funcs to standard PKGBUILD(5) text."""
    lines: list[str] = []

    # Maintainer / Contributors
    maint = vars_.get("maintainer", "")
    if maint:
        lines.append(f"# Maintainer: {maint}")
    for c in vars_.get("contributor", []) or []:
        lines.append(f"# Contributor: {c}")
    if lines:
        lines.append("")

    # Custom variables
    for key in (
        "_deploy_aur",
        "_pkgname",
        "_githubname",
        "_upstream_aur_pkg",
        "_upstream_arch_repo",
        "_demote_upstream_maintainer",
        "_auto_merge_build",
        "_use_common_gemini_settings",
        "_repo_subarch",
        "_tag",
        "_npmscope",
        "_npmname",
        "_npmver",
    ):
        val = vars_.get(key)
        if val is None or val is False or val == "":
            continue
        if isinstance(val, bool):
            lines.append(f"{key}=true")
        else:
            lines.append(f'{key}="{val}"')

    # PREREVIEW marker
    prereview = vars_.get("_prereview")
    if prereview:
        lines.append(f"# PREREVIEW: {prereview}")
        lines.append(
            "# Review the diff, verify build, then remove this marker to unblock release."
        )

    # Identity & versioning
    for key in ("pkgname", "pkgver"):
        if vars_.get(key):
            lines.append(f"{key}={vars_[key]}")
    lines.append(f"pkgrel={vars_.get('pkgrel', 1)}")
    if vars_.get("epoch") is not None:
        lines.append(f"epoch={vars_['epoch']}")
    if vars_.get("pkgdesc"):
        lines.append(f"pkgdesc={_q(vars_['pkgdesc'])}")

    # Metadata
    if vars_.get("arch"):
        lines.append(f"arch=({' '.join(_q(a) for a in vars_['arch'])})")
    if vars_.get("url"):
        lines.append(f"url='{vars_['url']}'")
    if vars_.get("license"):
        lines.append(f"license=({' '.join(_q(l) for l in vars_['license'])})")
    if vars_.get("groups"):
        lines.append(f"groups=({' '.join(_q(g) for g in vars_['groups'])})")

    # Dependencies
    for key in ("depends", "makedepends", "checkdepends"):
        val = vars_.get(key)
        if val:
            lines.append(f"{key}=({' '.join(_q(d) for d in val)})")

    # Optdepends
    opt = vars_.get("optdepends")
    if opt:
        items = []
        for o in opt:
            name = o.get("name", "")
            desc = o.get("desc", "")
            items.append(_q(f"{name}: {desc}" if desc else name))
        lines.append(f"optdepends=({' '.join(items)})")

    # Provides/Conflicts/Replaces
    for key in ("provides", "conflicts", "replaces"):
        val = vars_.get(key)
        if val:
            lines.append(f"{key}=({' '.join(_q(v) for v in val)})")

    # Config
    if vars_.get("backup"):
        lines.append(f"backup=({' '.join(_q(b) for b in vars_['backup'])})")
    if vars_.get("install"):
        lines.append(f"install={vars_['install']}")
    if vars_.get("options"):
        lines.append(f"options=({' '.join(_q(o) for o in vars_['options'])})")
    if vars_.get("changelog"):
        lines.append(f"changelog={vars_['changelog']}")

    # Source
    sources = vars_.get("source")
    if sources:
        items = []
        for s in sources:
            filename = s.get("filename", "")
            url = s.get("url", "")
            if filename and filename != url:
                items.append(f'"{filename}::{url}"')
            else:
                items.append(f'"{url}"')
        lines.append(f"source=({' '.join(items)})")

    # Checksums — use first available
    checksum_key = None
    for key in _CHECKSUM_KEYS:
        if key in vars_:
            checksum_key = key
            break
    if checksum_key and vars_.get(checksum_key):
        items = []
        for c in vars_[checksum_key]:
            items.append(f"'{c}'")
        lines.append(f"{checksum_key}=({' '.join(items)})")

    # validpgpkeys, noextract
    for key in ("validpgpkeys", "noextract"):
        val = vars_.get(key)
        if val:
            lines.append(f"{key}=({' '.join(_q(v) for v in val)})")

    # Lifecycle functions
    func_order = [
        ("pkgver", "pkgver"),
        ("prepare", "prepare"),
        ("build", "build"),
        ("check", "check"),
        ("package", "package"),
    ]
    for func_key, func_name in func_order:
        body = funcs.get(func_key)
        if body:
            lines.append("")
            lines.append(f"{func_name}() {{")
            for bline in body.strip().split("\n"):
                lines.append(f"    {bline}")
            lines.append("}")

    return "\n".join(lines) + "\n"


def _q(s: str) -> str:
    """Quote a value for PKGBUILD output. Single-quotes if needed."""
    if not s:
        return "''"
    if " " not in s and "'" not in s and '"' not in s:
        return s
    return f"'{s}'"


def _validate(vars_: dict, funcs: dict, pkg_dir: Path) -> bool:
    """Write package.pkl and validate with pkl eval --format json."""
    pkl_text = write_pkl_module(vars_, funcs)
    pkl_file = pkg_dir / "package.pkl"
    pkl_file.write_text(pkl_text)

    result = subprocess.run(
        ["pkl", "eval", str(pkl_file), "--format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _log(f"FAIL: Pkl validation error:\n{result.stderr}")
        return False
    return True


# ── variant consistency ───────────────────────────────────────────────────


def _check_variant_consistency(vars_: dict, pkg_name: str) -> None:
    pkgname_val = vars_.get("_pkgname")
    if not pkgname_val:
        return
    current_desc = vars_.get("pkgdesc", "")

    packages_dir = REPO_ROOT / "packages"
    for sibling_pkgbuild in sorted(packages_dir.glob("*/PKGBUILD")):
        sibling_name = sibling_pkgbuild.parent.name
        if sibling_name == pkg_name:
            continue
        try:
            sib_vars, _ = load_pkgbuild(str(sibling_pkgbuild))
        except Exception:
            continue
        if sib_vars.get("_pkgname") != pkgname_val:
            continue
        if sib_vars.get("pkgdesc", "") != current_desc:
            _log(
                f"::warning::pkgdesc differs from other {pkgname_val} variants. "
                f"Run validate-pkgbuilds-pkl.py to see full details."
            )
            break


# ── main ───────────────────────────────────────────────────────────────────


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pkg_name> <new_ver>", file=sys.stderr)
        sys.exit(1)

    pkg_name_raw = sys.argv[1]
    new_ver = sys.argv[2]

    # Resolve actual package directory by stripping tracking suffixes
    pkg_name = pkg_name_raw.removesuffix("-arch").removesuffix("-aur")
    pkg_dir = REPO_ROOT / "packages" / pkg_name

    _log(
        f"==> Synchronizing {pkg_name} (Triggered by {pkg_name_raw}) to version {new_ver}"
    )

    if not pkg_dir.is_dir():
        _log(f"::error::Package directory {pkg_dir} not found!")
        sys.exit(1)

    # Load current PKGBUILD
    vars_, funcs = load_pkgbuild(str(pkg_dir / "PKGBUILD"))

    # 0. Upstream merge logic
    upstream_changed = False
    upstream_url, base_url = _resolve_upstream(vars_)

    if upstream_url and base_url:
        fetched, changed = _fetch_upstream(upstream_url, base_url, pkg_dir)
        cache = pkg_dir / ".PKGBUILD.upstream"
        if fetched and changed and cache.exists():
            _log("  -> Upstream PKGBUILD changed, classifying and merging...")

            # Classify changes
            old_vars, _ = load_pkgbuild(str(pkg_dir / ".PKGBUILD.upstream"))
            new_vars, _ = load_pkgbuild(str(pkg_dir / "PKGBUILD.new"))
            events, build_changed = _classify_changes(old_vars, new_vars)
            if events:
                _log(f"  -> Upstream changes detected: {sorted(events)}")
                _log(f"  -> Review required: {['BUILD'] if build_changed else '[]'}")

            # Download new upstream assets
            _fetch_assets((pkg_dir / "PKGBUILD.new").read_text(), base_url, pkg_dir)

            # Protected merge
            vars_, funcs, ok = _merge_with_identity(vars_, funcs, pkg_dir)
            if not ok:
                sys.exit(1)

            _apply_prereview_marker(vars_, build_changed, new_ver)
            upstream_changed = True

        elif fetched and changed:
            # Initial bootstrap — cache doesn't exist yet
            _log("  -> Initial upstream tracking setup.")
            _fetch_assets((pkg_dir / "PKGBUILD.new").read_text(), base_url, pkg_dir)
            (pkg_dir / "PKGBUILD.new").rename(pkg_dir / ".PKGBUILD.upstream")
            upstream_changed = True

    # 1. Version update
    _log("  -> Updating versions in PKGBUILD")
    _bump_version(vars_, pkg_name_raw, pkg_name, new_ver, upstream_changed)

    # 1.5. Package-specific hook
    _run_update_hook(pkg_dir, new_ver)

    # 1.6. Shared assets
    _sync_shared_assets(vars_, pkg_dir)

    # 2. Changelog
    _generate_changelog(vars_, pkg_dir, pkg_name, new_ver)

    # 3. Checksums
    _compute_checksums(vars_, pkg_dir)

    # 4. Validate and render
    if not _validate(vars_, funcs, pkg_dir):
        sys.exit(1)

    (pkg_dir / "PKGBUILD").write_text(_render_pkgbuild(vars_, funcs))

    # 5. Variant consistency
    _check_variant_consistency(vars_, pkg_name)

    _log(f"==> Synchronization complete for {pkg_name}")


if __name__ == "__main__":
    main()
