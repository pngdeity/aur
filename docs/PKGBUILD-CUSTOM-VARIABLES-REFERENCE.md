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

### AUR Deployment

**_deploy_aur** (boolean)
:   When `true`, the CI/CD pipeline (`release.yml` → `scripts/aur-deploy.sh`) processes this package's PKGBUILD into AUR-compatible output and pushes it to `aur.archlinux.org`. The processing step strips repo-local `_`-prefixed variables, `# PREREVIEW:` markers, and inlines `source "../..."` directives before push.
:   **Typical Usage**: Set on base packages that serve as the canonical upstream for an AUR publication. Variant packages (those with `_repo_subarch` set) MUST NOT set `_deploy_aur=true` — the script enforces this with a hard error.
:   **Mutual Exclusion**: Setting both `_deploy_aur=true` and `_repo_subarch` will cause `aur-deploy.sh` to exit with an error.

### Authorship Management

**_demote_upstream_maintainer** (boolean)
:   When `true`, `scripts/sync-package.sh` demotes all `# Maintainer:` lines (except line 1, which carries the local maintainer) to `# Contributor:` during both bootstrap and update. This is the preferred declarative pattern for authorship management during hybrid imports.
:   **Typical Usage**: Set on packages imported from the AUR or Arch GitLab where upstream maintainer credits should be preserved as contributors rather than maintainers.

### Variant Builds

**_repo_subarch** (string)
:   Defines the deployment sub-architecture for variant package builds (e.g., `x86_64_v3`, `x86_64_v4`). Read by `arch-builder.sh` to inject corresponding CFLAGS and by `release.yml` to route `.pkg.tar.zst` artifacts to the correct repository directory.
:   **Typical Usage**: Set only on variant PKGBUILDs (e.g., `packages/mypkg-v3/PKGBUILD`). Base packages must not set this variable. Mutually exclusive with `_deploy_aur`.

**_auto_merge_build** (boolean)
:   When `true`, `scripts/sync-package.sh` automatically accepts upstream build logic changes (C8 concern) without injecting a `# PREREVIEW:` marker. The default is to gate build changes for human review.
:   **Typical Usage**: Set on packages where upstream build logic changes are explicitly trusted and do not require manual verification.

---

## FOOTNOTES & CITATIONS

[^1]: **Arch Wiki: VCS package guidelines**. "VCS packages should provide and conflict with the non-VCS version of the package." *Reasoning: This justifies the use of `_pkgname` to systematically generate the 'provides' and 'conflicts' arrays in variant packages.*
