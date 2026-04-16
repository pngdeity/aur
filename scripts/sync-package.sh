#!/usr/bin/env bash
# scripts/sync-package.sh
# Orchestrates package synchronization: versioning, changelogs, and hashes.

set -euo pipefail

PKG_NAME=$1
NEW_VER=$2
PKG_DIR="packages/${PKG_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Synchronizing ${PKG_NAME} to version ${NEW_VER}"

if [[ ! -d "${PKG_DIR}" ]]; then
    echo "::error::Package directory ${PKG_DIR} not found!"
    exit 1
fi

cd "${PKG_DIR}"

# 1. Version Update (Oblivious path)
echo "  -> Updating versions in PKGBUILD"
# Update pkgver and reset pkgrel to 1
sed -i "s/^pkgver=.*/pkgver=${NEW_VER}/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD

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
