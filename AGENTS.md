# AGENTS.md - Arch Linux Build System (ABS) Engineering Standards

This document defines the specialized mandates and expert workflows for
contributing to Arch Linux package files within this repository. Adhere to these
standards to ensure the highest quality, security, and automation compatibility.

## System Constraints

- **No privilege escalation**: `doas` authentication is unavailable in
  non-interactive mode. Never attempt `doas`, `sudo`, or any root-requiring
  command. For builds requiring a clean chroot (`pkgctl build`, etc.), report
  the step as pending human execution.

## 1. Foundational Documentation & Specifications

All contributions to the `packages/` directory must adhere to the following
canonical specifications.

### Core Manuals (The "Laws")

#### 1. Build Foundation

- **PKGBUILD(5)**: Primary reference for the build description file. Use
  `man 5 PKGBUILD`.
- **makepkg(8)**: Primary tool for build logic validation and testing. Use
  `man 8 makepkg`.
- **updpkgsums(8)**: Utility for updating integrity hashes. Use
  `man 8 updpkgsums`.
- **.SRCINFO(5)**: Mandatory for metadata consistency and AUR helper
  compatibility. Use `man 5 SRCINFO`.

#### 2. Environment & Configuration

- **devtools(7)**: Developer tools for the Arch Linux distribution. Use
  `man 7 devtools`.
- **makepkg.conf(5)**: System-wide build configuration (CFLAGS, environment).
  Use `man 5 makepkg.conf`.
- **pacman.conf(5)**: Pacman package manager configuration. Use
  `man 5 pacman.conf`.

#### 3. Unified Package Control (pkgctl)

- **pkgctl(1)**: Unified frontend for devtools. Use `man 1 pkgctl`.

##### A. Build & Audit

- **pkgctl-build(1)**: Build packages inside a clean chroot.
- **pkgctl-diff(1)**: Compare package files and builds.

##### B. Repository & AUR

- **pkgctl-repo(1)**: Manage Git packaging repositories. (Sub-pages: `clean`,
  `clone`, `configure`, `create`, `switch`, `web`)
- **pkgctl-aur(1)**: Interact with the AUR. (Sub-page: `aur-drop-from-repo`)
- **pkgctl-search(1)**: Search expressions across the packaging group.

##### C. Release & Database

- **pkgctl-release(1)**: Commit, tag, and upload build artifacts.
- **pkgctl-db(1)**: Pacman database modification. (Sub-pages: `move`, `remove`,
  `update`)

##### D. Versioning & Upstream Discovery

- **nvchecker(1)**: New version checker for software releases. Use
  `man 1 nvchecker`.
