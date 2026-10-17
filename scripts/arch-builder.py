#!/usr/bin/env python3
"""Standardized Arch Linux package builder for monorepos.

Builds a single package directory using makepkg inside a Docker container
(fresh container per job in CI). For strict clean-chroot verification,
use 'pkgctl build' locally — see AGENTS.md §3.

Usage:
    python arch-builder.py <package_dir> <version>

Exit codes:
    0 — build succeeded
    1 — usage error or build failure
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(
    cmd: list[str], cwd: str | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check)


def import_pgp_keys(pkg_dir: str) -> None:
    result = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=pkg_dir,
        capture_output=True,
        text=True,
    )
    keys = re.findall(r"^\s*validpgpkeys = (.*)", result.stdout, re.MULTILINE)
    for key_line in keys:
        for key in key_line.split():
            key = key.strip("'\"")
            print(f"  -> Importing PGP Key: {key}")
            try:
                subprocess.run(["gpg", "--recv-keys", key], check=False)
            except subprocess.CalledProcessError:
                print(f"    ! Warning: Failed to fetch PGP key {key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Arch Linux package")
    parser.add_argument("pkg_dir", help="Path to package directory")
    parser.add_argument(
        "version",
        nargs="?",
        default=None,
        help="Optional version string (deprecated/ignored)",
    )
    args = parser.parse_args()

    pkg_dir = args.pkg_dir
    pkg_name = Path(pkg_dir).name
    print(f"==> Building package in: {pkg_dir}")

    import time

    os.environ.setdefault("SOURCE_DATE_EPOCH", str(int(time.time())))

    base_build_dir = os.environ.get("BUILDDIR", "/tmp/makepkg-build")
    base_pkg_dest = os.environ.get("PKGDEST", "/tmp/makepkg-pkg")
    base_src_dest = os.environ.get("SRCDEST", "/tmp/makepkg-src")
    dist_dir = Path(os.environ.get("DISTDIR", "/tmp/makepkg-dist"))

    # Isolate build directories per package
    build_dir = Path(base_build_dir) / pkg_name
    pkg_dest = Path(base_pkg_dest) / pkg_name
    src_dest = Path(base_src_dest) / pkg_name

    for d in (build_dir, pkg_dest, src_dest, dist_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Clean any stale artifacts in pkg_dest before building
    for old_pkg in pkg_dest.glob("*.pkg.tar.zst"):
        old_pkg.unlink()

    os.environ["BUILDDIR"] = str(build_dir)
    os.environ["PKGDEST"] = str(pkg_dest)
    os.environ["SRCDEST"] = str(src_dest)

    # System update (can be hoisted by setting SKIP_SYSUPDATE=1 in parent loop)
    if not os.environ.get("SKIP_SYSUPDATE"):
        subprocess.run(["sudo", "pacman", "-Syu", "--noconfirm"], check=True)

    import_pgp_keys(pkg_dir)

    print("  -> Starting makepkg...")
    try:
        subprocess.run(
            [
                "makepkg",
                "--syncdeps",
                "--noconfirm",
                "--noprogressbar",
                "--needed",
                "--clean",
                "--rmdeps",
            ],
            cwd=pkg_dir,
            check=True,
        )
    finally:
        # Clean up build directory to conserve disk space
        shutil.rmtree(build_dir, ignore_errors=True)

    artifacts = list(pkg_dest.glob("*.pkg.tar.zst"))
    for artifact in artifacts:
        dst = dist_dir / artifact.name
        shutil.copy2(artifact, dst)
        print(f"  -> Copied {artifact.name} to {dst}")

    print(f"==> Finished building {pkg_dir}")


if __name__ == "__main__":
    main()
