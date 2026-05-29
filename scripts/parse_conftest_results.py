#!/usr/bin/env python3
"""Parse conftest JSON output and print a human-readable summary."""
from __future__ import annotations

import argparse
import json
import sys


def parse_results(results_path: str) -> int:
    try:
        with open(results_path) as f:
            results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: cannot read results: {e}", file=sys.stderr)
        return 1

    failures = 0
    warnings = 0
    for r in results:
        for f_msg in r.get("failures", []):
            failures += 1
            print(f"  FAIL: {f_msg['msg']}")
        for w_msg in r.get("warnings", []):
            warnings += 1
            print(f"  WARN: {w_msg['msg']}")

    if failures == 0 and warnings == 0:
        print("conftest: PASS (no violations)")
        return 0
    elif failures > 0:
        print(f"conftest: FAIL ({failures} deny violations remain after exceptions)")
        return 1
    else:
        print(f"conftest: PASS ({warnings} warnings remain — no deny violations)")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse conftest JSON results")
    parser.add_argument("results_path", help="Path to conftest JSON output file")
    args = parser.parse_args()
    sys.exit(parse_results(args.results_path))
