#!/usr/bin/env python3
"""Convert an Arch Linux PKGBUILD into a Pkl amending module.

Usage:
    python3 scripts/pkgbuild_to_pkl.py packages/opendoas/PKGBUILD > /tmp/opendoas.pkl

Loads the PKGBUILD via pkgbuild_loader, writes Pkl output via pkl_writer.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pkgbuild_loader import load_pkgbuild
from pkl_writer import write_pkl_module


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <PKGBUILD_PATH>", file=sys.stderr)
        sys.exit(1)

    pkgbuild_path = sys.argv[1]

    # Validate the input path
    p = Path(pkgbuild_path).resolve()
    if not p.is_file():
        print(f"ERROR: not a file: {pkgbuild_path}", file=sys.stderr)
        sys.exit(1)
    if p.name != "PKGBUILD":
        print(f"ERROR: file must be named PKGBUILD, got: {p.name}", file=sys.stderr)
        sys.exit(1)

    try:
        vars_, funcs = load_pkgbuild(pkgbuild_path)
    except subprocess.TimeoutExpired:
        print("Error: bash subprocess timed out", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: invalid value in PKGBUILD — {e}", file=sys.stderr)
        sys.exit(1)

    output = write_pkl_module(vars_, funcs)
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
