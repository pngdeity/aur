#!/usr/bin/env bash
# scripts/sync-package.sh
# Orchestrates package synchronization: versioning, changelogs, hashes, and upstream merges.

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

# --- Helper: Identity Protection ---
# Snapshots critical identity variables to preserve them across upstream merges
snapshot_identity() {
    grep -E '^(pkgname|pkgver|pkgrel|provides|conflicts|replaces|source)=' PKGBUILD > .identity.tmp
    # Handle pkgver() function if it exists
    if grep -q "^pkgver()" PKGBUILD; then
        sed -n '/^pkgver()/,/^}/p' PKGBUILD > .pkgver_func.tmp
    fi
}

restore_identity() {
    # Restore simple variables
    while IFS= read -r line; do
        var_name=$(echo "$line" | cut -d= -f1)
        # Use a delimiter that won't appear in the line for sed
        sed -i "s|^${var_name}=.*|$line|" PKGBUILD
    done < .identity.tmp
    
    # Restore pkgver() function
    if [[ -f .pkgver_func.tmp ]]; then
        # Remove any existing pkgver() or static pkgver that might have been merged
        sed -i '/^pkgver()/,/^}/d' PKGBUILD
        # Insert the function after the maintainer header or at top
        cat .pkgver_func.tmp >> PKGBUILD.new_func
        cat PKGBUILD >> PKGBUILD.new_func
        mv PKGBUILD.new_func PKGBUILD
        rm .pkgver_func.tmp
    fi
    rm .identity.tmp
}

# --- Helper: Asset Discovery ---
fetch_upstream_assets() {
    local upstream_content="$1"
    local base_url="$2"
    echo "  -> Scanning for missing upstream assets..."
    
    # Extract files from source array that are not URLs
    local assets=$(echo "$upstream_content" | sed -n '/^source=(/,/)/p' | grep -v '=(' | grep -v ')' | tr -d '"' | tr -d "'" | xargs -n1 echo | grep -v '://' | cut -d: -f1 || true)
    
    for asset in $assets; do
        if [[ ! -f "$asset" ]]; then
            echo "    -> Downloading missing asset: $asset"
            curl -sL "${base_url}/${asset}" -o "$asset"
        fi
    done
}

CURRENT_VER=$(grep -oP '^pkgver=\K.*' PKGBUILD || echo "")
CURRENT_REL=$(grep -oP '^pkgrel=\K.*' PKGBUILD || echo "1")

# 0. Upstream Merge Logic
UPSTREAM_CHANGED=false
ARCH_REPO=$(grep -E '^_upstream_arch_repo=' PKGBUILD | cut -d= -f2 | tr -d '"' | tr -d "'" || echo "")
AUR_PKG=$(grep -E '^_upstream_aur_pkg=' PKGBUILD | cut -d= -f2 | tr -d '"' | tr -d "'" || echo "")

if [[ -n "$ARCH_REPO" ]]; then
    echo "  -> Checking official Arch upstream ($ARCH_REPO)"
    BASE_URL="https://gitlab.archlinux.org/${ARCH_REPO}/-/raw/main"
    UPSTREAM_URL="${BASE_URL}/PKGBUILD"
elif [[ -n "$AUR_PKG" ]]; then
    echo "  -> Checking AUR upstream ($AUR_PKG)"
    BASE_URL="https://aur.archlinux.org/cgit/aur.git/plain"
    UPSTREAM_URL="${BASE_URL}/PKGBUILD?h=${AUR_PKG}"
fi

if [[ -n "${UPSTREAM_URL:-}" ]]; then
    if curl -sL "$UPSTREAM_URL" -o PKGBUILD.new && grep -q "pkgname=" PKGBUILD.new; then
        if [[ -f .PKGBUILD.upstream ]]; then
            if ! cmp -s .PKGBUILD.upstream PKGBUILD.new; then
                echo "  -> Upstream PKGBUILD changed, attempting hybrid merge..."
                
                # Download new assets referenced in upstream
                fetch_upstream_assets "$(cat PKGBUILD.new)" "$BASE_URL"
                
                # Perform protected merge
                snapshot_identity
                git merge-file PKGBUILD .PKGBUILD.upstream PKGBUILD.new || echo "  -> Merge conflicts detected! Please resolve manually."
                restore_identity
                
                mv PKGBUILD.new .PKGBUILD.upstream
                UPSTREAM_CHANGED=true
            else
                echo "  -> Upstream PKGBUILD unchanged."
                rm PKGBUILD.new
            fi
        else
            echo "  -> Initial upstream tracking setup."
            fetch_upstream_assets "$(cat PKGBUILD.new)" "$BASE_URL"
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
    # Only bump if software version didn't just change
    NEW_REL=$((CURRENT_REL + 1))
    sed -i "s/^pkgrel=.*/pkgrel=${NEW_REL}/" PKGBUILD
fi

# 1.5. Package-Specific Transformation (Specialized path)
if [[ -x "./update.sh" ]]; then
    echo "  -> Running package-specific transformation script"
    ./update.sh "${NEW_VER}"
fi

# 1.6. Shared Asset Synchronization (Centralization path)
if grep -q "^_use_common_gemini_settings=true" PKGBUILD; then
    echo "  -> Syncing shared gemini-cli settings from common/"
    cp "${SCRIPT_DIR}/../common/gemini-cli-settings.json" "settings.json"
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
