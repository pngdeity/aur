#!/usr/bin/env bash
# scripts/arch-builder.sh
# Standardized Arch Linux package builder for monorepos.
# Usage: ./arch-builder.sh <package_dir> <version>

set -e

PKG_DIR="$1"
NEW_VER="$2"

if [[ -z "$PKG_DIR" || -z "$NEW_VER" ]]; then
    echo "Usage: $0 <package_dir> <version>"
    exit 1
fi

echo "==> Building package in: $PKG_DIR"

# 0. Local Repository Setup (Circular Dependency Resolver)
LOCAL_REPO_DIR="/tmp/local-repo"
if [ ! -d "$LOCAL_REPO_DIR" ]; then
    echo "  -> Initializing local repository for dependency resolution..."
    mkdir -p "$LOCAL_REPO_DIR"
    
    # Add to pacman.conf if not already there. We use sudo since pacman.conf is root-owned.
    if ! grep -q "\[local-nightly\]" /etc/pacman.conf; then
        echo -e "\n[local-nightly]\nSigLevel = Optional TrustAll\nServer = file://$LOCAL_REPO_DIR" | sudo tee -a /etc/pacman.conf > /dev/null
    fi
fi

cd "$PKG_DIR"

# 1. Versioning Management (Point 4 & 2)
# Respect VCS packages by skipping manual injection if pkgver() exists.
if grep -q "pkgver()" PKGBUILD; then
    echo "  -> VCS/pkgver() function detected. Skipping manual version injection."
else
    # Extract existing version to propagate it to all helper variables
    OLD_VER=$(grep "^pkgver=" PKGBUILD | cut -d= -f2 | tr -d "'\" ")
    if [[ -n "$OLD_VER" ]]; then
      echo "  -> Injecting version $NEW_VER (Replacing $OLD_VER)"
      sed -i "s/\b$OLD_VER\b/$NEW_VER/g" PKGBUILD
    fi
fi

# 2. PGP Key Management (Point 3)
# Automatically import keys defined in the PKGBUILD
KEYS=$(grep -oP 'validpgpkeys=\(\K[^)]+' PKGBUILD | tr -d "'\"" || true)
for KEY in $KEYS; do
    echo "  -> Importing PGP Key: $KEY"
    gpg --recv-keys "$KEY" || echo "    ! Warning: Failed to fetch PGP key $KEY"
done

# 3. Integrity Check
# Let the Arch Build System update the hashes for the new version/commit
echo "  -> Updating checksums..."
updpkgsums

# 4. Build
# Delegate compilation and dependency resolution to makepkg
echo "  -> Starting makepkg..."
makepkg --syncdeps --noconfirm --noprogressbar --needed

# 5. Move artifacts to a central location
mkdir -p ../dist
cp *.pkg.tar.zst ../dist/ 2>/dev/null || true

echo "==> Finished building $PKG_DIR"
