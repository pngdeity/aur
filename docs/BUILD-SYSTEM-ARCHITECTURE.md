# Build System Architecture: Hybrid Upstream & Identity Protection

This document outlines the specialized maintenance processes, automation logic, and foundational philosophy implemented in this repository to handle Arch Linux package derivatives and their upstream relationships.

## 1. Architectural Philosophy

The build system is designed around three abstract requirements that ensure maintainability and automation compatibility.

### A. The Hybrid Merge Pattern
The orchestration layer is responsible for reconciling two conflicting states: Upstream Innovation (new dependencies/logic) and Local Identity (maintainer headers, variants, custom patches).
- **Requirement**: The system MUST snapshot local "Identity Variables" (`pkgname`, `pkgver`, `pkgrel`) before merging upstream changes, ensuring that the package remains distinct within this repository's namespace while benefiting from upstream logic updates. [^1]

### B. Oblivious Build standard
A `PKGBUILD` MUST be "oblivious" to the internet at build-time. 
- **Requirement**: No `curl`, `wget`, or API calls are permitted within any `PKGBUILD` function (e.g., `prepare()`). All intelligent data fetching (versions, changelogs, assets) MUST be offloaded to the pre-build synchronization phase. [^2]

### C. Idempotent Transformation Hooks
When a package requires non-standard modifications (like cleaning up poorly written upstream code), the modifications MUST NOT be manual.
- **Requirement**: Custom logic MUST be isolated in an external hook (`update.sh`). This hook MUST be idempotent, meaning multiple executions on the same source produce the same result, preventing cumulative corruption during repeated sync cycles. [^3]

---

## 2. Implementation: Identity Protection (The Shield)

To prevent derivative packages (variants) from being "overwritten" by stable upstream metadata during a merge, `scripts/sync-package.sh` implements an identity shield:

1.  **Snapshot**: Before merging, it records local-owned variables: `pkgname`, `pkgver`, `pkgrel`, `source`, `provides`, `conflicts`, and `replaces`.
2.  **Hybrid Merge**: It performs a 3-way merge (`git merge-file`) between the local `PKGBUILD`, a cached upstream state (`.PKGBUILD.upstream`), and the new official `PKGBUILD`.
3.  **Restore**: It automatically re-applies the snapshotted variables, ensuring the package remains a variant of the correct version.

---

## 3. Centralized Asset Management (Gemini-CLI)

To eliminate duplication across the multiple `gemini-cli` variants (`stable`, `-preview`, `-nightly`, `-git`), a shared asset synchronization pattern is used.

- **Source of Truth**: `common/gemini-cli-settings.json` at the repository root.
- **Trigger**: PKGBUILDs defining `_use_common_gemini_settings=true`.
- **Logic**: During the synchronization phase, `scripts/sync-package.sh` automatically copies the central settings file into the package source directory before updating hashes and metadata.

---

## 4. Maintenance Workflows

### Automated Asset Discovery
The sync script automatically scans the upstream `source` array for local files (patches, `.install` scripts, `.service` files). If a file exists in the official repository but is missing locally, the script automatically downloads it via `curl` from GitLab, ensuring your package never misses a new standard established by official maintainers.

### Pkgrel Management
- If `pkgver` changes: `pkgrel` is reset to `1`.
- If only the packaging configuration changes (via 3-way merge): `pkgrel` is **incremented** (e.g., `1` -> `2`) to notify users of the configuration update.

---

## FOOTNOTES & CITATIONS

[^1]: **Arch Wiki: PKGBUILD**. "The PKGBUILD file is a shell script that contains the build information required by Arch Linux packages." *Reasoning: Our hybrid merge extends this definition by treating the PKGBUILD as a mergeable data object rather than a static script.*
[^2]: **makepkg(8)** (Pacman Manual). "makepkg is a script to automate the building of packages... it will do the rest: download and validate source files." *Reasoning: makepkg expects sources to be declared in the source array for integrity checking. In-file fetching bypasses hash verification and violates the Arch Build System's security model.*
[^3]: **Arch Wiki: Creating packages**. "Package integrity is essential... hashes are used to verify the integrity of all source files." *Reasoning: Idempotent hooks ensure that the 'transformed' source remains predictable, allowing for consistent hash generation across different build environments.*
