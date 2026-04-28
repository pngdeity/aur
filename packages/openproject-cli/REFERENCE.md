# REFERENCE.md - Repository-Specific PKGBUILD Extensions

This document defines the custom variables and architectural requirements for package build files within this repository. These extensions allow for automated synchronization with upstream sources while preserving repository-specific identity and configurations.

## OPTIONS AND DIRECTIVES (CUSTOM)

The following variables are interpreted by the repository's orchestration layer (e.g., `sync-package.sh`) to manage the lifecycle of a package. These are NOT standard Arch Linux variables and are ignored by `makepkg`.

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

### Context Preservation

**_pkgname** (string)
:   Stores the canonical name of the software, isolated from repository-specific suffixes like `-git`, `-nightly`, or `-preview`.
:   **Typical Usage**: Essential for monorepo environments where multiple variants of the same software exist, allowing shared scripts to reference the base product correctly.

---

## ARCHITECTURAL PHILOSOPHY

The build system in this repository is designed around three abstract requirements that ensure maintainability and automation compatibility.

### 1. The Hybrid Merge Pattern
The orchestration layer is responsible for reconciling two conflicting states:
- **Upstream Innovation**: New dependencies, build flags, and sources defined by the primary package maintainers.
- **Local Identity**: Repository-specific maintainer headers, version tracking logic, and custom patches.

**Requirement**: The system MUST snapshot local "Identity Variables" (pkgname, pkgver, pkgrel) before merging upstream changes, ensuring that the package remains distinct within this repository's namespace while benefiting from upstream logic updates. [^1]

### 2. Oblivious Build standard
A `PKGBUILD` MUST be "oblivious" to the internet at build-time. 
- **Requirement**: No `curl`, `wget`, or API calls are permitted within any `PKGBUILD` function (e.g., `prepare()`). All intelligent data fetching (versions, changelogs, assets) MUST be offloaded to the pre-build synchronization phase. [^2]

### 3. Idempotent Transformation Hooks
When a package requires non-standard modifications (like cleaning up poorly written upstream code), the modifications MUST NOT be manual.
- **Requirement**: Custom logic MUST be isolated in an external hook (`update.sh`). This hook MUST be idempotent, meaning multiple executions on the same source produce the same result, preventing cumulative corruption during repeated sync cycles. [^3]

---

## FOOTNOTES & CITATIONS

[^1]: **Arch Wiki: PKGBUILD** (Last Modified: 25 March 2026). "The PKGBUILD file is a shell script that contains the build information required by Arch Linux packages." *Reasoning: Our hybrid merge extends this definition by treating the PKGBUILD as a mergeable data object rather than a static script.*
[^2]: **makepkg(8)** (Pacman Manual). "makepkg is a script to automate the building of packages... it will do the rest: download and validate source files." *Reasoning: makepkg expects sources to be declared in the source array for integrity checking. In-file fetching bypasses hash verification and violates the Arch Build System's security model.*
[^3]: **Arch Wiki: Creating packages** (Last Modified: 1 April 2026). "Package integrity is essential... hashes are used to verify the integrity of all source files." *Reasoning: Idempotent hooks ensure that the 'transformed' source remains predictable, allowing for consistent hash generation across different build environments.*
[^4]: **Arch Wiki: VCS package guidelines** (Last Modified: 24 March 2026). "VCS packages should provide and conflict with the non-VCS version of the package." *Reasoning: This justifies the use of `_pkgname` to systematically generate the 'provides' and 'conflicts' arrays in variant packages.*
