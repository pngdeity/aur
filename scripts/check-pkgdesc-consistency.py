#!/usr/bin/env python3
"""Validate pkgdesc consistency across package variant groups.

All packages sharing the same _pkgname must have identical pkgdesc strings.
Outputs findings to stdout and errors as GitHub Actions annotations when
running in CI mode.

Usage:
    python check-pkgdesc-consistency.py [--ci]

Exit codes:
    0 — all variant groups consistent
    1 — violations found
    2 — usage error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PKGVAR = REPO_ROOT / "scripts" / "pkgvar"
EXCLUDE_DIRS = {"template", "openproject-cli"}


def pkgvar(pkgbuild: Path, var: str) -> str:
    result = subprocess.run(
        [str(PKGVAR), str(pkgbuild), var],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def format_desc(desc: str, max_len: int = 22) -> str:
    return f'"{desc}"'


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check pkgdesc consistency across variant groups"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Output in GitHub Actions annotation format",
    )
    if sys.argv[1:] and sys.argv[1] in ("-h", "--help"):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    print("==> Checking pkgdesc consistency across variant groups...")

    by_pkgname: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    group_members: dict[str, int] = defaultdict(int)

    packages_dir = REPO_ROOT / "packages"
    for pkgbuild in sorted(packages_dir.glob("*/PKGBUILD")):
        pkg_dir = pkgbuild.parent.name
        if pkg_dir in EXCLUDE_DIRS:
            continue

        pkgname_val = pkgvar(pkgbuild, "_pkgname")
        desc_val = pkgvar(pkgbuild, "pkgdesc")
        if not pkgname_val or not desc_val:
            continue

        by_pkgname[pkgname_val][desc_val].append(pkg_dir)
        group_members[pkgname_val] += 1

    violations = False
    for pkgname_val in sorted(group_members):
        if group_members[pkgname_val] <= 1:
            continue

        descs = by_pkgname[pkgname_val]
        if len(descs) <= 1:
            print(f"  \u2713 {pkgname_val}: consistent")
            continue

        violations = True
        print(f"  \u2717 {pkgname_val}: pkgdesc mismatch")
        for desc_val, dirs in sorted(descs.items()):
            for d in sorted(dirs):
                if args.ci:
                    print(
                        f"::warning file=packages/{d}/PKGBUILD"
                        f"::pkgdesc differs from other {pkgname_val} variants"
                    )
                print(f'    {d:<22s} "{desc_val}"')

    if violations:
        print(
            "\n::error::pkgdesc consistency violations found. "
            "All packages sharing the same _pkgname must have identical pkgdesc."
        )
        sys.exit(1)

    print("\n  -> All variant groups consistent.")


if __name__ == "__main__":
    main()
