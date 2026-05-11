# KCL + OPA Shift-Left Validation Layer — Implementation Plan

**Date:** 2026-05-11
**Status:** Proposed
**Handoff Reference:** `handoffs/manifest-refactor-review-response.md`
**Phase 1 Detail:** [`docs/KCL-OPA-PHASE1-SCHEMA-DESIGN.md`](KCL-OPA-PHASE1-SCHEMA-DESIGN.md)

---

## 0. Executive Summary

This plan implements the revised `manifest-refactor-review-response.md` proposal: a KCL typed schema for `PKGBUILD(5)` metadata + OPA/Rego policy engine + Python renderer, operating as a **pre-commit and pre-build validation gate**.

**Non-negotiable boundaries:**
- Does not replace `makepkg`, `sync-package.sh`, `aur-deploy.sh`, the Docker builder, or GPG signing workflows.
- Does not modify the existing 4-workflow CI/CD pipeline topology — it adds validation gates upstream of the existing build step.
- The `AGENTS.md` package-local `AGENTS.md` convention remains orthogonal (not modeled in the schema).

**Scope decision deferred**: Whether KCL eventually becomes the canonical authoring format (replacing hand-authored PKGBUILDs) is deferred to a post-Phase-3 decision gate. Phase 1–3 treat KCL as a validation-only layer. Phase 4 is a pilot conversion and requires a separate go/no-go decision.

---

## 1. Technology Viability Assessment

| Technology | In Arch Repos? | In Builder Image? | Viability |
|-----------|----------------|-------------------|-----------|
| **KCL** | No | No | Static binary from GitHub releases; installed in a lightweight CI validation job (not the builder container) |
| **Conftest (OPA)** | No | No | Same — static binary from GitHub releases |
| **Python 3** | Yes (`python`) | Yes (from `base-devel`) | No blockers |

**CI infrastructure decision**: Validation runs in `ubuntu-latest` (GitHub-hosted runner) with KCL + Conftest downloaded on-demand. The existing `arch-builder` Docker container is **not** modified. This keeps the builder image lean and avoids maintaining KCL/Conftest version pins in the Dockerfile.

---

## 2. Architecture

```
PKGBUILD (existing, hand-authored)
    │
    ▼
┌──────────────────────────────────┐
│  scripts/pkgbuild_to_kcl.py      │   Phase 1 — Import PKGBUILD → KCL model
│  (deprecated once package.k      │   Temporary scaffolding; removed when
│   files are authored manually)   │   all packages have native package.k
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  schemas/arch_pkg.k              │   Phase 1 — KCL schema (100% PKGBUILD(5))
│  packages/<name>/package.k       │   Phase 4+ — per-package KCL data files
└──────────────┬───────────────────┘
               │
               ├──▶ kcl run → manifest.json
               │
               ▼
┌──────────────────────────────────┐
│  conftest test manifest.json     │   Phase 2 — OPA policy enforcement
│  policies/repository.rego        │   https, no-sudo, provides/conflicts,
│                                  │   pkgdesc consistency, etc.
└──────────────┬───────────────────┘
               │  pass
               ▼
┌──────────────────────────────────┐
│  scripts/kcl_to_pkgbuild.py      │   Phase 3 — Render PKGBUILD from JSON
│  (round-trip parity required)    │   Acceptance: diff-identical to source
└──────────────┬───────────────────┘
               │
               ▼
           PKGBUILD (rendered)
               │
               ▼
  Existing build pipeline (makepkg → pkgctl build → aur-deploy)
```

**Phase 1–3**: Validation runs as a parallel check. The hand-authored PKGBUILD remains the source of truth. The renderer proves round-trip equivalence but does not replace the committed PKGBUILD.

**Phase 4 (deferred decision)**: The rendered PKGBUILD replaces the hand-authored one as the build input. The `package.k` file becomes the canonical authoring format.

---

## 3. Phase 1: KCL Schema — Estimated 3–4 days

**Goal**: A KCL schema covering 100% of `PKGBUILD(5)` surface area + 13 custom `_`-prefixed variables, plus an import script to bootstrap the model from existing PKGBUILDs.

