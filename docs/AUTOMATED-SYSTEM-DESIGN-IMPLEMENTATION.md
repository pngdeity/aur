# Automated System Architecture — Implementation Design

**Date:** 2026-05-06
**Status:** Implemented (commit `dc714e2`)
**Reference:** [Conceptual Architecture](AUTOMATED-SYSTEM-ARCHITECTURE.md)

This document provides the technical design and implementation details for the Automated Maintenance System. It maps the conceptual lifecycle stages to specific Bash scripts, regular expressions, and CI/CD workflows.

---

## 1. Technology Stack

- **Orchestration:** GitHub Actions (YAML)
- **Engine:** Bash (4.0+)
- **Discovery:** `nvchecker`, `nvtake`
- **Logic Parsing:** `grep`, `sed`, `awk`, `diff`, `jq`
- **Reconciliation:** `git merge-file` (Standard 3-way merge)
- **Asset Handling:** `curl`
- **Verification:** `makepkg`, `namcap`, `pkgctl` (devtools)

---

## 2. Engine Implementation (`scripts/sync-package.sh`)

The core engine is a single Bash script that implements the reconciliation pipeline.

### 2.1 Identity Shielding (`snapshot_identity` / `restore_identity`)

To protect the local variant's "personality" during reconciliation, the script uses a snapshot-and-restore pattern.

**Snapshot Logic:**
```bash
snapshot_identity() {
    grep -E '^(pkgname|pkgver|pkgrel|provides|conflicts|replaces|source)=' PKGBUILD > .identity.tmp
    if grep -q "^pkgver()" PKGBUILD; then
        sed -n '/^pkgver()/,/^}/p' PKGBUILD > .pkgver_func.tmp
    fi
}
```

**Restoration Logic:**
Uses `sed` to replace merged variables with their original local values and re-injects the `pkgver()` function if it was shielded.

### 2.2 Change Classification (`classify_upstream_changes`)

The classifier uses `diff` between the old cached upstream (`.PKGBUILD.upstream`) and the new upstream to identify changes. Concern types are identified via regular expressions:

| Concern | Regex Pattern |
|---------|---------------|
| AUTHORSHIP | `^[<>].*# (Maintainer\|Contributor):` |
| IDENTITY | `^[<>].*(pkgname=\|provides=\|conflicts=\|replaces=)` |
| VERSION | `^[<>].*(pkgver=\|pkgrel=\|^pkgver\(\))` |
| METADATA | `^[<>].*(pkgdesc=\|url=\|license=\|arch=\|backup=\|install=\|options=)` |
| DEPENDS | `^[<>].*depends=` (includes make/check/opt variants) |
| SOURCES | `^[<>].*(source=\|sha256sums=\|sha512sums=\|b2sums=)` |
| BUILD | `^[<>].*(prepare\(\)\|build\(\)\|check\(\)\|package\(\))` |

### 2.3 PREREVIEW Marker (`apply_prereview_marker`)

When a change to **Build Logic** is detected, an `awk` script injects a comment after the maintainer header:

```bash
awk '/^# Maintainer:/ { print; print "# PREREVIEW: upstream build functions changed"; ... next } 1' PKGBUILD
```

---

## 3. Configuration Implementation

System directives are implemented as `_`-prefixed variables in the `PKGBUILD`.

| Variable | Implementation Detail |
|----------|-----------------------|
| `_upstream_arch_repo` | Triggers GitLab fetch from `gitlab.archlinux.org`. |
| `_upstream_aur_pkg` | Triggers AUR fetch from `aur.archlinux.org`. |
| `_demote_upstream_maintainer` | Triggers `sed '2,$ s/^# Maintainer:/# Contributor:/g'`. |
| `_use_common_gemini_settings` | Triggers `cp common/gemini-cli-settings.json settings.json`. |
| `_githubname` | Used as input for `scripts/generate-changelog.sh`. |

---

## 4. CI/CD Pipeline Implementation

### 4.1 Discovery Workflow (`discovery.yml`)

1.  **Consolidation:** Aggregates all `.nvchecker.toml` files into a single `master.toml`.
2.  **Execution:** Runs `nvchecker --logger json`.
3.  **Sync:** For each `updated` event, invokes `bash scripts/sync-package.sh <name> <version>`.
4.  **Filter:** Uses `grep` to scan for `# PREREVIEW:` markers.
5.  **Dispatch:** Updates `oldver.json`, commits, and triggers `release.yml` for unblocked packages.

### 4.2 Build Workflow (`build.yml`)

Runs inside a specialized Docker container (`ghcr.io/.../arch-builder`) and executes `scripts/arch-builder.sh`, which uses `makepkg --clean --syncdeps` inside a fresh container per job for dependency-resolved building. For strict clean-chroot verification (locally), use `pkgctl build` — see AGENTS.md §3.

### 4.3 Release Workflow (`release.yml`)

1.  **Binary pipeline** (`publish` job): Downloads artifacts from `build.yml`, prunes packages older than 7 days, runs `repo-add --sign` to regenerate the repository database, and uses `rsync` to synchronize to the distribution host.
2.  **AUR pipeline** (`deploy-aur` job): Runs in parallel with `publish`, gated on build success (`needs: run-builds`). For each package with `_deploy_aur=true`, invokes `scripts/aur-deploy.sh` to process the repo PKGBUILD into AUR-compatible output and pushes it to `aur.archlinux.org`. Requires `AUR_SSH_PRIVATE_KEY` GitHub Secret.

---

## 5. File System Data Model

```
packages/<name>/
  ├── PKGBUILD               # Source of Truth (Local)
  ├── .PKGBUILD.upstream     # Cache Baseline (Last known upstream)
  ├── .SRCINFO               # Generated Metadata
  ├── .nvchecker.toml        # Discovery Config
  ├── update.sh              # Optional Transformation Hook
  └── [Assets]               # Patches, install scripts, local configs
```

---

## 6. Implementation Principles

1.  **Single Entry Point:** All synchronization logic (Bootstrap and Update) is contained within `scripts/sync-package.sh` to ensure consistency between manual and CI-driven runs.
2.  **Metadata Isolation:** The system treats the `PKGBUILD` as a data structure, using targeted `sed` and `grep` operations to modify specific fields without disturbing unrelated content.
3.  **Safety First:** The discovery workflow is designed to fail-safe; if a reconciliation is ambiguous or logic changes, the package is blocked from release until a human intervenes.
