#!/usr/bin/env bash
# scripts/sync-package.sh
# Orchestrates package synchronization: versioning, changelogs, and hashes.

set -euo pipefail

PKG_NAME_RAW=$1
NEW_VER=$2

# Resolve actual package directory by stripping tracking suffixes
PKG_NAME=${PKG_NAME_RAW%-arch}
PKG_NAME=${PKG_NAME%-aur}
PKG_DIR="packages/${PKG_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Synchronizing ${PKG_NAME} (Triggered by ${PKG_NAME_RAW}) to version ${NEW_VER}"

if [[ ! -d "${PKG_DIR}" ]]; then
    echo "::error::Package directory ${PKG_DIR} not found!"
    exit 1
fi

cd "${PKG_DIR}"

CURRENT_VER=$(grep -oP '^pkgver=\K.*' PKGBUILD || echo "")
CURRENT_REL=$(grep -oP '^pkgrel=\K.*' PKGBUILD || echo "1")

# 0. Upstream Merge Logic
UPSTREAM_CHANGED=false
ARCH_REPO=$(grep -E '^_upstream_arch_repo=' PKGBUILD | cut -d= -f2 | tr -d '"' | tr -d "'" || echo "")
AUR_PKG=$(grep -E '^_upstream_aur_pkg=' PKGBUILD | cut -d= -f2 | tr -d '"' | tr -d "'" || echo "")

if [[ -n "$ARCH_REPO" ]]; then
    echo "  -> Checking official Arch upstream ($ARCH_REPO)"
    UPSTREAM_URL="https://gitlab.archlinux.org/${ARCH_REPO}/-/raw/main/PKGBUILD"
elif [[ -n "$AUR_PKG" ]]; then
    echo "  -> Checking AUR upstream ($AUR_PKG)"
    UPSTREAM_URL="https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=${AUR_PKG}"
fi

if [[ -n "${UPSTREAM_URL:-}" ]]; then
    if curl -sL "$UPSTREAM_URL" -o PKGBUILD.new && grep -q "pkgname=" PKGBUILD.new; then
        if [[ -f .PKGBUILD.upstream ]]; then
            if ! cmp -s .PKGBUILD.upstream PKGBUILD.new; then
                echo "  -> Upstream PKGBUILD changed, attempting merge..."
                git merge-file PKGBUILD .PKGBUILD.upstream PKGBUILD.new || echo "  -> Merge conflicts detected in PKGBUILD! Please resolve manually."
                mv PKGBUILD.new .PKGBUILD.upstream
                UPSTREAM_CHANGED=true
            else
                echo "  -> Upstream PKGBUILD unchanged."
                rm PKGBUILD.new
            fi
        else
            echo "  -> Initial upstream tracking setup."
            mv PKGBUILD.new .PKGBUILD.upstream
            UPSTREAM_CHANGED=true
        fi
    else
        echo "  -> Failed to fetch upstream PKGBUILD."
        rm -f PKGBUILD.new
    fi
fi

# 1. Version Update
echo "  -> Updating versions in PKGBUILD"
# If the trigger is the software version changing, update pkgver and reset pkgrel
if [[ "$PKG_NAME_RAW" == "$PKG_NAME" ]] && [[ "$CURRENT_VER" != "$NEW_VER" ]]; then
    sed -i "s/^pkgver=.*/pkgver=${NEW_VER}/" PKGBUILD
    sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
# If the trigger was an upstream config change (or we just found one), bump pkgrel
elif [[ "$UPSTREAM_CHANGED" == "true" ]]; then
    NEW_REL=$((CURRENT_REL + 1))
    sed -i "s/^pkgrel=.*/pkgrel=${NEW_REL}/" PKGBUILD
fi

# 1.5. Package-Specific Transformation (Specialized path)
if [[ -x "./update.sh" ]]; then
    echo "  -> Running package-specific transformation script"
    ./update.sh "${NEW_VER}"
fi

# 2. Intelligent Changelog Automation (DRY path)
GITHUB_REPO=$(grep -oP '(?<=^_githubname=).+' PKGBUILD | tr -d '"' | tr -d "'" || echo "")

if [[ -n "${GITHUB_REPO}" ]]; then
    # Determine the tag pattern, fallback to v$pkgver
    TAG_PATTERN=$(grep -oP '(?<=^_tag=).+' PKGBUILD | tr -d '"' | tr -d "'" || echo "")
    TAG=${TAG_PATTERN:-"v${NEW_VER}"}
    TAG=$(echo "${TAG}" | sed "s/\${pkgver}/${NEW_VER}/g")
    
    # Extract API version if specified
    API_VER=$(grep -oP '(?<=^# _github_api_version=).+' PKGBUILD | tr -d '"' | tr -d "'" || echo "2026-03-10")

    CHANGELOG_FILE="${PKG_NAME}.changelog"
    bash "${SCRIPT_DIR}/generate-changelog.sh" "${GITHUB_REPO}" "${TAG}" "${CHANGELOG_FILE}" "${API_VER}"
    
    # Inject 'changelog' variable into PKGBUILD only if not present
    if ! grep -q "^changelog=" PKGBUILD; then
        echo "  -> Injecting changelog variable"
        sed -i "/^pkgname=/a changelog=${CHANGELOG_FILE}" PKGBUILD
    fi
fi

# 3. Hash Update
# updpkgsums requires the source files to be reachable/downloadable
echo "  -> Updating checksums"
updpkgsums

# 4. Metadata Update
echo "  -> Regenerating .SRCINFO"
makepkg --printsrcinfo > .SRCINFO

echo "==> Synchronization complete for ${PKG_NAME}"