**Deliverables**:
- `schemas/arch_pkg.k` — complete KCL schema
- `scripts/pkgbuild_to_kcl.py` — PKGBUILD → KCL import utility
- `scripts/validate-pkgbuilds.sh` — orchestration wrapper (import → `kcl run` → `conftest test`)

**Detailed design**: [`docs/KCL-OPA-PHASE1-SCHEMA-DESIGN.md`](KCL-OPA-PHASE1-SCHEMA-DESIGN.md)

---

## 4. Phase 2: OPA Policy Engine — Estimated 2–3 days

**Goal**: A Rego ruleset that programmatically audits KCL-generated JSON before any build is attempted.

### 4.1 Policy Rules (12 rules)

Sources: Handoff §3.B/C, AGENTS.md variant conventions, TODO §62.

| # | Rule Name | Trigger | Severity | Source |
|---|-----------|---------|----------|--------|
| 1 | `enforce_https` | Any `source[].url` starting with `http://` | ERROR | Handoff |
| 2 | `privilege_escalation` | String `sudo` in any lifecycle function or `.install` file | ERROR | Handoff |
| 3 | `architecture_mismatch` | Architecture-specific flags on `arch=(any)` packages | WARN | Adapted from handoff "headless" rule |
| 4 | `no_unprovided_conflicts` | Entry in `conflicts` or `replaces` not also in `provides` | ERROR | AGENTS.md |
| 5 | `no_self_reference` | `pkgname` appearing in its own `provides` or `conflicts` | ERROR | AGENTS.md |
| 6 | `deploy_aur_subarch_mutex` | `_deploy_aur=true` AND `_repo_subarch` set simultaneously | ERROR | AGENTS.md |
| 7 | `pkgdesc_consistency` | Packages sharing `_pkgname` have differing `pkgdesc` | ERROR | AGENTS.md |
| 8 | `valid_architectures` | `arch` contains unknown values | ERROR | `PKGBUILD(5)` |
| 9 | `required_fields` | Missing `pkgname`, `pkgver`, `pkgrel`, `pkgdesc`, `arch`, `url`, `license` | ERROR | `PKGBUILD(5)` |
| 10 | `source_integrity` | `sha*sums` length != `source` length (excluding SKIP entries) | ERROR | `PKGBUILD(5)` |
| 11 | `vcs_skip` | Non-VCS source has `SKIP` checksum | WARN | VCS guidelines |
| 12 | `maintainer_present` | `# Maintainer:` header pattern not found | WARN | Repo convention |

### 4.2 Policy Exception Mechanism

Package-level exceptions via `packages/<name>/policy_exceptions.yaml`:

```yaml
exceptions:
  - rule: enforce_https
    reason: "Upstream does not publish tarballs over HTTPS (pinned by sha256sum)"
  - rule: vcs_skip
    reason: "Binary package — no VCS sources to checksum"
```

The `validate-pkgbuilds.sh` wrapper passes these through to `conftest` as `--data` flags or merges them into a combined input.

### 4.3 Relationship to Existing Validators

| Existing Validator | Replaced By | Notes |
|--------------------|------------|-------|
| `scripts/check-metadata.sh` | Rules 9, 10 | `.SRCINFO` diff check is orthogonal — keep as-is |
| `scripts/check-pkgdesc-consistency.sh` | Rule 7 | Keep as pre-commit hook until OPA matures; then retire |
| TODO §62 "Quality Rules Engine" | Rules 4, 5, 7 | Fully superseded |

### 4.4 Deliverables
- `policies/repository.rego` — policy ruleset
- `packages/<name>/policy_exceptions.yaml` — per-package exceptions (empty initially)
- Updated `scripts/validate-pkgbuilds.sh` — invoke `conftest test`

---

## 5. Phase 3: Renderer + CI Injection — Estimated 3–4 days

**Goal**: A Python renderer that converts validated KCL JSON back into syntactically valid `PKGBUILD(5)` text, plus CI integration at all three insertion points.

### 5.1 PKGBUILD Renderer (`scripts/kcl_to_pkgbuild.py`)

Converts validated KCL JSON into syntactically correct `PKGBUILD(5)` text:

