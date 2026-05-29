#!/usr/bin/env bash
# scripts/aur-deploy.sh
# Process a repo PKGBUILD into AUR-compatible output and push to the AUR.
# Usage: ./aur-deploy.sh <package_dir> [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$1"
DRY_RUN=false

if [[ "${2:-}" == "--dry-run" ]]; then
	DRY_RUN=true
fi

if [[ -z "$PKG_DIR" || ! -d "$PKG_DIR" ]]; then
	echo "Usage: $0 <package_dir> [--dry-run]"
	exit 1
fi

cd "$PKG_DIR"
PKG_NAME=$(basename "$PKG_DIR")

echo "==> AUR Deploy: ${PKG_NAME}"

# --- Safety gate: variant packages must not deploy to AUR ---
if grep -q "^_repo_subarch=" PKGBUILD; then
	echo "::error::Package ${PKG_NAME} has _repo_subarch set. Variant PKGBUILDs must not deploy to AUR."
	exit 1
fi

# --- Check opt-in ---
if ! grep -q "^_deploy_aur=true" PKGBUILD; then
	echo "  -> _deploy_aur not set, skipping AUR deployment."
	exit 0
fi

# --- Processing ---
AUR_DIR="/tmp/aur-deploy/${PKG_NAME}"
echo "  -> Producing AUR-compatible PKGBUILD"
rm -rf "$AUR_DIR"
mkdir -p "$AUR_DIR"
cp PKGBUILD "$AUR_DIR/PKGBUILD"

# 1. Inline source directives (recursively resolve relative paths starting with ../)
echo "  -> Resolving source directives"
while grep -q '^source "\.\./' "$AUR_DIR/PKGBUILD"; do
	sourced_rel=$(grep -oP '^source "\K(\.\./[^"]+)' "$AUR_DIR/PKGBUILD" | head -1)
	sourced_abs=$(realpath "$(dirname "PKGBUILD")/$sourced_rel")
	if [[ ! -f "$sourced_abs" ]]; then
		echo "::error::Sourced file not found: ${sourced_abs}"
		exit 1
	fi
	esc_rel=$(printf '%s\n' "$sourced_rel" | sed 's/[\/&]/\\&/g')
	sed -i "/^source \"${esc_rel}\"/{
        r ${sourced_abs}
        d
    }" "$AUR_DIR/PKGBUILD"
done

# 2. Strip known repo-local _-prefixed variables (keep standard ones like _name)
echo "  -> Stripping repo-local variables"
REPO_LOCAL_VARS=(
	'_deploy_aur'
	'_demote_upstream_maintainer'
	'_upstream_aur_pkg'
	'_upstream_arch_repo'
	'_use_common_gemini_settings'
	'_repo_subarch'
	'_auto_merge_build'
)
for var in "${REPO_LOCAL_VARS[@]}"; do
	sed -i "/^${var}=/d" "$AUR_DIR/PKGBUILD"
done

# 3. Strip PREREVIEW markers and their companion action comments
echo "  -> Stripping PREREVIEW markers"
sed -i '/^# PREREVIEW:/d' "$AUR_DIR/PKGBUILD"
sed -i '/^# Review the diff/d' "$AUR_DIR/PKGBUILD"

# 4. Generate .SRCINFO from the processed PKGBUILD
echo "  -> Generating .SRCINFO"
cd "$AUR_DIR"
makepkg --printsrcinfo >.SRCINFO

# 5. Validate output with namcap
echo "  -> Running namcap on processed PKGBUILD"
if command -v namcap &>/dev/null; then
	namcap PKGBUILD || echo "  ::warning::namcap reported issues"
fi

# --- Git Push ---
AUR_REMOTE="ssh://aur@aur.archlinux.org/${PKG_NAME}.git"
PKGVER=$("$SCRIPT_DIR/pkgvar" "$AUR_DIR/PKGBUILD" pkgver)
PKGREL=$("$SCRIPT_DIR/pkgvar" "$AUR_DIR/PKGBUILD" pkgrel)

# Check SSH connectivity to AUR (requires AUR_SSH_PRIVATE_KEY in ssh-agent or key file)
echo "  -> Checking SSH connectivity to AUR"
if ! ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -q -T aur@aur.archlinux.org help 2>&1; then
	echo "::error::Cannot connect to aur.archlinux.org. Ensure AUR_SSH_PRIVATE_KEY is loaded in ssh-agent."
	echo "::error::Run: eval \$(ssh-agent) && ssh-add /path/to/aur-deploy-key"
	exit 1
fi
echo "  -> SSH connection verified."

# Clone existing AUR repository (read-only — commit/push only in live mode)
AUR_CLONE="/tmp/aur-deploy/${PKG_NAME}-remote"
rm -rf "$AUR_CLONE"

if git clone "$AUR_REMOTE" "$AUR_CLONE" 2>/dev/null; then
	echo "  -> Cloned existing AUR repository for ${PKG_NAME}"
else
	echo "::error::AUR repository for ${PKG_NAME} does not exist."
	echo "::error::You must register the pkgbase '${PKG_NAME}' on https://aur.archlinux.org/ first."
	exit 1
fi

# Copy processed files into clone
cp "$AUR_DIR/PKGBUILD" "$AUR_DIR/.SRCINFO" "$AUR_CLONE/"

# Diff processed output against current AUR state
cd "$AUR_CLONE"
git add PKGBUILD .SRCINFO
if git diff --cached --quiet; then
	echo "  -> AUR repository already up to date (content identical)."
	exit 0
fi

COMMIT_MSG="${PKG_NAME}: update to ${PKGVER}-${PKGREL}"

if $DRY_RUN; then
	echo "  -> Dry run: changes that would be pushed to AUR:"
	echo "  -> Remote: ${AUR_REMOTE}"
	echo "  -> Files: PKGBUILD, .SRCINFO"
	echo "  -> Commit message: ${COMMIT_MSG}"
	echo
	git diff --cached --stat
	echo
	echo "  -> Diff preview:"
	git diff --cached
	echo
	echo "::notice::Dry run complete. No changes pushed."
	exit 0
fi

# Commit and push (live mode only)
git commit -m "$COMMIT_MSG"
git push
echo "  -> Pushed ${COMMIT_MSG} to AUR."
echo "==> AUR deployment complete for ${PKG_NAME}"
