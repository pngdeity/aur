#!/bin/bash
set -euo pipefail
pkg="python-pytest-recording"
mkdir -p "packages/$pkg"
curl -sL "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=$pkg" -o "packages/$pkg/PKGBUILD"
sed -i "1s/^/# Maintainer: pngdeity <pngdeity@tutanota.com>\n_upstream_aur_pkg=\"$pkg\"\n_demote_upstream_maintainer=true\n/" "packages/$pkg/PKGBUILD"
ver=$(grep -E "^pkgver=" "packages/$pkg/PKGBUILD" | cut -d= -f2 | head -n 1 | tr -d "'" | tr -d '"')
bash scripts/sync-package.sh "$pkg" "$ver"

cd "packages/$pkg"
pkgctl version setup
cd ../..
