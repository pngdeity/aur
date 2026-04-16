#!/bin/bash
set -e

# This script is called by scripts/sync-package.sh during the sync phase.
# It handles the package-specific transformation of upstream ranger
# into the patched ranger-doas variant.

# NOTE: The current transformation is naive and simply replaces 'sudo' with 'doas'.
# This does NOT account for the fact that doas lacks a '-b' (background) flag.
# Commands relying on backgrounding via sudo may fail or hang in this version.

UPSTREAM_URL="https://github.com/ranger/ranger.git"
LATEST_VER=$1 # sync-package.sh will pass the new version as the first argument

echo "Updating ranger-doas to version $LATEST_VER..."

# 1. Clone fresh upstream and apply transformations
git clone --depth 1 --branch "v$LATEST_VER" "$UPSTREAM_URL" ranger-update
cd ranger-update

# Replicate the transformations
sed -i 's/sudo/doas/g' ranger/core/runner.py
sed -i "s/\['sudo', '-E', 'su', 'root', '-mc'\]/\['doas', '\/bin\/sh', '-c'\]/g" ranger/ext/rifle.py
find . -type f \( -name "README.md" -o -name "*.pod" -o -name "*.conf" -o -name "CHANGELOG.md" -o -name "*.svg" \) \
    -exec sed -i 's/sudo/doas/g' {} +

# 2. Generate the new patch
# Responsibility for PKGBUILD metadata and checksums is delegated to sync-package.sh
git diff > "../doas-substitution.patch"
cd ..

# Cleanup
rm -rf ranger-update
