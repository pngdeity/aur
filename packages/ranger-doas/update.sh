#!/usr/bin/env python3
"""Regenerate doas-substitution.patch from upstream ranger source.

Called by sync-package.py after upstream merge. Clones the ranger repo
at the new version tag, applies sudo→doas substitutions to source files,
and generates a fresh patch. Idempotent — re-running produces the same patch.

Usage:
    python update.sh <new_version>

Exit codes:
    0 — patch regenerated successfully
    1 — git clone or diff failure
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_URL = "https://github.com/ranger/ranger.git"
PATCH_FILE = "doas-substitution.patch"

# Files to blanket-replace sudo→doas (documentation, configs)
_GLOB_FILES = ("README.md", "*.pod", "*.conf", "CHANGELOG.md", "*.svg")


def _replace_in_file(path: Path, old: bytes, new: bytes) -> None:
    data = path.read_bytes()
    if old in data:
        path.write_bytes(data.replace(old, new))


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <new_version>", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1]
    pkg_dir = Path.cwd()
    patch_path = pkg_dir / PATCH_FILE
    print(f"  -> Regenerating {PATCH_FILE} for ranger v{version}")

    tmp = Path(tempfile.mkdtemp(prefix="ranger-update-"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", f"v{version}", UPSTREAM_URL, str(tmp)],
            check=True,
            capture_output=True,
            text=True,
        )

        # Apply sudo→doas substitutions
        _replace_in_file(tmp / "ranger/core/runner.py", b"sudo", b"doas")
        _replace_in_file(
            tmp / "ranger/ext/rifle.py",
            b"['sudo', '-E', 'su', 'root', '-mc']",
            b"['doas', '/bin/sh', '-c']",
        )

        for pattern in _GLOB_FILES:
            for f in tmp.rglob(pattern):
                _replace_in_file(f, b"sudo", b"doas")

        # Generate patch
        diff = subprocess.run(
            ["git", "-C", str(tmp), "diff"],
            check=True,
            capture_output=True,
            text=True,
        )
        patch_path.write_text(diff.stdout)
        print(f"  -> Wrote {patch_path} ({len(diff.stdout)} bytes)")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
