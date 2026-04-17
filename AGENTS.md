# AGENTS.md - Arch Linux Build System (ABS) Engineering Standards

This document defines the specialized mandates and expert workflows for contributing to Arch Linux package files within this repository. Adhere to these standards to ensure the highest quality, security, and automation compatibility.

## 1. Foundational Documentation & Specifications

All contributions to the `packages/` directory must adhere to the following canonical specifications.

### Core Manuals (The "Laws")

#### 1. Build Foundation
- **PKGBUILD(5)**: Primary reference for the build description file. Use `man 5 PKGBUILD`.
- **makepkg(8)**: Primary tool for build logic validation and testing. Use `man 8 makepkg`.
- **updpkgsums(8)**: Utility for updating integrity hashes. Use `man 8 updpkgsums`.
- **.SRCINFO(5)**: Mandatory for metadata consistency and AUR helper compatibility. Use `man 5 SRCINFO`.

#### 2. Environment & Configuration
- **devtools(7)**: Developer tools for the Arch Linux distribution. Use `man 7 devtools`.
- **makepkg.conf(5)**: System-wide build configuration (CFLAGS, environment). Use `man 5 makepkg.conf`.
- **pacman.conf(5)**: Pacman package manager configuration. Use `man 5 pacman.conf`.

#### 3. Unified Package Control (pkgctl)
- **pkgctl(1)**: Unified frontend for devtools. Use `man 1 pkgctl`.

##### A. Build & Audit
- **pkgctl-build(1)**: Build packages inside a clean chroot.
- **pkgctl-diff(1)**: Compare package files and builds.

##### B. Repository & AUR
- **pkgctl-repo(1)**: Manage Git packaging repositories. (Sub-pages: `clean`, `clone`, `configure`, `create`, `switch`, `web`)
- **pkgctl-aur(1)**: Interact with the AUR. (Sub-page: `aur-drop-from-repo`)
- **pkgctl-search(1)**: Search expressions across the packaging group.

##### C. Release & Database
- **pkgctl-release(1)**: Commit, tag, and upload build artifacts.
- **pkgctl-db(1)**: Pacman database modification. (Sub-pages: `move`, `remove`, `update`)

