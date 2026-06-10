#!/usr/bin/env python3
"""Process a repo PKGBUILD into AUR-compatible output and push to the AUR.

Inlines source directives, strips repo-local variables and PREREVIEW
markers, generates .SRCINFO, runs namcap, and pushes to aur.archlinux.org.

Usage:
    python aur-deploy.py <package_dir> [--dry-run]

Exit codes:
    0 — AUR up to date or deployment skipped or successful
    1 — error (missing dir, SSH failure, variant block, etc.)
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PKGVAR = SCRIPTS_DIR / "pkgvar"

REPO_LOCAL_VARS = [
    "_deploy_aur",
    "_demote_upstream_maintainer",
    "_upstream_aur_pkg",
    "_upstream_arch_repo",
    "_use_common_gemini_settings",
    "_repo_subarch",
    "_auto_merge_build",
]


def pkgvar(pkgbuild: Path, var: str) -> str:
    result = subprocess.run(
        [str(PKGVAR), str(pkgbuild), var],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def check_ssh() -> None:
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=10",
            "-q",
            "-T",
            "aur@aur.archlinux.org",
            "help",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            "::error::Cannot connect to aur.archlinux.org. "
            "Ensure AUR_SSH_PRIVATE_KEY is loaded in ssh-agent."
        )
        print("::error::Run: eval $(ssh-agent) && ssh-add /path/to/aur-deploy-key")
        sys.exit(1)
    print("  -> SSH connection verified.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy a PKGBUILD to the AUR")
    parser.add_argument("pkg_dir", help="Path to package directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without pushing"
    )
    args = parser.parse_args()

    pkg_dir = Path(args.pkg_dir)
    if not pkg_dir.is_dir():
        print(f"Usage: {sys.argv[0]} <package_dir> [--dry-run]", file=sys.stderr)
        sys.exit(1)

    pkg_name = pkg_dir.name
    pkgbuild = pkg_dir / "PKGBUILD"
    print(f"==> AUR Deploy: {pkg_name}")

    source_directive_re = re.compile(r'^source "\.\./')
    deploys_aur_re = re.compile(r"^_deploy_aur=true")
    subarch_re = re.compile(r"^_repo_subarch=")
    prereview_re = re.compile(r"^# PREREVIEW:")
    review_re = re.compile(r"^# Review the diff")

    # Safety gate
    with open(pkgbuild) as f:
        content = f.read()

    if subarch_re.search(content):
        print(
            f"::error::Package {pkg_name} has _repo_subarch set. "
            "Variant PKGBUILDs must not deploy to AUR."
        )
        sys.exit(1)

    if not deploys_aur_re.search(content):
        print("  -> _deploy_aur not set, skipping AUR deployment.")
        sys.exit(0)

    # Produce AUR-compatible PKGBUILD
    aur_dir = Path(tempfile.mkdtemp(prefix=f"aur-deploy-{pkg_name}-"))
    aur_pkgbuild = aur_dir / "PKGBUILD"
    shutil.copy(pkgbuild, aur_pkgbuild)
    print("  -> Producing AUR-compatible PKGBUILD")

    # 1. Inline source directives
    print("  -> Resolving source directives")
    parent_dir = pkgbuild.parent
    while True:
        text = aur_pkgbuild.read_text()
        m = source_directive_re.search(text)
        if not m:
            break
        relative = m.group(0).removeprefix('source "')
        sourced_abs = (parent_dir / relative).resolve()
        if not sourced_abs.is_file():
            print(f"::error::Sourced file not found: {sourced_abs}")
            sys.exit(1)

        sourced_text = sourced_abs.read_text()
        text = text.replace(f'source "{relative}"', sourced_text)
        aur_pkgbuild.write_text(text)

    # 2. Strip repo-local variables
    print("  -> Stripping repo-local variables")
    lines = aur_pkgbuild.read_text().splitlines(keepends=True)
    lines = [
        line
        for line in lines
        if not any(line.startswith(f"{v}=") for v in REPO_LOCAL_VARS)
    ]
    aur_pkgbuild.write_text("".join(lines))

    # 3. Strip PREREVIEW markers
    print("  -> Stripping PREREVIEW markers")
    lines = aur_pkgbuild.read_text().splitlines(keepends=True)
    lines = [
        line
        for line in lines
        if not prereview_re.match(line) and not review_re.match(line)
    ]
    aur_pkgbuild.write_text("".join(lines))

    # 4. Generate .SRCINFO
    print("  -> Generating .SRCINFO")
    result = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=str(aur_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"::error::makepkg --printsrcinfo failed: {result.stderr}")
        sys.exit(1)
    (aur_dir / ".SRCINFO").write_text(result.stdout)

    # 5. namcap
    print("  -> Running namcap on processed PKGBUILD")
    if shutil.which("namcap"):
        result = subprocess.run(
            ["namcap", str(aur_pkgbuild)],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print(result.stdout)
        if result.returncode != 0:
            print("  ::warning::namcap reported issues")
    else:
        print("  -> namcap not found, skipping")

    # Git operations
    aur_remote = f"ssh://aur@aur.archlinux.org/{pkg_name}.git"
    pkgver = pkgvar(aur_pkgbuild, "pkgver")
    pkgrel = pkgvar(aur_pkgbuild, "pkgrel")

    check_ssh()

    aur_clone = Path(tempfile.mkdtemp(prefix=f"aur-clone-{pkg_name}-"))
    result = subprocess.run(
        ["git", "clone", aur_remote, str(aur_clone)], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"::error::AUR repository for {pkg_name} does not exist.")
        print(
            f"::error::You must register the pkgbase '{pkg_name}' on https://aur.archlinux.org/ first."
        )
        sys.exit(1)
    print(f"  -> Cloned existing AUR repository for {pkg_name}")

    shutil.copy(aur_pkgbuild, aur_clone / "PKGBUILD")
    shutil.copy(aur_dir / ".SRCINFO", aur_clone / ".SRCINFO")

    subprocess.run(
        ["git", "add", "PKGBUILD", ".SRCINFO"], cwd=str(aur_clone), check=True
    )
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(aur_clone))
    if result.returncode == 0:
        print("  -> AUR repository already up to date (content identical).")
        sys.exit(0)

    commit_msg = f"{pkg_name}: update to {pkgver}-{pkgrel}"

    if args.dry_run:
        print("  -> Dry run: changes that would be pushed to AUR:")
        print(f"  -> Remote: {aur_remote}")
        print("  -> Files: PKGBUILD, .SRCINFO")
        print(f"  -> Commit message: {commit_msg}")
        print()
        subprocess.run(["git", "diff", "--cached", "--stat"], cwd=str(aur_clone))
        print()
        print("  -> Diff preview:")
        subprocess.run(["git", "diff", "--cached"], cwd=str(aur_clone))
        print()
        print("::notice::Dry run complete. No changes pushed.")
        return

    subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(aur_clone), check=True)
    subprocess.run(["git", "push"], cwd=str(aur_clone), check=True)
    print(f"  -> Pushed {commit_msg} to AUR.")
    print(f"==> AUR deployment complete for {pkg_name}")


if __name__ == "__main__":
    main()
