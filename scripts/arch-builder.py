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
    parser.add_argument("version", help="Version string")
    args = parser.parse_args()

    pkg_dir = args.pkg_dir
    print(f"==> Building package in: {pkg_dir}")

    os.environ.setdefault(
        "SOURCE_DATE_EPOCH",
        str(
            int(
                subprocess.run(
                    ["date", "+%s"], capture_output=True, text=True
                ).stdout.strip()
            )
        ),
    )

    build_dir = os.environ.get("BUILDDIR", "/tmp/makepkg-build")
    pkg_dest = os.environ.get("PKGDEST", "/tmp/makepkg-pkg")
    src_dest = os.environ.get("SRCDEST", "/tmp/makepkg-src")
    dist_dir = os.environ.get("DISTDIR", "/tmp/makepkg-dist")

    for d in (build_dir, pkg_dest, src_dest, dist_dir):
        os.makedirs(d, exist_ok=True)

    os.environ["BUILDDIR"] = build_dir
    os.environ["PKGDEST"] = pkg_dest
    os.environ["SRCDEST"] = src_dest

    subprocess.run(["sudo", "pacman", "-Syu", "--noconfirm"], check=True)
    import_pgp_keys(pkg_dir)

    print("  -> Starting makepkg...")
    subprocess.run(
        [
            "makepkg",
            "--syncdeps",
            "--noconfirm",
            "--noprogressbar",
            "--needed",
            "--clean",
        ],
        cwd=pkg_dir,
        check=True,
    )

    dist = Path(dist_dir)
    pkg_dest_path = Path(pkg_dest)
    for artifact in pkg_dest_path.glob("*.pkg.tar.zst"):
        dst = dist / artifact.name
        dst.write_bytes(artifact.read_bytes())
        print(f"  -> Copied {artifact.name} to {dst}")

    print(f"==> Finished building {pkg_dir}")


if __name__ == "__main__":
    main()
