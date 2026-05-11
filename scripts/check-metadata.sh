#!/usr/bin/env bash
# scripts/check-metadata.sh
# Validates that .SRCINFO is in sync with PKGBUILD.

set -euo pipefail

PKG_DIR=$1

if [[ -z "$PKG_DIR" ]]; then
    echo "Usage: $0 <package_dir>"
    exit 1
fi

cd "$PKG_DIR"

if [[ ! -f PKGBUILD ]]; then
    echo "::error::PKGBUILD not found in $PKG_DIR"
    exit 1
fi

echo "==> Validating metadata for $(basename "$PKG_DIR")"

# Generate temporary .SRCINFO
makepkg --printsrcinfo > .SRCINFO.tmp

# Compare
if ! diff -u .SRCINFO .SRCINFO.tmp; then
    echo "::error::.SRCINFO is out of sync with PKGBUILD in $PKG_DIR! Run 'makepkg --printsrcinfo > .SRCINFO' locally."
    rm .SRCINFO.tmp
    exit 1
fi

rm .SRCINFO.tmp
echo "  -> .SRCINFO is valid."
