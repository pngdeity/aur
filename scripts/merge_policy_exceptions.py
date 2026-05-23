#!/usr/bin/env python3
"""Merge per-package policy_exceptions.yaml files into manifest.json."""
from __future__ import annotations

import argparse
import json
import os
import sys
from glob import glob


def merge_exceptions(manifest_path: str, packages_dir: str) -> None:
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read manifest: {e}", file=sys.stderr)
        sys.exit(1)

    exceptions: dict[str, dict[str, str]] = {}
    for yf in sorted(glob(f"{packages_dir}/*/policy_exceptions.yaml")):
        pkgname = os.path.basename(os.path.dirname(yf))
        try:
            import yaml
            with open(yf) as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"ERROR: cannot parse {yf}: {e}", file=sys.stderr)
            sys.exit(1)
        if data and "exceptions" in data:
            for exc in data["exceptions"]:
                rule = exc["rule"]
                reason = exc.get("reason", "")
                exceptions.setdefault(pkgname, {})[rule] = reason

    existing = manifest.setdefault("exceptions", {})
    existing.update(exceptions)

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    if exceptions:
        print(f"Merged exceptions for {len(exceptions)} package(s):")
        for pkg, rules in sorted(exceptions.items()):
            for rule, reason in sorted(rules.items()):
                print(f"  {pkg}: {rule} — {reason}")
    else:
        print("No per-package policy_exceptions.yaml files found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge policy exceptions into manifest")
    parser.add_argument("manifest_path", help="Path to manifest.json")
    parser.add_argument("packages_dir", help="Path to packages/ directory")
    args = parser.parse_args()
    merge_exceptions(args.manifest_path, args.packages_dir)
