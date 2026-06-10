#!/usr/bin/env python3
"""Install required validation tools (pkl + conftest) via system package manager.

On Arch Linux, uses yay to install pkl-bin and conftest from AUR.
Verifies both tools are on PATH after installation.

Exit codes:
    0 — all tools present or installed successfully
    1 — installation failed or tools not found after install
"""

from __future__ import annotations

import shutil
import subprocess
import sys


def _find(name: str) -> str | None:
    return shutil.which(name)


def install_tools() -> bool:
    result = subprocess.run(
        ["yay", "-S", "--noconfirm", "pkl-bin", "conftest"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: yay install failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def main() -> None:
    missing = []
    if not _find("pkl"):
        missing.append("pkl")
    if not _find("conftest"):
        missing.append("conftest")

    if missing:
        print(f"Missing tools: {' '.join(missing)}")
        print("Attempting install via yay...")
        if not install_tools():
            sys.exit(1)

    for tool in ("pkl", "conftest"):
        if not _find(tool):
            print(f"ERROR: {tool} not found on PATH after install", file=sys.stderr)
            sys.exit(1)

    subprocess.run(["pkl", "--version"])
    subprocess.run(["conftest", "--version"])


if __name__ == "__main__":
    main()
