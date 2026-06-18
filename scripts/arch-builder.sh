#!/usr/bin/env bash
# scripts/arch-builder.sh
# Standardized Arch Linux package builder for monorepos.
# Usage: ./arch-builder.sh <package_dir>
#
# Build isolation: uses makepkg --clean --syncdeps inside a Docker container
# (fresh container per job in CI). For strict clean-chroot verification,
# use 'pkgctl build' locally — see AGENTS.md §3.

set -e

PKG_DIR="$1"

if [[ -z "$PKG_DIR" ]]; then
	echo "Usage: $0 <package_dir>"
	exit 1
fi

echo "==> Building package in: $PKG_DIR"

# Reproducible builds: respect SOURCE_DATE_EPOCH if set (e.g. by CI or local env),
# otherwise fall back to current timestamp.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(date +%s)}"

# Use writable build directories (repo checkout may be read-only in CI)
export BUILDDIR="${BUILDDIR:-/tmp/makepkg-build}"
export PKGDEST="${PKGDEST:-/tmp/makepkg-pkg}"
export SRCDEST="${SRCDEST:-/tmp/makepkg-src}"
mkdir -p "$BUILDDIR" "$PKGDEST" "$SRCDEST"

# Refresh package DB before syncdeps (container image may be stale)
sudo pacman -Syu --noconfirm

cd "$PKG_DIR"

# 1. PGP Key Management
# Automatically import keys defined in the PKGBUILD
# This remains in the builder as keys are environment-specific (keyring)
KEYS=$(makepkg --printsrcinfo 2>/dev/null | sed -n 's/^\s*validpgpkeys = //p' || true)
for KEY in $KEYS; do
	echo "  -> Importing PGP Key: $KEY"
	gpg --recv-keys "$KEY" || echo "    ! Warning: Failed to fetch PGP key $KEY"
done

# 2. Build
# Delegate compilation and dependency resolution to makepkg.
# We assume PKGBUILD has already been synchronized (versioned/hashed) by sync-package.sh.
echo "  -> Starting makepkg..."
makepkg --syncdeps --noconfirm --noprogressbar --needed --clean

# 3. Move artifacts to a central location (writable — checkout may be read-only)
export DISTDIR="${DISTDIR:-/tmp/makepkg-dist}"
mkdir -p "$DISTDIR"
cp "$PKGDEST"/*.pkg.tar.zst "$DISTDIR"/ 2>/dev/null || true

echo "==> Finished building $PKG_DIR"