- Outputs `# Maintainer:` header line
- Emits variables in standard order: `pkgname`, `pkgver`, `pkgrel`, `pkgdesc`, `arch`, `url`, `license`, `depends`, `makedepends`, `checkdepends`, `optdepends`, `provides`, `conflicts`, `replaces`, `backup`, `install`, `changelog`, `source`, checksums, `validpgpkeys`, `noextract`, `options`, functions
- Handles Bash array syntax: `depends=('foo' 'bar')`
- Handles VCS source fragments (`git+https://...#tag=`, `#commit=`) intact
- Handles multi-line function bodies with correct indentation
- Preserves blank line separation between sections
- Emits custom `_`-prefixed variables in their original order
- **Round-trip acceptance criterion**: `PKGBUILD → kcl → JSON → render → PKGBUILD2` must produce output that, when diffed against the original, shows no functional differences. Byte-level differences (comment whitespace, blank line count) are acceptable. The rendered PKGBUILD must build correctly in the Docker container.

### 5.2 Pre-Commit Hook

Addition to `.pre-commit-config.yaml` — a new `local` hook entry alongside the existing `check-pkgdesc-consistency`:

```yaml
- id: kcl-validate
  name: KCL Schema + OPA Policy Validation
  entry: bash scripts/validate-pkgbuilds.sh
  language: system
  files: ^packages/.*/(PKGBUILD|package\.k)$
  pass_filenames: false
```

### 5.3 CI Injection: `build.yml`

A new `validate` job runs **before** the existing `execute` job, in `ubuntu-latest` (not the builder container):

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Install KCL + Conftest
        run: |
          curl -sSL <pinned kcl release URL> | tar xz
          curl -sSL <pinned conftest release URL> | tar xz
          sudo mv kcl conftest /usr/local/bin/
      - name: Run Validation
        run: ./scripts/validate-pkgbuilds.sh

  execute:
    needs: validate
    runs-on: ubuntu-latest
    container: ghcr.io/${{ github.repository }}/arch-builder:latest
    # ... existing steps unchanged ...
```

The `needs: validate` gate prevents the builder from starting until validation passes.

### 5.4 CI Injection: `discovery.yml`

Inserted after the `check-pkgdesc-consistency.sh` gate (after line 60) and before the `git commit`/`git push` block (line 93). Failure blocks the push:

```yaml
if ! bash scripts/validate-pkgbuilds.sh; then
  echo "::error::Aborting discovery pipeline — KCL/OPA validation failures."
  exit 1
fi
```

### 5.5 Deliverables
- `scripts/kcl_to_pkgbuild.py` — renderer
- `scripts/validate-pkgbuilds.sh` — updated orchestration wrapper
- Updated `.pre-commit-config.yaml`
- Updated `.github/workflows/build.yml`
- Updated `.github/workflows/discovery.yml`

---

## 6. Phase 4: Pilot Migration — Estimated 2–3 days

**Prerequisite**: Post-Phase-3 go/no-go decision. Phase 4 is not committed until then.

### 6.1 Pilot Selection

**Recommended**: `opendoas` (68 lines, moderate complexity).

Rationale: Exercises patching, C build, `.install` scriptlet, VCS source with `#tag=`, provides/conflicts/replaces, custom `backup` field, `validpgpkeys`, and `sha256sums` — without the dynamic version computation or npm/bun complexity. If `opendoas` succeeds, a second pilot on `opencode-git` (the most complex: bun build, architecture branching, `_target_arch()` helper, multi-source, `pkgver()`, skipped checksums, completions generation) validates the schema under stress.

### 6.2 Pilot Steps
1. Manually author `packages/opendoas/package.k` (without the import script — validates schema authoring ergonomics).
2. `kcl run packages/opendoas/package.k` → `manifest.json`.
3. `conftest test manifest.json` — resolve any policy findings.
4. `python scripts/kcl_to_pkgbuild.py manifest.json > /tmp/PKGBUILD.rendered`.
5. `diff /tmp/PKGBUILD.rendered packages/opendoas/PKGBUILD` — verify functional equivalence.
6. If diff is clean: commit `package.k`, archive original PKGBUILD as `PKGBUILD.manual`, and wire the render pipeline to produce the PKGBUILD at build time.
7. Build through Docker container: `pkgctl build` verifies the rendered PKGBUILD produces the expected binary.
8. Run through 2 full CI cycles before declaring the pilot successful.

