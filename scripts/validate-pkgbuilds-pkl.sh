#!/usr/bin/env bash
# scripts/validate-pkgbuilds-pkl.sh
# Orchestration wrapper: finds all PKGBUILDs, imports via pkgbuild_to_pkl.py,
# validates each with pkl eval --format json, merges results into manifest.json.
#
# Exit codes:
#   0 — all packages validated successfully
#   1 — validation failure (one or more packages failed)
#   2 — missing prerequisites
set -euo pipefail

PACKAGES_DIR="${PACKAGES_DIR:-packages}"
SCHEMA_FILE="${SCHEMA_FILE:-schemas/arch_pkg.pkl}"
MANIFEST_FILE="${MANIFEST_FILE:-manifest.json}"
FAILED=0
PACKAGE_COUNT=0

# ── Prerequisites check ──
if ! command -v pkl &>/dev/null; then
    echo "ERROR: pkl not found in PATH — install pkl-bin or download from https://github.com/apple/pkl/releases"
    exit 2
fi
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found in PATH"
    exit 2
fi
if [[ ! -f "$SCHEMA_FILE" ]]; then
    echo "ERROR: schema file not found: $SCHEMA_FILE"
    exit 2
fi

# ── Discover PKGBUILDs ──
shopt -s nullglob
pkgbuilds=("$PACKAGES_DIR"/*/PKGBUILD)
shopt -u nullglob

if [[ ${#pkgbuilds[@]} -eq 0 ]]; then
    echo "No PKGBUILD files found in $PACKAGES_DIR"
    exit 0
fi

echo "Discovered ${#pkgbuilds[@]} package(s)"

# ── Import + validate each package ──
for pkgbuild in "${pkgbuilds[@]}"; do
    pkg_dir="$(dirname "$pkgbuild")"
    pkg_name="$(basename "$pkg_dir")"
    pkl_file="$pkg_dir/package.pkl"
    json_file="$pkg_dir/package.json"
    PACKAGE_COUNT=$((PACKAGE_COUNT + 1))

    # Step a: Import PKGBUILD → Pkl
    if ! python3 scripts/pkgbuild_to_pkl.py "$pkgbuild" > "$pkl_file" 2>/dev/null; then
        echo "FAIL: $pkg_name — import failed"
        FAILED=1
        continue
    fi

    # Step b: Validate with pkl eval → JSON
    if ! pkl eval "$pkl_file" --format json > "$json_file" 2>/dev/null; then
        echo "FAIL: $pkg_name — Pkl validation error"
        FAILED=1
        continue
    fi

    echo "OK: $pkg_name"
done

# ── Merge results into manifest.json ──
echo "{ \"version\": 1, \"packages\": {" > "$MANIFEST_FILE"
first=true
for pkgbuild in "${pkgbuilds[@]}"; do
    pkg_dir="$(dirname "$pkgbuild")"
    pkg_name="$(basename "$pkg_dir")"
    json_file="$pkg_dir/package.json"

    if [[ ! -f "$json_file" ]]; then
        continue
    fi
    if [[ "$(wc -c < "$json_file")" -eq 0 ]]; then
        continue
    fi

    if [[ "$first" == true ]]; then
        first=false
    else
        echo -n "," >> "$MANIFEST_FILE"
    fi
    printf '\n"%s": ' "$pkg_name" >> "$MANIFEST_FILE"
    cat "$json_file" >> "$MANIFEST_FILE"
done
echo "" >> "$MANIFEST_FILE"
echo "}}" >> "$MANIFEST_FILE"

# ── Report ──
echo "---"
echo "Packages discovered: $PACKAGE_COUNT"
echo "Manifest written: $MANIFEST_FILE"

if [[ $FAILED -ne 0 ]]; then
    echo "RESULT: FAIL (validation errors)"
    exit 1
fi

echo "RESULT: PASS (all packages validated)"

# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Merge per-package policy exceptions into manifest.json
# ═══════════════════════════════════════════════════════════════════════
if [[ -n "${SKIP_CONFTEST:-}" ]]; then
    echo "SKIP_CONFTEST=1 — skipping policy evaluation"
    exit 0
fi

if ! command -v conftest &>/dev/null; then
    echo "WARN: conftest not found — skipping policy evaluation"
    exit 0
fi

echo ""
echo "── Policy evaluation phase ──"

python3 -c '
import json, os, sys, glob

manifest_path = sys.argv[1]
packages_dir = sys.argv[2]

with open(manifest_path) as f:
    manifest = json.load(f)

exceptions = {}
for yf in sorted(glob.glob(f"{packages_dir}/*/policy_exceptions.yaml")):
    pkgname = os.path.basename(os.path.dirname(yf))
    import yaml
    with open(yf) as f:
        data = yaml.safe_load(f)
    if data and "exceptions" in data:
        for exc in data["exceptions"]:
            rule = exc["rule"]
            reason = exc.get("reason", "")
            exceptions.setdefault(pkgname, {})[rule] = reason

manifest["exceptions"] = exceptions

with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

if exceptions:
    print(f"Merged exceptions for {len(exceptions)} package(s):")
    for pkg, rules in sorted(exceptions.items()):
        for rule, reason in sorted(rules.items()):
            print(f"  {pkg}: {rule} — {reason}")
else:
    print("No per-package policy_exceptions.yaml files found.")
' "$MANIFEST_FILE" "$PACKAGES_DIR"

echo ""

# ── Run conftest ──
CONFTEST_TMP="$(mktemp)"
trap 'rm -f "$CONFTEST_TMP"' EXIT

set +e
conftest test "$MANIFEST_FILE" --policy policies/ --output json > "$CONFTEST_TMP" 2>/dev/null
CONFTEST_EXIT=$?
set -e

python3 -c '
import json, sys, os

with open(sys.argv[1]) as f:
    results = json.load(f)

failures = 0
warnings = 0
for r in results:
    fname = r.get("filename", "?")
    for f_msg in r.get("failures", []):
        failures += 1
        msg = f_msg["msg"]
        print(f"  FAIL: {msg}")
    for w_msg in r.get("warnings", []):
        warnings += 1
        msg = w_msg["msg"]
        print(f"  WARN: {msg}")

if failures == 0 and warnings == 0:
    print("conftest: PASS (no violations)")
    sys.exit(0)
elif failures > 0:
    print(f"conftest: FAIL ({failures} deny violations remain after exceptions)")
    sys.exit(1)
else:
    print(f"conftest: PASS ({warnings} warnings remain — no deny violations)")
    sys.exit(0)
' "$CONFTEST_TMP"

rm -f "$CONFTEST_TMP"
trap - EXIT
