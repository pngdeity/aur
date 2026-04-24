# Architecture: Hybrid Upstream Integration & Identity Protection

This document outlines the specialized maintenance processes and automation logic implemented in this repository to handle Arch Linux package derivatives and their upstream relationships.

## 1. Centralized Asset Management (Gemini-CLI)
To eliminate duplication across the multiple `gemini-cli` variants (`stable`, `-preview`, `-nightly`, `-git`), a shared asset synchronization pattern is used.

- **Source of Truth**: `common/gemini-cli-settings.json` at the repository root.
- **Trigger**: PKGBUILDs defining `_use_common_gemini_settings=true`.
- **Logic**: During the synchronization phase, `scripts/sync-package.sh` automatically copies the central settings file into the package source directory before updating hashes and metadata.

## 2. Hybrid Upstream Integration
The repository employs a "Metadata Overlay" strategy to inherit packaging improvements from official Arch Linux Maintainers while preserving local customizations.

### A. Two-Tier Tracking
Packages can track two distinct types of "Upstreams" simultaneously via `.nvchecker.toml`:
1.  **Software Upstream (GitHub/NPM)**: Monitors the source code for new releases.
2.  **Packaging Upstream (Arch GitLab)**: Monitors the official Arch Linux repository for changes to the `PKGBUILD`, patches, or system configurations (e.g., unit files).

### B. The Shield: Identity Protection
To prevent derivative packages (variants) from being "overwritten" by stable upstream metadata during a merge, `scripts/sync-package.sh` implements an identity shield:
1.  **Snapshot**: Before merging, it records local-owned variables: `pkgname`, `pkgver`, `pkgrel`, `source`, `provides`, `conflicts`, and `replaces`.
2.  **Hybrid Merge**: It performs a 3-way merge (`git merge-file`) between the local `PKGBUILD`, a cached upstream state (`.PKGBUILD.upstream`), and the new official `PKGBUILD`.
3.  **Restore**: It automatically re-applies the snapshotted variables, ensuring the package remains a variant of the correct version.

### C. Automated Asset Discovery
The sync script automatically scans the upstream `source` array for local files (patches, `.install` scripts, `.service` files). If a file exists in the official repository but is missing locally, the script automatically downloads it via `curl` from GitLab, ensuring your package never misses a new standard established by official maintainers.

## 3. Maintenance Workflows

### Manual Intervention
- **Merge Conflicts**: If upstream changes conflict with local surgical edits, the sync script will flag the conflict markers in the `PKGBUILD` for manual resolution.
- **Dependency Drift**: If `updpkgsums` detects a change in an upstream manifest (like `package.json`), the resulting diff in `sha256sums` serves as a signal to manually review and update the `depends` array.

### Pkgrel Management
- If `pkgver` changes: `pkgrel` is reset to `1`.
- If only the packaging configuration changes (via 3-way merge): `pkgrel` is **incremented** (e.g., `1` -> `2`) to notify users of the configuration update.
