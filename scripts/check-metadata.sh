#!/usr/bin/env bash
# scripts/check-metadata.sh
# Validates that PKGBUILD can produce valid .SRCINFO metadata.
# .SRCINFO is a build artifact (per SRCINFO-VERSION-CONTROL-POLICY.md) and is
# not version-controlled. This script performs syntactic validation only.

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

if ! makepkg --printsrcinfo >/dev/null; then
	echo "::error::PKGBUILD in $PKG_DIR fails to generate valid .SRCINFO metadata."
	exit 1
fi

echo "  -> PKGBUILD produces valid .SRCINFO metadata."