- **nvtake(1)**: Manage the state of software version checks. Use `man 1 nvtake`
  (see also
  [Debian Manual](https://manpages.debian.org/testing/python3-nvchecker/nvtake.1)).
- **pkgctl-version(1)**: Upstream version tracking frontend. (Sub-pages:
  `check`, `setup`, `upgrade`)

##### E. Compliance & Infrastructure

- **pkgctl-auth(1)**: Authenticate with services (GitLab). (Sub-pages: `login`,
  `status`)
- **pkgctl-license(1)**: Check and manage package license compliance.
  (Sub-pages: `check`, `setup`)
- **pkgctl-issue(1)**: Work with GitLab packaging issues. (Sub-pages: `close`,
  `comment`, `create`, `edit`, `list`, `move`, `reopen`, `view`)

#### 4. Quality Control & Legacy devtools

- **checkpkg(1)**: Check for broken dependencies and SONAME bumps. Use
  `man 1 checkpkg`.
- **diffpkg(1)**: Compare the contents of two packages. Use `man 1 diffpkg`.
- **makerepropkg(1)**: Test reproducible builds. Use `man 1 makerepropkg`.
- **sogrep(1)**: Search for packages linking against specific libraries. Use
  `man 1 sogrep`.
- **makechrootpkg(1)**: Granular control over clean chroot builds. Use
  `man 1 makechrootpkg`.

#### 5. AUR Helper Tools (aurutils)

- **aur(1)**: Helper tools for the Arch User Repository. Use `man 1 aur`.
- **aur-sync(1)**: Synchronize local repositories with the AUR. Use
  `man 1 aur-sync`.
- **aur-repo(1)**: Manage local package repositories. Use `man 1 aur-repo`.
- **aur-vercmp(1)**: Version comparison for AUR packages. Use
  `man 1 aur-vercmp`.
- **aur-chroot(1)**: Clean chroot build wrapper for AUR. Use `man 1 aur-chroot`.

#### 6. Search & Discovery

- **Apropos**: If no specific manual is found, search via `apropos <keyword>`.

### Source Authority Hierarchy

When sources contradict, the following ranking governs. Higher numbers outrank
lower numbers.

1. **Man Pages ("The Laws")** — `PKGBUILD(5)`, `makepkg(8)`, etc. Define
   canonical tool behavior, format, and constraints. Highest authority.
2. **Upstream Build Documentation** — The project's own README, build files
   (`CMakeLists.txt`, `Makefile`, `Cargo.toml`), and release notes.
   Authoritative for _how_ the software builds, subject to man page constraints.
3. **Official Arch GitLab PKGBUILDs** — Maintained by Arch Linux packagers.
   Authoritative for distro conventions, but may contain environment-specific
   paths that require stripping during hybrid import.
4. **Observable Build Behavior** — What actually compiles and passes `check()`
   in a clean chroot (`pkgctl build`). Empirical truth carries weight.
5. **Repo-Level Conventions** — This `AGENTS.md`, `docs/`, and `scripts/`.
   Define how _this_ repository operates.
6. **`namcap`** — Static analysis. A consultant, not a judge: catch objective
   errors but defer to higher-ranked sources on runtime dependencies and build
   logic.
7. **Arch Wiki Articles** — User-generated community guides. Valuable for
   established best practices, but are **advisory, not authoritative**. May be
   outdated. Consult them, verify against higher-ranked sources.

### Reading & Executing from Manual Pages

When consulting manual pages (Tier 1 Authority), you MUST understand the
distinction between a manual page identifier and the actual command invocation.

- **Understanding the Manual System:** If you are ever unsure how to search,
  format, or navigate manual pages, your first step MUST be to consult the
  manual page for the `man` command itself using `man 1 man`.
- **Man Page Names vs. Executables:** The name of a manual page (e.g.,
  `aur-chroot(1)`, `pkgctl-build(1)`) often represents a subcommand of a larger
  suite. It does **not** necessarily mean the executable is hyphenated.
- **The SYNOPSIS is Law:** To determine the correct executable usage, you MUST
  read the `SYNOPSIS` section of the specific manual page.
  - _Incorrect Assumption:_ Executing `aur-chroot` because the man page is
    `man 1 aur-chroot`.
  - _Correct Execution:_ Reading `man 1 aur-chroot`, observing the synopsis
    `aur chroot [options]`, and executing `aur chroot`.
- **Validation:** If a command fails with `command not found`, verify the actual
  invocation syntax in the man page's `SYNOPSIS` before assuming the tool is
  uninstalled.

### Arch Linux Wiki Guides

The following articles provide the standard for specific package types and
quality controls:

- **[Creating packages](https://wiki.archlinux.org/title/Creating_packages)**:
  The foundation for all new package development.
- **[VCS package guidelines](https://wiki.archlinux.org/title/VCS_package_guidelines)**:
  Mandatory for `*-git` packages (e.g., `amass-git`).
- **[Patching packages](https://wiki.archlinux.org/title/Patching_packages)**:
  Critical when a package carries out-of-tree `.patch` files.
- **[.SRCINFO Wiki](https://wiki.archlinux.org/title/.SRCINFO)**: Guidelines for
  metadata generation.
- **[namcap](https://wiki.archlinux.org/title/namcap)**: Tool for `PKGBUILD` and
  package linting.
- **[Arch User Repository](https://wiki.archlinux.org/title/Arch_User_Repository)**:
  Standards for AUR compatibility.
- **[Unofficial user repositories](https://wiki.archlinux.org/title/Unofficial_user_repositories)**:
  Context for repository database management.
- **[Security Guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines#Security)**:
  Critical for privileged/setuid packages like `opendoas`.
- **[Building in a clean chroot](https://wiki.archlinux.org/title/DeveloperWiki:Building_in_a_clean_chroot)**:
  The standard for environment isolation.
- **[Reproducible Builds](https://wiki.archlinux.org/title/Reproducible_Builds)**:
  Mandatory use of `SOURCE_DATE_EPOCH` for consistency.

> **Language & Framework Guidelines**: The articles above cover general
> packaging practice. For language-specific and framework-specific standards
> (Node.js, Python, CMake, etc.), consult
> [`docs/LANGUAGE-PACKAGING-GUIDELINES.md`](docs/LANGUAGE-PACKAGING-GUIDELINES.md)
> — a complete catalog of all 35
> [Arch package guidelines](https://wiki.archlinux.org/title/Category:Arch_package_guidelines)
> indexed by `makedepends` key and package type.
>
> **General Packaging Reference**: For articles covering PKGBUILD authoring,
> build verification, AUR interaction, and repository management, consult
> [`docs/WIKI-REFERENCE.md`](docs/WIKI-REFERENCE.md) — a structured catalog
> sourced from
> [Category:Package development](https://wiki.archlinux.org/title/Category:Package_development)
> and
> [Category:Package management](https://wiki.archlinux.org/title/Category:Package_management).
>
> All wiki articles are tier 7 (advisory) in the
> [source authority hierarchy](#source-authority-hierarchy). Report
> discrepancies per the [escalation protocol](#conflict-resolution--escalation).

### `docs/` Directory Reference

All files in `docs/` are part of the project's context. Consult any file
relevant to the current task.

| File                                                                                        | Purpose                                                                                                                                  |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [ABS-FUNDAMENTALS.md](docs/ABS-FUNDAMENTALS.md)                                             | Core ABS concepts: PKGBUILD lifecycle, makepkg, AUR structure                                                            |
| [AUTOMATED-SYSTEM-ARCHITECTURE.md](docs/AUTOMATED-SYSTEM-ARCHITECTURE.md)                   | Conceptual model: Lifecycle phases, concern taxonomy, review gates                                                       |
| [AUTOMATED-SYSTEM-DESIGN-IMPLEMENTATION.md](docs/AUTOMATED-SYSTEM-DESIGN-IMPLEMENTATION.md) | Technical design: Engine logic, classification regex, CI/CD workflows                                                    |
| [BASH-COMPLETION-CONVENTIONS.md](docs/BASH-COMPLETION-CONVENTIONS.md)                       | Shared bash-completion conventions (``_comp_`` namespace, ``_comp_compgen_help``)                                        |
| [LANGUAGE-PACKAGING-GUIDELINES.md](docs/LANGUAGE-PACKAGING-GUIDELINES.md)                   | Catalog of 35 language/framework Arch Wiki guidelines indexed by `makedepends`                                           |
| [PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md](docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md)       | Repository-specific PKGBUILD variables (``_upstream_*``, ``_githubname``, ``_tag``) and the `scripts/pkgvar` utility    |
| [PKGBUILD-RENDERER-CI.md](docs/PKGBUILD-RENDERER-CI.md)                                     | PKGBUILD renderer and CI integration design                                                                              |
| [PKL-CROSS-PHASE-EVALUATION.md](docs/PKL-CROSS-PHASE-EVALUATION.md)                         | Decision: Pkl selected over KCL/CUE                                                                                      |
| [PKL-SCHEMA-DESIGN.md](docs/PKL-SCHEMA-DESIGN.md)                                           | Pkl PKGBUILD schema design                                                                                               |
| [REGO-POLICY-ENGINE.md](docs/REGO-POLICY-ENGINE.md)                                         | OPA/Conftest policy engine design                                                                                        |
| [SRCINFO-VERSION-CONTROL-POLICY.md](docs/SRCINFO-VERSION-CONTROL-POLICY.md)                 | Policy: `.SRCINFO` is a build artifact, not version-controlled                                                           |
| [TODO.md](docs/TODO.md)                                                                     | Outstanding work items                                                                                                   |
| [WIKI-REFERENCE.md](docs/WIKI-REFERENCE.md)                                                 | Catalog of 17 general Arch Wiki articles organized by task domain                                                        |

### `docs/archive/` — Retained Reasoning Artifacts

| File                                                                   | Purpose                                           |
| ---------------------------------------------------------------------- | ------------------------------------------------- |

(No archived documents. Superseded design artifacts are removed — git history preserves prior versions.)

### Package Context Discovery

Before modifying any package in `packages/`:

1. Open the `PKGBUILD` and scan `makedepends` against
   [`docs/LANGUAGE-PACKAGING-GUIDELINES.md`](docs/LANGUAGE-PACKAGING-GUIDELINES.md)
   — every matching entry has specific packaging standards.
2. Scan `pkgname` against both catalogs for package-type triggers (`-git`
   suffix, setuid binaries, etc.).
3. If a package-local `AGENTS.md` exists, read it — its exceptions take
   precedence over general guidelines.
4. For task-specific guidance (PKGBUILD authoring, build verification, AUR, repo
   management), consult [`docs/WIKI-REFERENCE.md`](docs/WIKI-REFERENCE.md) by
   task domain.

### Agent Skills

Multi-step workflows are packaged as Agent Skills in `.agents/skills/`. The
agent router auto-loads these when a matching task is detected via the skill's
`description` field.

| Skill                | Description                                                            |
| -------------------- | ---------------------------------------------------------------------- |
| `pkg-update`         | Update a package to a new upstream version (sync, verify, acknowledge) |
| `pkg-bootstrap`      | Initialize a new package (skeleton, bootstrap, nvchecker, discovery)   |
| `pkg-patch-recovery` | Recover from patch failures and checksum mismatches                    |

### Conflict Resolution & Escalation

If any two sources in the hierarchy above contradict:

- The **higher-ranked** source governs implementation.
- You **MUST** note the discrepancy to the user. The report must include:
  1. Identification of both conflicting sources (with exact location/section).
  2. The specific contradictory claim from each source.
  3. A technical analysis of _why_ the information conflicts (e.g., version
     drift, upstream API changes, environment-specific defaults, or stale wiki
     content).
- Do not silently choose one source over another.

## 2. Project-Specific Mandates

### Upstream Discovery & Sovereignty

- **Authority Priority**: When seeking upstream packaging logic, your search
  order MUST be: 1. Official Arch GitLab (`archlinux/packaging/packages/`), 2.
  The AUR (`aur.archlinux.org`), 3. Upstream source repository.
- **Official GitLab Nuance**: Official GitLab PKGBUILDs are the **first place to
  look** (tier 3 in the hierarchy), but may contain environment-specific paths
  (e.g., internal build server paths) that require stripping during a Hybrid
  Import.
- **AUR Preference**: If a package is explicitly labeled as an AUR variant
  (e.g., in its name or `_upstream_aur_pkg`), prioritize the AUR source over the
  Official GitLab to preserve community-driven AUR optimizations.

### Standard Operating Routine: The Maintenance Pulse

To maintain a proactive (not reactive) repository, you MUST periodically run
`nvchecker -c .nvchecker.toml` to identify upstream version drifts. Every
detected delta must be resolved via the `pkg-update` skill, which handles the
full sync → verify → acknowledge cycle.

### Publishing Targets & Platform Responsibilities

This repository produces three types of deployable artifacts, each with a
distinct target and responsibility boundary:

| Artifact                             | Produced By                                                         | Target                                                                                                                   | Responsibility                                                                                    |
| ------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| **AUR PKGBUILDs**                    | CI/CD pipeline (`release.yml` → `scripts/aur-deploy.py` → git push) | `aur.archlinux.org` — the Arch User Repository hosts these PKGBUILDs for end users and AUR helpers to download and build | **This repository** processes and pushes AUR-compatible PKGBUILDs to their respective AUR remotes |
| **Binary packages** (`.pkg.tar.zst`) | `release.yml` → `makepkg`                                           | Apache host (`/var/www/html/repo/nightly/`) — serves a pacman-compatible repository database                             | **Release pipeline** (`release.yml`) handles database generation, signing, and `rsync` deployment |
| **Builder image**                    | `builder-image.yml` → Docker build                                  | `ghcr.io/<org>/<repo>/arch-builder`                                                                                      | **CI/CD pipeline** builds and pushes on Dockerfile changes                                        |

- **The Interface**: The primary publishing interface is the CI/CD pipeline. For
  binary packages and the builder image, the pipeline triggers automatically on
  discovery of upstream changes. For AUR PKGBUILDs, the pipeline processes
  repo-local PKGBUILDs into AUR-compatible output and pushes them to the AUR as
  a deployment step.
- **Sovereignty**: Do not attempt to manage remote secrets, tokens, or runner
  configurations unless explicitly instructed. Focus on ensuring the local state
  and build output are correct.

### AUR Deployment Gate

- **_deploy_aur Flag**: Packages intended for AUR publication must set
  `_deploy_aur=true` in the PKGBUILD. The `release.yml` pipeline runs
  `scripts/aur-deploy.py` for each flagged package after successful builds. The
  script processes the repo PKGBUILD (inlines `source` directives, strips
  repo-local `_`-prefixed variables and `# PREREVIEW:` markers, generates
  `.SRCINFO`) and pushes to `aur.archlinux.org`.
- **Mutual Exclusion**: `_deploy_aur=true` and `_repo_subarch` are mutually
  exclusive. `aur-deploy.py` hard-blocks this combination. Variant packages are
  build targets only — never AUR-deployed.

### Variant Builds (Sub-Architecture Optimization)

- **Naming Convention**: Variant packages use a suffix on the directory name
  matching the deployment sub-architecture (e.g., `packages/mypkg-v3/` for
  x86-64-v3 builds). The `pkgname` remains identical to the base package —
  differentiation is via an elevated `pkgrel` (ALHP pattern: base `pkgrel=1` →
  variant `pkgrel=1.1`). Pacman resolves the correct variant via repository
  priority in `pacman.conf`.
- **Variable**: `_repo_subarch` defines the deployment sub-architecture (e.g.,
  `x86_64_v3`) and controls CFLAGS injection in `arch-builder.py` and artifact
  routing in `release.yml`.
- **Thin PKGBUILDs**: Variant PKGBUILDs may use
  `source "../mypkg/PKGBUILD.common"` to share definitions with the base
  package. These are repo-local idioms that `aur-deploy.py` inlines during AUR
  processing. Variant PKGBUILDs themselves are never AUR-deployed.
- **Shared pkgdesc**: All packages sharing the same `_pkgname` value MUST use an
  identical `pkgdesc` string. This ensures consistent presentation across
  variant package listings (e.g., `apm`, `apm-bin`, `pkl-lsp`, `pkl-lsp-bin`).
  The `_pkgname` variable is the authoritative discriminator for variant groups.
  Run `python3 scripts/validate-pkgbuilds-pkl.py` to validate (includes conftest
  Rule 7 — `deny_pkgdesc_consistency`). The convention:
  `_pkgname` present and equal to `pkgname` signals the base package (variants
  exist); `_pkgname` present and unequal signals a variant sibling; `_pkgname`
  absent signals a standalone package with no variants.

- **provides/conflicts convention**: Per the Arch Wiki
  [PKGBUILD#conflicts netbeans example](https://wiki.archlinux.org/title/PKGBUILD#conflicts),
  pacman resolves variant mutual exclusivity transitively through `provides`.
  Every variant package must declare both `provides=("$_pkgname")` and
  `conflicts=("$_pkgname")` — enumerating sibling variants in `conflicts` is
  unnecessary. Two additional rules apply universally: (1) every entry in
  `conflicts` or `replaces` must have a matching entry in `provides` (no
  unprovided conflicts); (2) `provides` and `conflicts` must not contain the
  package's own `pkgname` (self-reference). These are enforced by conftest Rules
  4–5 (`no_unprovided_conflicts`, `no_self_reference`) in
  `policies/repository.rego`.

### Tool Supremacy & Precision

- **Absolute Mandate**: You MUST NEVER bypass the official devtools/pkgctl
  ecosystem. Direct calls to `makepkg` or manual `sed` logic in `prepare()` are
  prohibited unless a corresponding `pkgctl` subcommand or `update.sh` hook is
  technically impossible.
- **Help-First Protocol**: If a subcommand has not been used in the current
  session, run `pkgctl <subcommand> --help` to verify the exact syntax and
  available flags.
- **PKGBUILD Variable Extraction**: When extracting values (standard or custom
  `_`-prefixed) from a `PKGBUILD`, use `scripts/pkgvar` — a sandboxed
  bash-source utility that resolves ALL variables correctly, including
  references like `_pkgname=$_npmname` and `${pkgname#python-}`. Do NOT use
  `grep`/`cut`/`tr` patterns for variable extraction; these fail on quoted
  values and cannot resolve variable references. Boolean presence checks
  (`grep -q "pattern"`) are acceptable where the exact resolved value is not
  needed. Run `scripts/pkgvar --help` for the full interface.
- **pkgdesc Enforcement Topology** (4-layer): (1) Pre-commit hook
  (`.pre-commit-config.yaml`) blocks commits of inconsistent PKGBUILDs; (2)
  `sync-package.py` §5 warns during automated sync; (3) CI `discovery.yml` gate
  aborts the pipeline before `git push`; (4) CI `build.yml` gate blocks build of
  inconsistent packages. All four call `python3 scripts/validate-pkgbuilds-pkl.py`
  (which runs conftest Rule 7 — `deny_pkgdesc_consistency` in
  `policies/repository.rego`).

> **Note — Script Language Migration**: All automation scripts in `scripts/` are
> now Python (`.py`). Bash wrappers (`sync-package.sh`, `aur-deploy.sh`,
> `arch-builder.sh`, etc.) have been retired. Design documents under `docs/` may
> still reference `.sh` suffixes from the original Bash implementation — the
> logic and function names are unchanged; only the runtime has moved to Python.
> Package-local `update.sh` hooks (if present) are executed by `sync-package.py`
> regardless of their internal language.

### Semantic Commit Standards

- **Format**: All commit messages MUST follow the
  `<type>: <scope>: <description>` convention.
- **Types**: Use `feat` (new features/packages), `fix` (bug fixes), `docs`
  (documentation updates), `chore` (maintenance/tooling), and `pkg` (generic
  package updates).
- **Scope**: The scope MUST be the package name (e.g., `opendoas`) or the
  functional area (e.g., `scripts`).
- **Package Updates**: Updates triggered by `sync-package.py` MUST use the
  format: `<pkgname>: update to <version>`.
- **Imperative Mood**: Use the imperative mood in the description (e.g., "add
  Rowhammer patch" instead of "added Rowhammer patch").

### Identity & Security

- **Maintainer Identity**: Every package must use:
  `# Maintainer: pngdeity <pngdeity@tutanota.com>`.
- **Reproducibility**: Use
  `local _build_date=$(date --utc --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +"%Y-%m-%d")`
  for any time-sensitive build metadata.

### New Package Initialization (Bootstrap Workflow)

To add a new package, activate the `pkg-bootstrap` skill. It handles skeleton
creation, upstream dependency verification (for non-mirrored packages),
`sync-package.py` bootstrapping, `pkgctl version setup`, conditional local
`AGENTS.md` creation, and `.nvchecker.toml` registration.

**Critical**: For packages that do not mirror an existing Arch/AUR PKGBUILD (no
`_upstream_aur_pkg` or `_upstream_arch_repo`), all runtime dependencies MUST be
verified manually against the upstream project's dependency manifest. See the
`pkg-bootstrap` skill for the per-language manifest checklist.

### Hybrid Import & Cleanup SOP

If an upstream `PKGBUILD` requires "cleanup" (formatting, logic improvements, or
PKGBUILD metadata patches), you MUST NOT perform these edits manually in the
`PKGBUILD`. Instead, use one of two patterns depending on the change type:

1. **Declarative (preferred)**: For authorship demotion, set
   `_demote_upstream_maintainer=true` in the `PKGBUILD`. The sync script handles
   this centrally during both bootstrap and update. For asset synchronization
   across variants, use `_use_common_gemini_settings=true` (aspirational — no
   current packages use this).

2. **Imperative (`update.sh`)**: For genuinely unique per-package
   transformations that cannot be expressed declaratively (e.g., regenerating
   patches from upstream source, dynamic command extraction), place logic in a
   package-local `./update.sh` script. This script MUST be idempotent, MUST NOT
   modify PKGBUILD metadata (only source files), and runs with guaranteed
   preconditions: the PKGBUILD is finalized and all assets are present.

Source-code `.patch` files applied during `prepare()` belong in the `source[]`
array — they are standard Arch practice and are preserved across merges by
identity protection, not by `update.sh`.

3. **Automated Execution**: The `scripts/sync-package.py` tool runs `update.sh`
   (if executable) after the upstream merge and declarative rules but before
   hash generation.
4. **Verification**: After a transformation, run `namcap PKGBUILD` to verify
   that the cleanup has actually improved the package quality according to Arch
   standards.

### Dependency Management & Coordinated Rebuilds

- **Cautionary Mandate**: Standard Operating Procedures (SOPs) for cross-package
  dependency updates and coordinated rebuilds are NOT fully developed.
- **Human Oversight**: If a package update introduces a breaking change (e.g., a
  SONAME bump) that affects other packages in the repository, you MUST seek
  human guidance before proceeding with a multi-package modification.
- **Validation**: Use `sogrep` and `checkpkg` to identify the blast radius of a
  dependency change, but do not attempt a coordinated release autonomously.

### Hierarchical Policies (AGENTS.md)

- **Exception-Based Documentation**: Package-local `AGENTS.md` files are
  strictly **OPTIONAL**. They should only exist if a package requires
  specialized guidance that cannot be captured by standard Arch Linux packaging
  standards or static analysis tools.
- **Self-Healing Documentation**: All documentation in this repository is
  **SELF-HEALING**. Every agent or maintainer interacting with the codebase MUST
  verify that the documentation relevant to their task remains accurate. If an
  inconsistency, omission, or outdated instruction is discovered, it MUST be
  corrected immediately as part of the current task.
- **Strict Scope**: The file MUST be scoped entirely to exceptions relevant only
  to the package it applies to: functional limitations, non-obvious workarounds,
  edge-case patches, or environment isolation anomalies.
- **No Boilerplate**: Local files MUST NOT contain boilerplate headers, Upstream
  URLs, or Build System definitions if that data is already present or implied
  by the `PKGBUILD`.

## 3. Mandatory Verification Workflow

Before proposing or pushing a change to any package, an agent MUST perform:

1. **Sync**: Run `python scripts/sync-package.py <pkgname> <version>` to update
   hashes and changelogs.
2. **Lint**: Run `namcap PKGBUILD`.
3. **Metadata**: Run `makepkg --printsrcinfo > /dev/null` to validate metadata
   generation (`.SRCINFO` is a generated artifact per
   `docs/SRCINFO-VERSION-CONTROL-POLICY.md`, not version-controlled).
4. **Clean Build**: Verify the build in a clean environment (locally via
   `pkgctl build` or via CI trigger).
5. Security/Quality: Use `pkgctl diff` to compare against current repository
   state where applicable.

Each workflow skill (`pkg-update`, `pkg-bootstrap`, `pkg-patch-recovery`)
includes an adapted verification sequence for its task type. The canonical steps
are defined here; the skills adapt them as needed (e.g., `pkg-bootstrap` omits
`pkgctl diff` on first build, `pkg-patch-recovery` omits the sync step).

## 3.1. Pragmatic Diagnostic & Self-Correction Loop

To ensure high-fidelity results while avoiding common agent failure modes (like
"tool-tyranny" or hallucinated success), the following patterns MUST be
employed:

1. **Surgical Root Cause Analysis**: If a build or synchronization fails, the
   agent MUST NOT guess. Use `grep` or `awk` to locate the _first_ fatal error
   in the logs (e.g., `ld: error:`, `npm ERR!`, `CMake Error`) to identify the
   actual breakage before proposing a fix.
2. **Deterministic Idempotency**: All transformation logic in `update.sh` MUST
   be idempotent. Ensure that `sed` or `patch` operations produce the same state
   regardless of execution count. Never inject non-deterministic data (like raw
   `date` or `hostname`) unless gated by `SOURCE_DATE_EPOCH`.
3. **Validation vs. Package-Specific Requirements**: Treat `namcap` as a
   consultant, not a judge. Use it to catch objective errors (bad permissions,
   missing licenses), but prioritize package-specific requirements in the local
   `AGENTS.md` (if it exists) for runtime dependencies or environmental
   requirements that static analysis may misidentify as "unnecessary."
4. **Payload Sanity Check**: Before finalizing an update, perform a "sanity
   check" on the package payload using `pkgctl diff --list`. Verify that the
   primary binary, license file, and directory structure remain consistent; any
   disappearance of `/usr/bin/` targets or a payload size deviation of >10% MUST
   be investigated as a potential regression.

### Troubleshooting & Manual Intervention

If the automated pipeline fails, follow these specific recovery patterns:

- **Patch Failures**: Activate the `pkg-patch-recovery` skill for deterministic
  recovery across clone → resolve → regenerate → verify.
- **Checksum Failures**: If `updpkgsums` fails due to a re-rolled upstream
  release, verify the file content before committing the new hashes.
- **Security & GPG**: The repository uses `repo-add --sign`. For manual key
  setup:
  1. Generate an RSA 4096-bit key (no expiry).
  2. Export to armor: `gpg --export-secret-keys --armor <KEY_ID>`.
  3. Store in GitHub Secret `REPO_GPG_KEY` for the `release.yml` workflow.

## 4. Future Mandates & Technical Debt

For outstanding work items, see [`docs/TODO.md`](docs/TODO.md).
