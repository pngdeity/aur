#!/bin/bash
set -euo pipefail
pkg="python-pytest-recording"
mkdir -p "packages/$pkg"
curl -sL "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=$pkg" -o "packages/$pkg/PKGBUILD"
sed -i "1s/^/# Maintainer: pngdeity <pngdeity@tutanota.com>\n_upstream_aur_pkg=\"$pkg\"\n/" "packages/$pkg/PKGBUILD"
ver=$(grep -E "^pkgver=" "packages/$pkg/PKGBUILD" | cut -d= -f2 | head -n 1 | tr -d "'" | tr -d '"')
bash scripts/sync-package.sh "$pkg" "$ver"

cat << 'IN_EOF' > "packages/$pkg/update.sh"
#!/bin/bash
set -e
LATEST_VER=$1
sed -i '2,$ s/^# Maintainer:/# Contributor:/g' PKGBUILD
IN_EOF
chmod +x "packages/$pkg/update.sh"

bash scripts/sync-package.sh "$pkg" "$ver"

cd "packages/$pkg"
pkgctl version setup
cd ../..
