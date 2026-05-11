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

# 1. PGP Key Management
# Automatically import keys defined in the PKGBUILD
# This remains in the builder as keys are environment-specific (keyring)
KEYS=$(makepkg --printsrcinfo | grep -oP '^\s*validpgpkeys = \K.*' || true)
for KEY in $KEYS; do
    echo "  -> Importing PGP Key: $KEY"
    gpg --recv-keys "$KEY" || echo "    ! Warning: Failed to fetch PGP key $KEY"
done

# 2. Build
# Delegate compilation and dependency resolution to makepkg.
# We assume PKGBUILD has already been synchronized (versioned/hashed) by sync-package.sh.
echo "  -> Starting makepkg..."
makepkg --syncdeps --noconfirm --noprogressbar --needed

# 3. Move artifacts to a central location
mkdir -p ../../dist
cp *.pkg.tar.zst ../../dist/ 2>/dev/null || true

echo "==> Finished building $PKG_DIR"
