#!/usr/bin/env bash
# scripts/publish-aur.sh
# Verify-then-Publish: builds and tests a package, then pushes it to the AUR.
# Usage: ./publish-aur.sh <package_dir>
#
# Required environment variables:
#   AUR_SSH_PRIVATE_KEY  - Contents of the SSH private key for AUR access
#
# Optional environment variables:
#   AUR_HOST             - AUR SSH hostname (default: aur.archlinux.org)
#   AUR_USER             - AUR SSH user (default: aur)

set -euo pipefail

PKG_DIR="${1:-}"

if [[ -z "$PKG_DIR" ]]; then
    echo "Usage: $0 <package_dir>"
    exit 1
fi

if [[ ! -d "$PKG_DIR" ]]; then
    echo "::error::Package directory '$PKG_DIR' does not exist."
    exit 1
fi

if [[ ! -f "$PKG_DIR/PKGBUILD" ]]; then
    echo "::error::No PKGBUILD found in '$PKG_DIR'."
    exit 1
fi

AUR_HOST="${AUR_HOST:-aur.archlinux.org}"
AUR_USER="${AUR_USER:-aur}"

# Derive the AUR package name from PKGBUILD
PKG_NAME=$(bash -c "source '$PKG_DIR/PKGBUILD'; echo \$pkgname")

if [[ -z "$PKG_NAME" ]]; then
    echo "::error::Could not determine pkgname from PKGBUILD."
    exit 1
fi

echo "==> Starting verify-then-publish for: $PKG_NAME"

# ── 1. GATE: Build and run tests ──────────────────────────────────────────────
# makepkg will compile, run check() if defined, and package. Any failure aborts.
echo "  -> Building and running checks with makepkg..."
(
    cd "$PKG_DIR"
    makepkg --syncdeps --check --noconfirm --noprogressbar --cleanbuild
)
echo "  -> Build and check passed."

# ── 2. METADATA PARITY: Regenerate .SRCINFO after successful build ────────────
# .SRCINFO must reflect the exact state of the verified PKGBUILD.
echo "  -> Regenerating .SRCINFO after verified build..."
(
    cd "$PKG_DIR"
    makepkg --printsrcinfo > .SRCINFO
)
echo "  -> .SRCINFO regenerated."

# ── 3. SECURITY: Configure SSH without logging secrets ───────────────────────
echo "  -> Configuring SSH for AUR access..."
SSH_DIR="$(mktemp -d)"
trap 'rm -rf "$SSH_DIR"' EXIT

chmod 700 "$SSH_DIR"
printf '%s\n' "${AUR_SSH_PRIVATE_KEY}" > "$SSH_DIR/aur_key"
chmod 600 "$SSH_DIR/aur_key"

# Add and verify the AUR host key against its known RSA fingerprint.
# Fingerprint sourced from: https://wiki.archlinux.org/title/AUR_submission_guidelines
# SHA256:48HcEYPGDPsEOJhFtFHmwDxWz2jdXNMbMnHqKh8IKWI  aur.archlinux.org (RSA)
AUR_EXPECTED_FP="SHA256:48HcEYPGDPsEOJhFtFHmwDxWz2jdXNMbMnHqKh8IKWI"
ssh-keyscan -H "$AUR_HOST" 2>/dev/null > "$SSH_DIR/known_hosts"
ACTUAL_FP=$(ssh-keygen -lf "$SSH_DIR/known_hosts" | grep RSA | awk '{print $2}')
if [[ "$ACTUAL_FP" != "$AUR_EXPECTED_FP" ]]; then
    echo "::error::AUR host key fingerprint mismatch! Expected $AUR_EXPECTED_FP, got $ACTUAL_FP"
    exit 1
fi

SSH_CMD="ssh -i $SSH_DIR/aur_key -o UserKnownHostsFile=$SSH_DIR/known_hosts -o StrictHostKeyChecking=yes"

# ── 4. PUBLISH: Push PKGBUILD and .SRCINFO to AUR ────────────────────────────
echo "  -> Cloning AUR repository for $PKG_NAME..."
AUR_REMOTE="${AUR_USER}@${AUR_HOST}:${PKG_NAME}.git"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$SSH_DIR" "$WORK_DIR"' EXIT

GIT_SSH_COMMAND="$SSH_CMD" git clone "$AUR_REMOTE" "$WORK_DIR" || {
    echo "  -> AUR repo not found; initialising a new one."
    mkdir -p "$WORK_DIR"
    git -C "$WORK_DIR" init
    GIT_SSH_COMMAND="$SSH_CMD" git -C "$WORK_DIR" remote add origin "$AUR_REMOTE"
}

# Copy PKGBUILD, .SRCINFO, and supporting files (patches, install scripts, etc.)
# Exclude build artefacts and git metadata.
rsync -a --exclude='.git' --exclude='*.pkg.tar.*' --exclude='src/' --exclude='pkg/' \
    "$PKG_DIR/" "$WORK_DIR/"

git -C "$WORK_DIR" config user.name "AUR Publisher"
git -C "$WORK_DIR" config user.email "aur-publisher@localhost"
git -C "$WORK_DIR" add -A

if git -C "$WORK_DIR" diff --cached --quiet; then
    echo "  -> No changes detected; skipping AUR push."
else
    PKG_VER=$(bash -c "source '$PKG_DIR/PKGBUILD'; echo \${pkgver}-\${pkgrel}")
    git -C "$WORK_DIR" commit -m "chore: release ${PKG_NAME} ${PKG_VER}"
    # Never print the SSH command or key paths in the push output
    GIT_SSH_COMMAND="$SSH_CMD" git -C "$WORK_DIR" push origin HEAD:master
    echo "  -> Successfully pushed $PKG_NAME $PKG_VER to the AUR."
fi

echo "==> publish-aur.sh finished for $PKG_NAME."
