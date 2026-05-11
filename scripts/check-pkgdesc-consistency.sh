#!/usr/bin/env bash
# scripts/check-pkgdesc-consistency.sh
# Validates that all package variants sharing the same _pkgname
# have identical pkgdesc strings.
#
# Exits 0 on success, 1 if violations are found, 2 on usage errors.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FOUND_VIOLATIONS=false
EXCLUDE_DIRS=("template" "openproject-cli")

# --- Usage ---
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    echo "Usage: $0 [--ci]"
    echo "  Validates that all package variants sharing the same _pkgname have identical pkgdesc."
    echo "  --ci   Output in GitHub Actions annotation format."
    exit 0
fi

CI_MODE=false
if [[ "${1:-}" == "--ci" ]]; then
    CI_MODE=true
fi

echo "==> Checking pkgdesc consistency across variant groups..."

# --- Collect data ---
declare -A PKGDESC_MAP  # _pkgname -> pkgdesc -> list of package dirs
declare -A GROUP_MEMBERS  # _pkgname -> count

for pkgbuild in "$REPO_ROOT"/packages/*/PKGBUILD; do
    pkg_dir=$(dirname "$pkgbuild")
    pkg_dir_name=$(basename "$pkg_dir")

    # Skip excluded directories
    skip=false
    for excl in "${EXCLUDE_DIRS[@]}"; do
        if [[ "$pkg_dir_name" == "$excl" ]]; then
            skip=true
            break
        fi
    done
    $skip && continue

    # Extract _pkgname and pkgdesc via sandboxed sourcing (resolves all variable references)
    _pkgname_val=$("$SCRIPT_DIR/pkgvar" "$pkgbuild" _pkgname)
    pkgdesc_val=$("$SCRIPT_DIR/pkgvar" "$pkgbuild" pkgdesc)

    if [[ -z "$_pkgname_val" ]] || [[ -z "$pkgdesc_val" ]]; then
        continue
    fi

    # Build composite key: _pkgname -> pkgdesc -> (space-separated dir names)
    key="${_pkgname_val}__${pkgdesc_val}"
    if [[ -n "${PKGDESC_MAP[$key]:-}" ]]; then
        PKGDESC_MAP[$key]="${PKGDESC_MAP[$key]} ${pkg_dir_name}"
    else
        PKGDESC_MAP[$key]="$pkg_dir_name"
    fi

    # Count members per _pkgname
    if [[ -n "${GROUP_MEMBERS[$_pkgname_val]:-}" ]]; then
        GROUP_MEMBERS[$_pkgname_val]=$((GROUP_MEMBERS[$_pkgname_val] + 1))
    else
        GROUP_MEMBERS[$_pkgname_val]=1
    fi
done

# --- Analyze ---
# Track unique pkgdesc values per _pkgname group using a delimiter that
# won't appear in actual descriptions: ASCII Unit Separator (0x1F).
US=$'\x1F'
declare -A GROUP_UNIQUE_DESCS  # _pkgname -> US-separated unique pkgdesc values

for key in "${!PKGDESC_MAP[@]}"; do
    _pkgname_val="${key%%__*}"
    pkgdesc_val="${key#*__}"
    existing="${GROUP_UNIQUE_DESCS[$_pkgname_val]:-}"
    if [[ "$existing" != *"${US}${pkgdesc_val}${US}"* ]]; then
        GROUP_UNIQUE_DESCS[$_pkgname_val]="${existing}${US}${pkgdesc_val}${US}"
    fi
done

# --- Report ---
for _pkgname_val in "${!GROUP_MEMBERS[@]}"; do
    member_count="${GROUP_MEMBERS[$_pkgname_val]}"
    if [[ "$member_count" -le 1 ]]; then
        continue  # Singleton group, nothing to compare
    fi

    # Count unique pkgdesc values by stripping empty entries and counting US-delimited tokens
    us_list="${GROUP_UNIQUE_DESCS[$_pkgname_val]}"
    # Trim leading/trailing separators and count
    trimmed="${us_list#"${US}"}"
    trimmed="${trimmed%"${US}"}"
    if [[ -z "$trimmed" ]]; then
        unique_count=0
    else
        IFS="$US" read -ra desc_array <<< "$trimmed"
        unique_count=${#desc_array[@]}
    fi

    if [[ "$unique_count" -le 1 ]]; then
        printf '  ✓ %s: consistent\n' "$_pkgname_val"
    else
        FOUND_VIOLATIONS=true
        printf '  ✗ %s: pkgdesc mismatch\n' "$_pkgname_val"

        # Show each variant's pkgdesc
        for key in "${!PKGDESC_MAP[@]}"; do
            if [[ "${key%%__*}" == "$_pkgname_val" ]]; then
                pkgdesc_val="${key#*__}"
                dirs="${PKGDESC_MAP[$key]}"
                for dir in $dirs; do
                    max_len=22
                    if [[ "$CI_MODE" == "true" ]]; then
                        echo "::warning file=packages/${dir}/PKGBUILD::pkgdesc differs from other ${_pkgname_val} variants"
                    fi
                    printf "    %-${max_len}s %s\n" "${dir}:" "\"${pkgdesc_val}\""
                done
            fi
        done
    fi
done

if [[ "$FOUND_VIOLATIONS" == "true" ]]; then
    printf '\n::error::pkgdesc consistency violations found. All packages sharing the same _pkgname must have identical pkgdesc.\n'
    exit 1
fi
printf '\n  -> All variant groups consistent.\n'
