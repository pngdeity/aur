# Automated System Architecture — Conceptual Model

**Date:** 2026-05-06
**Scope:** Automated Package Reconciliation, Identity Protection, and Publication Lifecycle.
**Version:** Implementation-agnostic. Current Bash/YAML implementation referenced in [Appendix A](#appendix-a-implementation-reference).

---

## 1. Conceptual Model

### 1.1 What the System Does

The automated maintenance system watches a collection of package build definitions for upstream changes. When a change is detected — a new software release, a modified build procedure, a shifted dependency — the system classifies the change by type, applies a per-type strategy, and either auto-integrates it or gates it for human review.

The system operates across two distinct lifecycle phases:

- **Bootstrap** — The one-time act of bringing a package into the collection. The upstream definition is ingested, local identity is stamped onto it, and the package enters monitoring.
- **Update** — The recurring act of reconciling upstream changes with local identity. Every detected change is classified and dispatched.

### 1.2 Core Abstractions

| Abstraction | Definition |
|-------------|-----------|
| **Build Definition** | The complete specification for compiling and packaging a piece of software. Contains both structured data (version, dependencies, source URLs) and imperative logic (build functions). |
| **Concern** | A semantically meaningful subdivision of a build definition. Each concern has a type, a detection rule, and a default merge strategy. |
| **Strategy** | The rule governing how the system responds to a change in a given concern. Strategies range from "ignore upstream" to "auto-adopt" to "flag for review." |
| **Event** | A typed, timestamped record of a detected upstream change. Events are the unit of work in the update pipeline. |
| **Identity** | The set of properties that make a build definition local rather than upstream: authorship, package name, variant designation, local patches. Identity is shielded from upstream changes. |
| **Cache** | The stored upstream state at the time of last sync. Used to compute what changed since then. |
| **Review Gate** | A mechanism that blocks automated publication when a change requires human judgment. |

### 1.3 System Boundaries

```
  External                         System                            External
┌──────────┐    ┌──────────────────────────────────────┐    ┌────────────────┐
│ Upstream │    │                                      │    │                │
│ sources  │───▶│  DISCOVERY → CLASSIFY → DISPOSITION  │───▶│ Published      │
│ (GitLab, │    │       │                    │         │    │ repository     │
│  AUR,    │    │       ▼                    ▼         │    │                │
│  GitHub) │    │  BOOTSTRAP              UPDATE       │    │                │
│          │    │  (first run)          (subsequent)   │    │                │
│          │    │       │                    │         │    │                │
│          │    │       └────────┬───────────┘         │    │                │
│          │    │                ▼                     │    │                │
│          │    │         VERIFY → PUBLISH              │    │                │
└──────────┘    └──────────────────────────────────────┘    └────────────────┘
```

---

## 2. Concern Taxonomy

A build definition is not a single document. It is a composition of semantically independent concerns. The system recognizes nine:

| # | Concern | Contains | Default Strategy | Rationale |
|---|---------|----------|-----------------|-----------|
| C1 | Authorship | Maintainer attribution, contributor credits | **LOCAL** | Upstream has no authority over who publishes this variant |
| C2 | Orchestration | System configuration variables (upstream tracking, demotion flags, asset triggers) | **LOCAL** | These are metadata about the system, not about the software |
| C3 | Identity | Package name, provided/conflicted/replaced packages | **LOCAL** | Variant names must not be overwritten by upstream |
| C4 | Version | Software version number, packaging revision number, version computation function | **TRACK** | The system monitors for new versions and updates them mechanically |
| C5 | Metadata | Description, homepage URL, license, architecture, backup files, install scripts | **TRACK** | Upstream refinements are usually correct and can be auto-adopted |
| C6 | Dependencies | Runtime, build-time, optional, and test dependencies | **MERGE** | New upstream dependencies should be adopted; removals should be reviewed |
| C7 | Sources | Download URLs, integrity hashes | **MERGE** | Upstream URL changes must be adopted; local additions must be preserved |
| C8 | Build Logic | Build preparation, compilation, testing, and packaging functions | **REVIEW** | Changes to build procedures can break the package and require human judgment |
| C9 | Trivia | Commentary, blank lines, editor modelines | **DISCARD** | No semantic value; noise in change detection |

### 2.1 Strategy Definitions

| Strategy | Behavior |
|----------|----------|
| **LOCAL** | Discard upstream changes. The local value always wins. |
| **TRACK** | Adopt upstream changes mechanically if the local value has not been customized. If customized, flag the discrepancy for review. |
| **MERGE** | Combine upstream changes with local additions. Upstream additions are adopted automatically. Upstream removals are flagged if they affect locally-declared items. |
| **REVIEW** | Never auto-apply. Record the change and block automated publication until a human resolves it. |
| **DISCARD** | Strip before any comparison. These elements are not part of the semantic content. |

---

## 3. Configuration Schema

The system is configured through key-value pairs embedded in the build definition. These are the system's API surface — the mechanism by which a human maintainer declares intent.

### 3.1 Identity & Authorship

| Key | Type | Effect |
|-----|------|--------|
| `_demote_upstream_maintainer` | boolean | When true, all upstream authorship claims are reduced to contributor credits. The local maintainer retains primary authorship. Applied at both bootstrap and update. |
| `_auto_merge_build` | boolean | When true, upstream changes to build logic (C8) are auto-adopted instead of gated for review. Default: false. |
| `_deploy_aur` | boolean | When true, the package is opted into AUR publication. The CI/CD pipeline processes the PKGBUILD and pushes to `aur.archlinux.org` after successful builds. Mutually exclusive with `_repo_subarch`. |

### 3.2 Upstream Tracking

| Key | Type | Effect |
|-----|------|--------|
| `_upstream_arch_repo` | string | Identifies the official Arch Linux packaging repository from which to fetch the upstream build definition. |
| `_upstream_aur_pkg` | string | Identifies the AUR package from which to fetch the upstream build definition. |

Exactly one of these must be set for a derivative package. A package with neither is considered custom (no upstream merge).

### 3.3 Asset Management

| Key | Type | Effect |
|-----|------|--------|
| `_use_common_gemini_settings` | boolean | When true, a shared asset is synchronized into the package directory during both bootstrap and update. |

### 3.4 Metadata Automation

| Key | Type | Effect |
|-----|------|--------|
| `_githubname` | string | GitHub repository identifier for automated changelog generation. |
| `_tag` | string | Tag pattern for matching upstream releases. Supports `${pkgver}` substitution. Default: `v${pkgver}`. |
| `_pkgname` | string | Canonical software name, stripped of variant suffixes. Used to generate provides/conflicts for variant packages. |

### 3.5 Variant Builds

| Key | Type | Effect |
|-----|------|--------|
| `_repo_subarch` | string | Defines the deployment sub-architecture for variant packages (e.g., `x86_64_v3`, `x86_64_v4`). Controls CFLAGS injection in the build environment and artifact routing in the release pipeline. Mutually exclusive with `_deploy_aur`. |

### 3.6 Proposed Extensions

| Key | Type | Effect |
|-----|------|--------|
| `_additional_source` | array | Local files to append to the upstream source array. |
| `_additional_depends` | array | Local additions to runtime dependencies. |
| `_additional_makedepends` | array | Local additions to build-time dependencies. |
| `_exclude_depends` | array | Upstream dependencies to exclude. |

---

## 4. Pipeline Architecture

The pipeline is a directed sequence of stages, each consuming and producing well-defined state. The pipeline branches at stage 1 based on whether the package has been previously synchronized (update path) or is being introduced for the first time (bootstrap path).

### 4.1 Stage Sequence

```
                     ┌──────────────────────────┐
                     │   STAGE 1: DETECT         │
                     │   Read upstream tracking  │
                     │   config. Fetch upstream  │
                     │   definition.              │
                     └──────────┬───────────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Cache exists?          │
                    └───┬───────────────┬───┘
                        │ YES           │ NO
                        ▼               ▼
              ┌─────────────────┐  ┌─────────────────┐
              │ STAGE 2a:       │  │ STAGE 2b:       │
              │ CLASSIFY        │  │ INGEST          │
              │ Compare cached  │  │ Save upstream   │
              │ vs new upstream │  │ as cache.       │
              │ → produce       │  │ Apply identity  │
              │   event set     │  │ rules.          │
              └────────┬────────┘  └────────┬────────┘
                       │                    │
                       ▼                    │
              ┌─────────────────┐           │
              │ STAGE 3a:       │           │
              │ RECONCILE       │           │
              │ Three-way merge │           │
              │ (local, old     │           │
              │  upstream, new  │           │
              │  upstream) with │           │
              │ identity shield │           │
              └────────┬────────┘           │
                       │                    │
                       ▼                    ▼
              ┌─────────────────────────────────────┐
              │ STAGE 4: IDENTITY                   │
              │ Apply declarative identity rules    │
              │ (demotion, asset sync).             │
              └────────────────┬────────────────────┘
                               │
                               ▼
              ┌─────────────────────────────────────┐
              │ STAGE 5: REVIEW GATE                │
              │ If build logic changed without      │
              │ opt-in, annotate definition with    │
              │ review-required marker.             │
              └────────────────┬────────────────────┘
                               │
                               ▼
              ┌─────────────────────────────────────┐
              │ STAGE 6: VERSION                    │
              │ Update version number and revision. │
              │ Reset revision on software change;  │
              │ increment on packaging change.      │
              └────────────────┬────────────────────┘
                               │
                               ▼
              ┌─────────────────────────────────────┐
              │ STAGE 7: CUSTOM TRANSFORMATION      │
              │ Execute imperative package-specific │
              │ transformation hook if present.     │
              │ Preconditions: definition finalized, │
              │ all assets present.                 │
              └────────────────┬────────────────────┘
                               │
                               ▼
              ┌─────────────────────────────────────┐
              │ STAGE 8: METADATA                   │
              │ Generate changelog, recompute       │
              │ integrity hashes, export metadata.  │
              └─────────────────────────────────────┘
```

### 4.2 Bootstrap Path (First Synchronization)

**Preconditions:** No upstream cache exists.

**Behavior:**
1. Fetch the upstream build definition.
2. Download any auxiliary assets referenced by upstream (patches, install scripts, configuration files).
3. Save the upstream definition as the cache baseline.
4. Apply declarative identity rules to the local definition (authorship demotion, asset synchronization).
5. Bump the packaging revision.
6. Generate changelog, hashes, and metadata export.

**Result:** The package enters the monitoring state with a valid cache for future comparison.

### 4.3 Update Path (Subsequent Synchronizations)

**Preconditions:** Upstream cache exists. Build definition has upstream tracking configuration.

**Behavior:**
1. Fetch the new upstream build definition.
2. Compute the difference between the cached upstream state and the new upstream state.
3. If unchanged: terminate (no work to do).
4. Classify each detected difference into one or more concern types.
5. Download new upstream assets.
6. Shield local identity properties from the merge.
7. Reconcile the local definition, the cached upstream definition, and the new upstream definition via a three-way merge.
8. Restore shielded identity properties.
9. Apply declarative identity rules (post-merge demotion).
10. If build logic changed without opt-in, inject a review-required annotation.
11. Update the cache to the new upstream state.
12. Update version numbering.
13. Execute source transformation hook (if present).
14. Generate changelog, hashes, and metadata export.

**Result:** The build definition is reconciled with upstream. Any review-required changes are annotated and gated from automated publication.

### 4.4 Identity Shielding

During the three-way reconciliation, a subset of the local build definition is temporarily extracted and held aside (shielded) to preserve the variant's personality. These properties are restored after reconciliation:

- **Artifact Identifier** (`pkgname`)
- **Semantic Version** (`pkgver`)
- **Revision Index** (`pkgrel`)
- **Compatibility Interface** (`provides`, `conflicts`, `replaces`)
- **Asset Manifest** (`source`)
- **Version Computation Logic** (`pkgver()` function)

These properties are restored after reconciliation, ensuring the variant identity survives any upstream changes to those fields. All other properties — dependencies, build functions, metadata — flow through the merge unshielded and may be modified.

---

## 5. Change Classification

### 5.1 Detection

A structural comparison of the cached upstream definition against the newly fetched upstream definition identifies every difference.

### 5.2 Typing

Each difference is matched against a concern-specific pattern:

| Concern | Detection Signal |
|---------|-----------------|
| AUTHORSHIP | Maintainer or Contributor attribution lines differ |
| IDENTITY | Package name, provides, conflicts, or replaces fields differ |
| VERSION | Version number, revision number, or version computation function differs |
| METADATA | Description, URL, license, architecture, backup, install script, or build options differ |
| DEPENDS | Runtime dependency list differs |
| MAKEDEPENDS | Build-time dependency list differs |
| CHECKDEPENDS | Test dependency list differs |
| OPTDEPENDS | Optional dependency list differs |
| SOURCES | Source URLs or integrity hash arrays differ |
| BUILD | Build preparation, compilation, testing, or packaging functions differ |

### 5.3 Event Production

Detected and typed changes produce an event set. Each event carries:
- The concern type
- The default strategy for that concern
- A human-readable description of what changed

The event set is consumed by downstream stages to determine which strategies to apply and whether to activate the review gate.

---

## 6. Review Gate

### 6.1 Trigger

The review gate activates when C8 (Build Logic) changes are detected and the package has not opted into automatic adoption of build changes via `_auto_merge_build=true`.

### 6.2 Mechanism

When activated, the system injects a structured annotation into the build definition:

```
Review-required: build logic changed (target version)
Action: review the diff, verify the build, remove this annotation to unblock publication.
```

The annotation is a marker — it has no effect on the build process itself, but is readable by downstream automation.

### 6.3 CI Integration

The continuous integration pipeline interrogates build definitions for review-required annotations before publication:

1. **Discovery phase**: After synchronizing all updated packages, packages carrying annotations are excluded from the publication batch. A diagnostic is emitted listing blocked packages.
2. **Build phase**: As a safety net, annotations are detected and warned on before build execution.
3. **Publication phase**: Only unblocked packages reach the build stage.

### 6.4 Resolution

To resolve a review gate:
1. A human reviews the upstream changes (diff available via the cache history).
2. The build is verified in an isolated environment.
3. The annotation is removed from the build definition.
4. The removal is committed. The next discovery cycle processes the package normally.

---

## 7. Imperative Transformation Hook

### 7.1 Purpose

A per-package executable hook for transformations that cannot be expressed declaratively.

### 7.2 Contract

**Preconditions** (guaranteed by the pipeline before invocation):
- The build definition is finalized — all reconciliations, identity rules, and version updates are complete.
- All source files and assets are present in the package directory.
- The target version is available.

**Postconditions** (the hook's responsibility):
- The hook must be idempotent — running it multiple times on the same state produces the same result.
- The hook must not modify build definition metadata (version, dependencies, authorship, source URLs).
- The hook may modify source files (regenerating patches, updating configuration, extracting content).

**Input:** The target version as a single argument.

### 7.3 When to Use

The hook exists only for genuinely unique per-package operations. Common operations are handled declaratively:

| Task | Mechanism |
|------|-----------|
| Authorship management | `_demote_upstream_maintainer` configuration key |
| Shared asset synchronization | `_use_common_gemini_settings` configuration key |
| Source-code patches | Standard `source[]` array (preserved by identity shielding) |
| Dynamic patch generation from upstream source | Source transformation hook |
| Dynamic content extraction from external tools | Source transformation hook |

---

## 8. Cache Model

### 8.1 Storage

The upstream state at the time of last successful synchronization is persisted as a cache entry within the package directory. The cache contains:
- The full upstream build definition (for structural comparison).
- Implicitly: a timestamp (the file modification time of the cache entry).

### 8.2 Invalidation

The cache is invalidated when the newly fetched upstream definition differs from the cached version. After successful reconciliation, the cache is updated to the new upstream state.

### 8.3 Lifecycle

- **Created** during bootstrap (first synchronization).
- **Updated** on every successful update synchronization.
- **Compared** on every update synchronization to detect changes.
- **Never deleted** automatically. Package decommissioning (not yet automated) would remove the cache alongside the package directory.

---

## 9. CI Integration Model

### 9.1 Discovery

- **Schedule**: Periodic.
- **Action**: Poll all tracked upstream sources for version changes.
- **Response**: For each change, invoke the synchronization pipeline. After all synchronizations complete, filter the changed set through the review gate and initiate publication for unblocked packages.

### 9.2 Build

- **Trigger**: Invoked by the publication stage with a batch of package paths.
- **Environment**: Isolated, hermetic build environment.
- **Action**: Validate metadata, check for review annotations (safety net), compile and package each definition, upload artifacts.

### 9.3 Publication

- **Trigger**: Invoked by discovery when unblocked updates exist.
- **Binary Publication**: Collect all build artifacts, prune expired packages from the repository, add new packages, regenerate and sign the repository database, synchronize to the distribution host.
- **AUR Publication**: Runs in parallel with binary publication, gated on build success. For each package with `_deploy_aur=true`, invokes `scripts/aur-deploy.sh` to process the PKGBUILD into AUR-compatible output (inlines `source` directives, strips repo-local variables and markers, generates `.SRCINFO`) and pushes to `aur.archlinux.org`. Requires `AUR_SSH_PRIVATE_KEY` GitHub Secret.

### 9.4 CI States

```
┌──────────┐     upstream change detected     ┌──────────────┐
│  IDLE    │──────────────────────────────────▶│  SYNCING     │
└──────────┘                                   └──────┬───────┘
                                                      │
                                        ┌─────────────┼─────────────┐
                                        │ build logic  │ no build    │
                                        │ changed      │ logic change│
                                        ▼              ▼             │
                               ┌──────────────┐ ┌──────────────┐    │
                               │  REVIEW      │ │  BUILDING    │◀───┘
                               │  (blocked)   │ └──────┬───────┘
                               └──────┬───────┘        │
                                      │                 ▼
                                      │ human    ┌──────────────┐
                                      │ resolves │  PUBLISHING  │
                                      │          └──────┬───────┘
                                      ▼                 │
                               ┌──────────────┐         │
                               │  BUILDING    │◀────────┘
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │  IDLE        │
                               └──────────────┘
```

---

## 10. Design Principles

1. **Declarative over imperative** — Configuration is expressed as typed key-value pairs. Imperative hooks (`update.sh`) exist only for operations that cannot be expressed declaratively.

2. **Bootstrap and update are distinct phases** — The first synchronization ingests and stamps identity. Subsequent synchronizations detect, classify, and reconcile. The two paths share infrastructure but have different preconditions and responsibilities.

3. **Every change is classified** — The system never silently accepts an upstream change. Every difference is typed and dispatched according to a per-concern strategy. Unknown or unclassifiable changes default to review-required.

4. **Build logic is sacred** — Changes to build procedures are never auto-adopted without explicit opt-in. This is the boundary between mechanical automation and human judgment.

5. **Automation must never publish unreviewed changes** — The review gate is not advisory. It blocks the publication pipeline. A human must explicitly resolve the gate.

6. **The synchronization pipeline is the single entry point** — Bootstrap, update, CI-driven, and manual operations all enter through the same pipeline. There is no back door.

7. **Oblivious Build standard** — A build definition MUST be "oblivious" to the internet at build-time. No network calls (curl, wget) are permitted within build functions. All data fetching MUST be offloaded to the pre-build synchronization phase.

---

## Appendix A: Implementation Reference

The current implementation is in Bash and GitHub Actions YAML:

| Conceptual Component | Implementation |
|---------------------|---------------|
| Synchronization pipeline | `scripts/sync-package.sh` |
| Configuration schema | `_`-prefixed variables in `PKGBUILD` (see `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md`) |
| Upstream cache | `.PKGBUILD.upstream` file in package directory |
| Identity shielding | `snapshot_identity()` / `restore_identity()` in `sync-package.sh` |
| Change classification | `classify_upstream_changes()` in `sync-package.sh` (uses `diff(1)` + regex) |
| Review gate annotation | `apply_prereview_marker()` in `sync-package.sh` (uses `awk` injection) |
| Source transformation hook | `./update.sh` in package directory |
| Discovery CI | `.github/workflows/discovery.yml` |
| Build CI | `.github/workflows/build.yml` |
| Publication CI | `.github/workflows/release.yml` |
| AUR processing | `scripts/aur-deploy.sh` |
| Signing, database management, metrics | Manual or scripted as needed |
| Bootstrap workflow | `.agents/skills/pkg-bootstrap/SKILL.md` |
| Update workflow | `.agents/skills/pkg-update/SKILL.md` |
| Architecture documentation | `docs/AUTOMATED-SYSTEM-ARCHITECTURE.md` |
| Configuration reference | `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` |

For implementation-coupled architectural detail, see [AUTOMATED-SYSTEM-DESIGN-IMPLEMENTATION.md](AUTOMATED-SYSTEM-DESIGN-IMPLEMENTATION.md).
