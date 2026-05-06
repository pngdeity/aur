# PKGBUILD Custom Variables Reference

This document defines the custom variables (prefixed with `_`) used in this repository to manage package lifecycles and metadata. These variables are interpreted by the repository's orchestration layer (e.g., `scripts/sync-package.sh`) and apply universally across all packages in the `packages/` directory.

## OPTIONS AND DIRECTIVES

The following variables are interpreted by the orchestration layer to manage automated updates and synchronization. These are NOT standard Arch Linux variables and are ignored by `makepkg`.

### Upstream Tracking

**_upstream_arch_repo** (string)
:   Defines the path to an official Arch Linux packaging repository on GitLab (e.g., `archlinux/packaging/packages/gemini-cli`). When present, the orchestration layer will attempt to perform a hybrid merge between the local PKGBUILD and the one found at this location.
:   **Typical Usage**: Used for packages that are forks or mirrors of official Arch Linux repository packages.

**_upstream_aur_pkg** (string)
:   Defines the name of an upstream package in the Arch User Repository (AUR). Similar to `_upstream_arch_repo`, but targets AUR sources.
:   **Typical Usage**: Used for packages that are modifications or mirrors of existing AUR packages.

### Automated Metadata

**_githubname** (string)
:   The shorthand GitHub repository identifier (e.g., `user/repo`). This is primarily used by the changelog generation engine to fetch release notes and tags via the GitHub API.
:   **Typical Usage**: Used for packages that have an active upstream GitHub presence where release notes are published.

**_tag** (string)
:   Defines the tag pattern used by the upstream repository (e.g., `v${pkgver}`). If omitted, the orchestration layer defaults to `v$pkgver`.
:   **Typical Usage**: Used when an upstream source uses non-standard tag formats (e.g., tags without a 'v' prefix or nightly-specific tags).

### Asset Synchronization

**_use_common_gemini_settings** (boolean)
:   Activates the Centralized Asset Management pattern for `gemini-cli` variant packages. When set to `true`, `scripts/sync-package.sh` automatically copies `common/gemini-cli-settings.json` into the package source directory during the synchronization phase before updating hashes and metadata.
:   **Typical Usage**: Shared across all `gemini-cli` variants (`stable`, `-preview`, `-nightly`, `-git`) to eliminate duplication of the settings file.

### Context Preservation

**_pkgname** (string)
:   Stores the canonical name of the software, isolated from repository-specific suffixes like `-git`, `-nightly`, or `-preview`.
:   **Typical Usage**: Essential for monorepo environments where multiple variants of the same software exist, allowing shared scripts to reference the base product correctly.

---

## FOOTNOTES & CITATIONS

[^1]: **Arch Wiki: VCS package guidelines**. "VCS packages should provide and conflict with the non-VCS version of the package." *Reasoning: This justifies the use of `_pkgname` to systematically generate the 'provides' and 'conflicts' arrays in variant packages.*
