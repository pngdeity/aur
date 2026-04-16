# AGENTS.md - Arch Linux Build System (ABS) Engineering Standards

This document defines the specialized mandates and expert workflows for contributing to Arch Linux package files within this repository. Adhere to these standards to ensure the highest quality, security, and automation compatibility.

## 1. Foundational Documentation & Specifications

All contributions to the `packages/` directory must adhere to the following canonical specifications.

### Core Manuals (The "Laws")
- **[PKGBUILD(5)](https://man.archlinux.org/man/PKGBUILD.5)**: Primary reference for the build description file.
- **[pkgctl(1)](https://man.archlinux.org/man/pkgctl.1)**: Unified command-line frontend for devtools; the modern standard for package management and building.
- **[.SRCINFO(5)](https://man.archlinux.org/man/SRCINFO.5.en)**: Mandatory for metadata consistency and AUR helper compatibility.
- **[updpkgsums(8)](https://man.archlinux.org/man/updpkgsums.8)**: Utility for updating integrity hashes.
- **[makepkg(8)](https://man.archlinux.org/man/makepkg.8)**: The primary tool for build logic validation and testing.

### Arch Linux Wiki Guides
The following articles provide the standard for specific package types and quality controls:
- **[Creating packages](https://wiki.archlinux.org/title/Creating_packages)**: The foundation for all new package development.
- **[VCS package guidelines](https://wiki.archlinux.org/title/VCS_package_guidelines)**: Mandatory for `*-git` packages (e.g., `gemini-cli-git`).
- **[Patching packages](https://wiki.archlinux.org/title/Patching_packages)**: Critical for `opendoas` and `ranger-doas` maintenance.
- **[.SRCINFO Wiki](https://wiki.archlinux.org/title/.SRCINFO)**: Guidelines for metadata generation.
- **[namcap](https://wiki.archlinux.org/title/namcap)**: Tool for `PKGBUILD` and package linting.
- **[Arch User Repository](https://wiki.archlinux.org/title/Arch_User_Repository)**: Standards for AUR compatibility.
- **[Unofficial user repositories](https://wiki.archlinux.org/title/Unofficial_user_repositories)**: Context for repository database management.
- **[Security Guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines#Security)**: Critical for privileged/setuid packages like `opendoas`.
- **[Building in a clean chroot](https://wiki.archlinux.org/title/DeveloperWiki:Building_in_a_clean_chroot)**: The standard for environment isolation.
- **[Reproducible Builds](https://wiki.archlinux.org/title/Reproducible_Builds)**: Mandatory use of `SOURCE_DATE_EPOCH` for consistency.

> **Note on Research Depth:** The articles cited above are the most relevant for this repository. However, completeness is achieved by following internal hyperlinks within these articles to related sub-topics (e.g., specific language guidelines like Node.js or CMake) as needed for the task at hand.

## 2. Project-Specific Mandates

### DRY Automation & Oblivious Builds
- **No In-File Fetching**: `PKGBUILD` files must NEVER contain `curl`, `jq`, or manual changelog fetching logic in `prepare()`.
- **Centralized Automation**: All intelligent sync tasks (versioning, hashes, changelogs) are offloaded to `scripts/sync-package.sh`.
- **Devtools Integration**: Prefer `pkgctl` subcommands (e.g., `pkgctl build`, `pkgctl version upgrade`) over legacy standalone scripts for environment-consistent results.
- **Dynamic Injection**: The `changelog=` variable is injected at build-time by the CI runner; do not add it manually to the Git source.

### Identity & Security
- **Maintainer Identity**: Every package must use: `# Maintainer: pngdeity <pngdeity@tutanota.com>`.
- **Reproducibility**: Use `local _build_date=$(date --utc --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +"%Y-%m-%d")` for any time-sensitive build metadata.

## 3. Mandatory Verification Workflow

Before proposing or pushing a change to any package, an agent MUST perform:
1. **Sync**: Run `bash scripts/sync-package.sh <pkgname> <version>` to update hashes and changelogs.
2. **Lint**: Run `namcap PKGBUILD`.
3. **Metadata**: Run `makepkg --printsrcinfo > .SRCINFO`.
4. **Clean Build**: Verify the build in a clean environment (locally via `pkgctl build` or via CI trigger).
5. **Security/Quality**: Use `pkgctl diff` to compare against current repository state where applicable.