### 6.3 Deliverables
- `packages/opendoas/package.k` — first native KCL package file
- `packages/opendoas/PKGBUILD.manual` — archived original
- Diff report confirming round-trip parity
- Schema amendments from pilot findings

---

## 7. Dependency & Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | KCL schema can't express dynamic `${var}` interpolation (e.g., `source=("git+${url}.git")`) | Medium | High | Schema stores source URLs as raw strings; structural validation occurs at the URL pattern level, not the `${var}` expansion level |
| R2 | Round-trip PKGBUILD → KCL → PKGBUILD not functionally identical | Medium | High | Acceptance criterion is functional equivalence (builds correctly), not byte identity. Diff test against all 6 existing PKGBUILDs |
| R3 | KCL/Conftest binary download flaky in CI (GitHub rate limits, release deletion) | Medium | Medium | Pin versions in `scripts/install-validator-tools.sh`; cache in GitHub Actions cache; fall back to vendored binaries in `scripts/bin/` |
| R4 | Team unfamiliar with KCL/Rego syntax inhibits adoption | High | Medium | Phase 1–3 auto-convert existing PKGBUILDs via import script; manual `.k` authoring only required if Phase 4 proceeds |
| R5 | `sync-package.sh` cannot process KCL-as-truth packages in Phase 4 | High (Phase 4 only) | Critical (Phase 4 only) | Phase 4 gate condition: do not proceed until `sync-package.sh` either works with rendered PKGBUILDs or has a KCL-aware adapter |
| R6 | Validation step adds CI latency | Low | Low | KCL compiles ~1s per package; Conftest evaluates ~1s total. Overhead <10s for 6 packages |

---

## 8. Relationship to Existing TODO Items

| TODO § | Title | Relationship |
|--------|-------|-------------|
| §62 | PKGBUILD Quality Rules Engine | **Superseded**. KCL + OPA is a more structured implementation. The Bash DSL approach in §62 is obsoleted by this plan. `pkgvar` array support becomes unnecessary — OPA validates against the KCL model directly. |
| §58 | Broader pkgvar adoption | **Partially superseded**. The 5 remaining grep extraction points in `sync-package.sh` and `aur-deploy.sh` are orthogonal — they handle upstream merge operations, not validation. If Phase 4 proceeds, these will eventually read from KCL manifests instead of grepping PKGBUILDs. |
| "Dev Branch" | CI Dry-Run Pipeline | The new `validate` job in `build.yml` is separable — can be tested in `dev` before `main`. |

---

## 9. Migration Decision Gate (Post-Phase 3)

Phase 3 delivers a working validation layer that runs alongside the existing pipeline without changing any PKGBUILDs. Phase 4 changes the source-of-truth format from PKGBUILD to KCL.

Decision to be made after Phase 3 verification:

| Criterion | Option A (Stop) | Option B (Proceed to Phase 4) |
|-----------|-----------------|-------------------------------|
| **What changes** | Nothing. PKGBUILDs remain hand-authored. | `package.k` becomes canonical. PKGBUILD becomes a build artifact. |
| **Value delivered** | 80% (typed validation + policy enforcement) | 100% (full format migration + validation) |
| **Risk** | Zero (validation is advisory) | Medium (format migration touches all packages and scripts) |
| **Maintenance burden** | KCL, Conftest, Python renderer | Same, plus ongoing renderer compatibility with `PKGBUILD(5)` evolution |
| **Author workflow** | Unchanged — edit PKGBUILD, commit PKGBUILD | Changed — edit `package.k`, PKGBUILD generated at build time |

Decision deferred per project guidance.

---

## 10. Timeline

| Phase | Estimated Effort | Cumulative |
|-------|-----------------|------------|
| Phase 1 (Schema + Import) | 3–4 days | 3–4 days |
| Phase 2 (Policy Engine) | 2–3 days | 5–7 days |
| Phase 3 (Renderer + CI) | 3–4 days | 8–11 days |
| Phase 4 (Pilot) | 2–3 days | 10–14 days |
| **Total** | **10–14 days** | |

Assumes one engineer working sequentially. Phases 1 and 2 could overlap if done in parallel (schema design + policy authoring are independent once the schema stabilizes).
