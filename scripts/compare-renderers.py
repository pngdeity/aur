"""Compare Pkl renderPKGBUILD() against Python renderer output.

Phase 1 gate verifier — proves renderPKGBUILD() can replace pkgbuild_renderer.py.
Accepts expected divergences where Pkl is more correct than Python.
Deleted in Phase 6 along with the Python renderer.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pkgbuild_loader import load_pkgbuild
from pkgbuild_renderer import render_pkgbuild

REPO_ROOT = Path(__file__).resolve().parent.parent
PKL_EVAL = ["pkl", "eval", "-x", "output.value.renderPKGBUILD()"]

# Packages where Pkl is more correct than Python (emits arch-specific sources/checksums
# that the Python renderer silently drops).
ARCH_PKGS = {"pkl-lsp-bin", "apm-bin", "go-regal-bin"}
ARCH_PREFIXES = (
    "source_x86_64=",
    "source_aarch64=",
    "sha512sums_x86_64=",
    "sha512sums_aarch64=",
)


def main() -> None:
    packages = sorted(
        p.name
        for p in (REPO_ROOT / "packages").iterdir()
        if p.is_dir() and (p / "PKGBUILD").exists() and (p / "package.pkl").exists()
    )

    total = 0
    expected = 0
    failures = 0

    for pkg_name in packages:
        pkg_dir = REPO_ROOT / "packages" / pkg_name
        total += 1

        v, f = load_pkgbuild(str(pkg_dir / "PKGBUILD"))
        py_output = render_pkgbuild(v, f)

        result = subprocess.run(
            PKL_EVAL + [str(pkg_dir / "package.pkl")],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"PKL_ERR: {pkg_name}")
            print(result.stderr)
            failures += 1
            continue

        pkl_output = result.stdout

        if py_output == pkl_output:
            print(f"OK: {pkg_name}")
        elif pkg_name in ARCH_PKGS:
            pkl_filtered = "\n".join(
                line
                for line in pkl_output.split("\n")
                if not line.startswith(ARCH_PREFIXES)
            )
            if py_output != pkl_filtered:
                print(f"UNEXPECTED_DIFF: {pkg_name}")
                failures += 1
            else:
                print(f"EXPECTED_DIFF: {pkg_name}")
                expected += 1
        else:
            print(f"DIFF: {pkg_name}")
            failures += 1

    print(f"---")
    print(f"{total} packages, {expected} expected divergences, {failures} failures")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