##### D. Versioning & Upstream Discovery
- **nvchecker(1)**: New version checker for software releases. Use `man 1 nvchecker`.
- **nvtake(1)**: Manage the state of software version checks. Use `man 1 nvtake` (see also [Debian Manual](https://manpages.debian.org/testing/python3-nvchecker/nvtake.1)).
- **pkgctl-version(1)**: Upstream version tracking frontend. (Sub-pages: `check`, `setup`, `upgrade`)

##### E. Compliance & Infrastructure
- **pkgctl-auth(1)**: Authenticate with services (GitLab). (Sub-pages: `login`, `status`)
- **pkgctl-license(1)**: Check and manage package license compliance. (Sub-pages: `check`, `setup`)
- **pkgctl-issue(1)**: Work with GitLab packaging issues. (Sub-pages: `close`, `comment`, `create`, `edit`, `list`, `move`, `reopen`, `view`)

#### 4. Quality Control & Legacy devtools
- **checkpkg(1)**: Check for broken dependencies and SONAME bumps. Use `man 1 checkpkg`.
- **diffpkg(1)**: Compare the contents of two packages. Use `man 1 diffpkg`.
- **makerepropkg(1)**: Test reproducible builds. Use `man 1 makerepropkg`.
- **sogrep(1)**: Search for packages linking against specific libraries. Use `man 1 sogrep`.
- **makechrootpkg(1)**: Granular control over clean chroot builds. Use `man 1 makechrootpkg`.

#### 5. AUR Helper Tools (aurutils)
- **aur(1)**: Helper tools for the Arch User Repository. Use `man 1 aur`.
- **aur-sync(1)**: Synchronize local repositories with the AUR. Use `man 1 aur-sync`.
- **aur-repo(1)**: Manage local package repositories. Use `man 1 aur-repo`.
- **aur-vercmp(1)**: Version comparison for AUR packages. Use `man 1 aur-vercmp`.
- **aur-chroot(1)**: Clean chroot build wrapper for AUR. Use `man 1 aur-chroot`.

#### 6. Search & Discovery
- **Apropos**: If no specific manual is found, search via `apropos <keyword>`.

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

### Conflict Resolution & Behavioral Guidance
- **Source Discrepancies**: If a man page (the "Laws") and an Arch Wiki Article seem to have conflicting information, you MUST note the discrepancy to the user.
- **Reporting Requirements**: Your report must include:
    1.  The specific man page and the Arch Wiki article involved.
    2.  The exact location/section of the contradicting information in each source.
    3.  A technical analysis of *why* the information is contradictory, supported by references (e.g., version changes, upstream bug reports, or environment-specific defaults).

## 2. Project-Specific Mandates

### Upstream Discovery & Sovereignty
- **Authority Priority**: When seeking upstream packaging logic, your search order MUST be: 1. Official Arch GitLab (`archlinux/packaging/packages/`), 2. The AUR (`aur.archlinux.org`), 3. Upstream source repository.
- **Official GitLab Nuance**: While the Official GitLab is the most authoritative source, you MUST acknowledge that its `PKGBUILD`s may contain environment-specific configurations (e.g., internal build server paths) that require stripping during a Hybrid Import.
- **AUR Preference**: If a package is explicitly labeled as an AUR variant (e.g., in its name or `_upstream_aur_pkg`), prioritize the AUR source over the Official GitLab to preserve community-driven AUR optimizations.

### Standard Operating Routine: The Maintenance Pulse
To maintain a proactive (not reactive) repository, you MUST follow this routine without awaiting specific user direction:
1.  **Monitor**: Periodically run `nvchecker -c .nvchecker.toml` to identify upstream version drifts.
2.  **Evaluate**: Compare `nvchecker` output against `oldver.json`. Every detected delta constitutes a MANDATORY task to initiate the `sync-package.sh` workflow.
3.  **Acknowledge (The nvtake Guard)**: Upon a successful sync and commit, you MUST run `nvtake <pkgname>` to synchronize the internal state. Since `nvtake` may lack a local manual, refer strictly to the [Debian Manual](https://manpages.debian.org/testing/python3-nvchecker/nvtake.1) and NEVER hallucinate flags.
4.  **Synchronize**: Ensure that every `PKGBUILD` update is accompanied by a `.SRCINFO` regeneration in the same commit.

### Event-Driven Publishing (Platform Abstraction)
- **Infrastructure Abstraction**: You are responsible for the **Source of Truth** (the Git repository). The actual deployment, database signing, and artifact hosting are handled by an external, event-driven infrastructure.
- **The Interface**: Your primary "Publish" button is `git push`. Pushing a verified, signed commit to the remote tracking branch constitutes a formal, non-reversible request for the infrastructure to build and deploy.
- **Sovereignty**: Do not attempt to manage remote secrets, tokens, or runner configurations unless explicitly instructed. Focus exclusively on ensuring the local state is perfect before the push.

### Tool Supremacy & Precision
- **Absolute Mandate**: You MUST NEVER bypass the official devtools/pkgctl ecosystem. Direct calls to `makepkg` or manual `sed` logic in `prepare()` are prohibited unless a corresponding `pkgctl` subcommand or `update.sh` hook is technically impossible.
- **Help-First Protocol**: If a subcommand has not been used in the current session, run `pkgctl <subcommand> --help` to verify the exact syntax and available flags.

### Semantic Commit Standards
- **Format**: All commit messages MUST follow the `<type>: <scope>: <description>` convention.
- **Types**: Use `feat` (new features/packages), `fix` (bug fixes), `docs` (documentation updates), `chore` (maintenance/tooling), and `pkg` (generic package updates).
- **Scope**: The scope MUST be the package name (e.g., `opendoas`) or the functional area (e.g., `scripts`).
- **Package Updates**: Updates triggered by `sync-package.sh` MUST use the format: `<pkgname>: update to <version>`.
- **Imperative Mood**: Use the imperative mood in the description (e.g., "add Rowhammer patch" instead of "added Rowhammer patch").

### Identity & Security
- **Maintainer Identity**: Every package must use: `# Maintainer: pngdeity <pngdeity@tutanota.com>`.
- **Reproducibility**: Use `local _build_date=$(date --utc --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +"%Y-%m-%d")` for any time-sensitive build metadata.

### New Package Initialization (Bootstrap Workflow)
When adding a new package to the `packages/` directory, use the following automated sequence to ensure consistency:
1.  **Skeleton**: Create the package directory and a minimal `PKGBUILD` defining the upstream source variables (`_upstream_aur_pkg` or `_upstream_arch_repo`).
2.  **Bootstrap**: Run `bash scripts/sync-package.sh <pkgname> <version>`. This fetches the upstream PKGBUILD, initializes the tracking state, and updates hashes.
3.  **nvchecker Setup**: Within the package directory, run `pkgctl version setup`. This automatically generates a valid `.nvchecker.toml` from the PKGBUILD source array.
4.  **Local AGENTS.md**: Create a local policy file referencing the upstream source and documenting package-specific tribal knowledge.
5.  **Global Discovery**: Register the new package in the root `.nvchecker.toml`.

### Hybrid Import & Cleanup SOP
If an upstream `PKGBUILD` requires "cleanup" (formatting, logic improvements, or custom patches), you MUST NOT perform these edits manually in the `PKGBUILD`. Instead, use the **Idempotent Transformation** pattern:
1.  **Isolate logic in `update.sh`**: Place all cleanup logic (e.g., `sed` replacements, variable reordering, or `patch` applications) into the package-local `./update.sh` script.
2.  **Automated Execution**: The `scripts/sync-package.sh` tool automatically calls `./update.sh` after the upstream merge but before hash generation.
3.  **Conflict Minimization**: By using a script to "fix" the upstream file after every merge, you ensure your improvements are preserved even when the upstream source changes, without causing permanent merge conflicts.
4.  **Verification**: After a transformation, run `namcap PKGBUILD` to verify that the cleanup has actually improved the package quality according to Arch standards.

### Dependency Management & Coordinated Rebuilds
- **Cautionary Mandate**: Standard Operating Procedures (SOPs) for cross-package dependency updates and coordinated rebuilds are NOT fully developed.
- **Human Oversight**: If a package update introduces a breaking change (e.g., a SONAME bump) that affects other packages in the repository, you MUST seek human guidance before proceeding with a multi-package modification.
- **Validation**: Use `sogrep` and `checkpkg` to identify the blast radius of a dependency change, but do not attempt a coordinated release autonomously.

### Hierarchical Policies (AGENTS.md)
- **New Packages**: Upon creation of a new subdirectory in `packages/`, you MUST create a local `AGENTS.md` file.
- **Reference Mandate**: The local `AGENTS.md` MUST include a strict instruction to reference the upstream source repository for all build, testing, and structural information.
- **Tribal Knowledge**: The file MUST document package-specific "tribal knowledge," including functional limitations (e.g., backgrounding support), specialized build flags (e.g., CMake types), and environment isolation rules.

## 3. Mandatory Verification Workflow

Before proposing or pushing a change to any package, an agent MUST perform:
1. **Sync**: Run `bash scripts/sync-package.sh <pkgname> <version>` to update hashes and changelogs.
2. **Lint**: Run `namcap PKGBUILD`.
3. **Metadata**: Run `makepkg --printsrcinfo > .SRCINFO`.
4. **Clean Build**: Verify the build in a clean environment (locally via `pkgctl build` or via CI trigger).
5. Security/Quality: Use `pkgctl diff` to compare against current repository state where applicable.

## 3.1. Pragmatic Diagnostic & Self-Correction Loop

To ensure high-fidelity results while avoiding common agent failure modes (like "tool-tyranny" or hallucinated success), the following patterns MUST be employed:

1.  **Surgical Root Cause Analysis**: If a build or synchronization fails, the agent MUST NOT guess. Use `grep` or `awk` to locate the *first* fatal error in the logs (e.g., `ld: error:`, `npm ERR!`, `CMake Error`) to identify the actual breakage before proposing a fix.
2.  **Deterministic Idempotency**: All transformation logic in `update.sh` MUST be idempotent. Ensure that `sed` or `patch` operations produce the same state regardless of execution count. Never inject non-deterministic data (like raw `date` or `hostname`) unless gated by `SOURCE_DATE_EPOCH`.
3.  **Validation vs. Tribal Knowledge**: Treat `namcap` as a consultant, not a judge. Use it to catch objective errors (bad permissions, missing licenses), but prioritize "Tribal Knowledge" in the local `AGENTS.md` for runtime dependencies or environmental requirements that static analysis may misidentify as "unnecessary."
4.  **Payload Sanity Check**: Before finalizing an update, perform a "sanity check" on the package payload using `pkgctl diff --list`. Verify that the primary binary, license file, and directory structure remain consistent; any disappearance of `/usr/bin/` targets or a payload size deviation of >10% MUST be investigated as a potential regression.

### Troubleshooting & Manual Intervention
If the automated pipeline fails, follow these specific recovery patterns:
- **Patch Failures**: If an upstream source change breaks an existing patch:
    1.  Clone upstream at the target version and attempt a manual `patch -p1`.
    2.  Resolve rejects (`.rej`), delete them, and generate a fresh patch via `git diff`.
    3.  Update the `PKGBUILD` and refresh checksums.
- **Checksum Failures**: If `updpkgsums` fails due to a re-rolled upstream release, verify the file content before committing the new hashes.
- **Security & GPG**: The repository uses `repo-add --sign`. For manual key setup:
    1.  Generate an RSA 4096-bit key (no expiry).
    2.  Export to armor: `gpg --export-secret-keys --armor <KEY_ID>`.
    3.  Store in GitHub Secret `REPO_GPG_KEY` for the `release.yml` workflow.

## 4. Future Mandates & Technical Debt

- [ ] **TODO: Package Decommissioning SOP**: Define a standard process for removing packages from the repository, including AUR dropping and discovery cleanup. (Due: Indeterminate)
- [ ] **TODO: Edge-Case Recovery Logic**: Define deterministic recovery paths for hybrid merge failures and 404 upstream assets. (Due: Upon `scripts/` directory refactor)
