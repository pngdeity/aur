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
	if ! python3 scripts/pkgbuild_to_pkl.py "$pkgbuild" >"$pkl_file"; then
		echo "FAIL: $pkg_name — import failed"
		FAILED=1
		continue
	fi

	# Step b: Validate with pkl eval → JSON
	if ! pkl eval "$pkl_file" --format json >"$json_file"; then
		echo "FAIL: $pkg_name — Pkl validation error"
		FAILED=1
		continue
	fi

	echo "OK: $pkg_name"
done

# ── Merge results into manifest.json ──
echo "{ \"version\": 1, \"packages\": {" >"$MANIFEST_FILE"
first=true
for pkgbuild in "${pkgbuilds[@]}"; do
	pkg_dir="$(dirname "$pkgbuild")"
	pkg_name="$(basename "$pkg_dir")"
	json_file="$pkg_dir/package.json"

	if [[ ! -f "$json_file" ]]; then
		continue
	fi
	if [[ "$(wc -c <"$json_file")" -eq 0 ]]; then
		continue
	fi

	if [[ "$first" == true ]]; then
		first=false
	else
		echo -n "," >>"$MANIFEST_FILE"
	fi
	printf '\n"%s": ' "$pkg_name" >>"$MANIFEST_FILE"
	cat "$json_file" >>"$MANIFEST_FILE"
done
echo "" >>"$MANIFEST_FILE"
echo "}}" >>"$MANIFEST_FILE"

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

python3 scripts/merge_policy_exceptions.py "$MANIFEST_FILE" "$PACKAGES_DIR"

echo ""

# ── Run conftest ──
CONFTEST_TMP="$(mktemp)"
trap 'rm -f "$CONFTEST_TMP"' EXIT

set +e
conftest test "$MANIFEST_FILE" --policy policies/ --output json >"$CONFTEST_TMP"
CONFTEST_EXIT=$?
set -e

python3 scripts/parse_conftest_results.py "$CONFTEST_TMP"

rm -f "$CONFTEST_TMP"
trap - EXIT
