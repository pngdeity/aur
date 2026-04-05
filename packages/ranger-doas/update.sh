#!/bin/bash
set -e

# This script is called by the master CI when a new version is detected.
# The current directory will be packages/ranger-doas/
UPSTREAM_URL="https://github.com/ranger/ranger.git"
LATEST_VER=$1 # nvchecker will pass the new version as the first argument

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
git diff > "../doas-substitution.patch"
cd ..

# 3. Update PKGBUILD
sed -i "s/^pkgver=.*/pkgver=$LATEST_VER/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD

# 4. Update Checksums (requires devtools)
updpkgsums

# Cleanup
rm -rf ranger-update
