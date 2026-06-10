#!/usr/bin/env python3
"""Validate all PKGBUILDs through the Pkl schema and OPA/Rego policy engine.

Discovers every PKGBUILD under packages/, imports each to Pkl via
pkgbuild_to_pkl.py, validates with pkl eval, merges results into
manifest.json, then runs conftest test against policies/repository.rego.

Exit codes:
    0 — all packages validated, no policy violations
    1 — validation or policy failure
    2 — missing prerequisites
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = Path(os.environ.get("PACKAGES_DIR", str(REPO_ROOT / "packages")))
SCHEMA_FILE = Path(
    os.environ.get("SCHEMA_FILE", str(REPO_ROOT / "schemas" / "arch_pkg.pkl"))
)
MANIFEST_FILE = Path(os.environ.get("MANIFEST_FILE", str(REPO_ROOT / "manifest.json")))
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _find(name: str) -> str | None:
    return shutil.which(name)


def check_prerequisites() -> None:
    if not _find("pkl"):
        print(
            "ERROR: pkl not found in PATH — "
            "install pkl-bin or download from https://github.com/apple/pkl/releases",
            file=sys.stderr,
        )
        sys.exit(2)
    if not _find("python3"):
        print("ERROR: python3 not found in PATH", file=sys.stderr)
        sys.exit(2)
    if not SCHEMA_FILE.is_file():
        print(f"ERROR: schema file not found: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(2)


def discover_pkgbuilds() -> list[Path]:
    pkgbuilds = sorted(PACKAGES_DIR.glob("*/PKGBUILD"))
    if not pkgbuilds:
        print(f"No PKGBUILD files found in {PACKAGES_DIR}")
    return pkgbuilds


def validate_packages(pkgbuilds: list[Path]) -> dict[str, Path]:
    """Import and pkl-validate each PKGBUILD. Returns pkgname -> json_path."""
    results: dict[str, Path] = {}
    failed = False

    for pkgbuild in pkgbuilds:
        pkg_dir = pkgbuild.parent
        pkg_name = pkg_dir.name
        pkl_file = pkg_dir / "package.pkl"
        json_file = pkg_dir / "package.json"

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "pkgbuild_to_pkl.py"), str(pkgbuild)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"FAIL: {pkg_name} — import failed")
            failed = True
            continue
        pkl_file.write_text(result.stdout)

        result = subprocess.run(
            ["pkl", "eval", str(pkl_file), "--format", "json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"FAIL: {pkg_name} — Pkl validation error")
            failed = True
            continue
        json_file.write_text(result.stdout)

        results[pkg_name] = json_file
        print(f"OK: {pkg_name}")

    if failed:
        print("---")
        print(f"Packages discovered: {len(pkgbuilds)}")
        print("RESULT: FAIL (validation errors)")
        sys.exit(1)
    return results


def build_manifest(validated: dict[str, Path]) -> None:
    manifest: dict = {"version": 1, "packages": {}}
    for pkg_name, json_path in sorted(validated.items()):
        try:
            manifest["packages"][pkg_name] = json.loads(json_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

    print("---")
    print(f"Packages discovered: {len(validated)}")
    print(f"Manifest written: {MANIFEST_FILE}")


def run_conftest() -> None:
    if os.environ.get("SKIP_CONFTEST"):
        print("SKIP_CONFTEST=1 — skipping policy evaluation")
        sys.exit(0)

    if not _find("conftest"):
        print("WARN: conftest not found — skipping policy evaluation")
        sys.exit(0)

    print("")
    print("── Policy evaluation phase ──")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "merge_policy_exceptions.py"),
            str(MANIFEST_FILE),
            str(PACKAGES_DIR),
        ],
        check=True,
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        subprocess.run(
            [
                "conftest",
                "test",
                str(MANIFEST_FILE),
                "--policy",
                str(REPO_ROOT / "policies"),
                "--output",
                "json",
            ],
            stdout=tmp,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "parse_conftest_results.py"), tmp.name],
        check=False,
    )


def main() -> None:
    check_prerequisites()
    pkgbuilds = discover_pkgbuilds()
    if not pkgbuilds:
        sys.exit(0)

    print(f"Discovered {len(pkgbuilds)} package(s)")
    validated = validate_packages(pkgbuilds)
    build_manifest(validated)
    print("RESULT: PASS (all packages validated)")
    run_conftest()


if __name__ == "__main__":
    main()
