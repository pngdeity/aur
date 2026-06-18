# Project TODO

Outstanding architectural and documentation items requiring completion.

## Architecture

- [ ] **Package Decommissioning SOP**: Define a standard process for removing
      packages from the repository, including AUR dropping and discovery
      cleanup. (Due: Indeterminate)
- [ ] **Edge-Case Recovery Logic**: Define deterministic recovery paths for
      hybrid merge failures and 404 upstream assets. (Due: After `sync-package.py`
      port — the last remaining script in the refactor)
- [ ] **Evaluate makepkg-optimize relevance**: Assess whether `makepkg-optimize`
      should be integrated into the build pipeline. Evaluate its compiler flag
      overrides against `makepkg.conf(5)` defaults, its impact on reproducible
      builds (`SOURCE_DATE_EPOCH`), and whether it provides meaningful
      performance or security gains for this repository's package set.

## Agent Skills

- [ ] **Skill Description Trigger Validation**: The three Agent Skills
      (`pkg-update`, `pkg-bootstrap`, `pkg-patch-recovery`) have untested
      `description` fields. Per the
      [agentskills.io optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
      guide: design 20 trigger eval queries per skill (should-trigger and
      should-not-trigger, including near-misses), run each query 3+ times
      against the agent router, and compute trigger rates. Use train/validation
      splits to avoid overfitting. Before implementation, research the state of
      the art — existing automated eval frameworks for skill description
      testing, prior work from
      [agentskills/skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator),
      and any trigger-testing tooling that has emerged since the spec was
      published.

## Engineering (CI/CD)

- [ ] **Local Repository for Circular Dependencies**: The original
      `arch-builder.py` and `build.yml` had placeholder logic for a
      `/tmp/local-repo` pacman repository to resolve inter-package circular
      dependencies within the monorepo. This was removed because an empty
      file:// repo with no database causes pacman v7.1.0 to fail
      (`error: could not find database`). When circular dependencies arise
      (e.g., package A depends on package B and vice versa), implement this
      properly:
  1. Create a valid pacman database in `/tmp/local-repo` using `repo-add` after
     each build publishes a `.pkg.tar.zst` there.
  2. Add `[local-nightly]` to `pacman.conf` in the `build.yml` Bootstrap step
     (already runs as root) — but only after at least one package is in the
     repo.
  3. Update `arch-builder.py` to publish built packages to the local repo before
     moving them to `dist/`. (Due: When the first package pair with mutual
     dependencies is added to the monorepo)

- [ ] **Binary Publish Prerequisites**: The `release.yml` publish job (lines
      27-103) requires infrastructure and secrets that are not yet provisioned.
      Until resolved, the job will fail harmlessly (AUR deploy runs
      independently), but no binary packages will reach the nightly repository.
  1. **Provision Apache host** — the target for `rsync` at `release.yml:103`
     (`/var/www/html/repo/nightly/`). The job pulls the existing repo at line 68
     and pushes at line 103 — both need a live host.
  2. **Configure GitHub Secrets**:
     - `REPO_HOST` — Apache server hostname
     - `REPO_USER` — SSH user with write access to the Apache docroot
     - `REPO_SSH_PRIVATE_KEY` — SSH key for rsync transport
     - `REPO_GPG_KEY` — GPG private key for `repo-add --sign` at
       `release.yml:88`
  3. **Validate connectivity** — after secrets are set, manually trigger
     `discovery.yml` (it will find no updates, skip the build, and not reach
     publish) or test the publish job in isolation. (Due: Before declaring the
     CI/CD pipeline operational for binary artifact delivery)

- [x] **Dev Branch with CI Dry-Run Pipeline** (partially complete —
      infrastructure in place, stabilization pending): `origin/dev` branch
      created from main (2026-05-15 swarm, S9.2). Discovery workflow dispatched
      on `dev` (S9.3). Remaining work:
  1. ~~**Create `dev` branch**~~: Done — `origin/dev` exists at same SHA as
     `main` (08f7faf).
  2. **Dry-run pipeline mechanics**: (pending) Extend `release.yml` and
     `build.yml` with `--dry-run` mode.
  3. **Branch-specific trigger logic**: (pending) `dev` triggers dry-run; `main`
     triggers production.
  4. **Stabilization criteria**: (pending — see Ready for Human checklist
     below).
  5. **Merge strategy**: (pending) `dev` → `main` PR after criteria met. (Due:
     Indeterminate — `feat/auto-review` branch deleted, packages cherry-picked
     to `feat/packages-to-add`)

## Decisions Pending

- [x] **Disposition of `TESTING_ARCHITECTURE_PLAN.md`**: Resolved — Python
      refactoring of `scripts/` is actively in progress on
      `feat/port-scripts-to-python` (6 of 7 scripts ported; `sync-package.py`
      is the final item). The plan doc remains as rationale reference.
- [x] **Disposition of `manifest.json`**: Resolved 2026-05-15 swarm (S8.2):
      `manifest.json` added to `.gitignore` as a generated build artifact.
      Regenerated by `validate-pkgbuilds-pkl.py` at CI time. Untracked via
      `git rm --cached` — no longer in version control.
- [x] **Disposition of `oldver.json`**: Resolved — tracked in version control as
      shared nvchecker state. Config path: `oldver` in `[__config__]` section of
      `.nvchecker.toml`.

## Engineering

- [x] ~~**pkgdesc Consistency Across Package Variants**~~: Rule documented in
      `AGENTS.md` (Variant Builds §) and
      `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` (`_pkgname` entry).
      Gemini-cli family pkgdesc + .SRCINFO synced to base. Enforcement:
      conftest Rule 7 (`deny_pkgdesc_consistency` in `policies/repository.rego`,
      enforced via `validate-pkgbuilds-pkl.py` in pre-commit and CI
      `build.yml`), with `sync-package.py` §5 emitting a warning. Extraction was migrated from broken
      `grep -oP | tr -d "'"` to `scripts/pkgvar` (sandboxed bash-source utility
      that resolves all variables including `_pkgname=$_npmname`).
      **Verification passed** (exit 0, all variant groups consistent). Enforcement
      has migrated to conftest Rule 7; the standalone `check-pkgdesc-consistency.py`
      script is slated for retirement (see §Engineering).

- [ ] **Remaining Quality Checks (not yet in Pkl/Rego)**: The Pkl schema
      (`schemas/arch_pkg.pkl`) and Rego policy engine (`policies/repository.rego`,
      14 rules + 2 planned) now cover the majority of PKGBUILD quality
      enforcement. Identify any remaining checks that Rego cannot express
      (e.g., checks requiring source-code inspection, build-time behavior, or
      chroot environment) and determine whether they belong in `sync-package.py`
      inline validation or a separate linting stage. Previous `pkgvar`-based
      rule engine plans are superseded — `load_pkgbuild()` + Rego is the
      resolver + rules engine respectively. (Due: Indeterminate)

- [x] **Port `sync-package.sh` → `sync-package.py`**: Replaced the last remaining
      Bash script (317 lines) with a structured-data Python implementation
      (669 lines → 561 lines, `scripts/sync-package.py`). Uses `load_pkgbuild()` for variable
      resolution, `hashlib`+`urllib` for checksums, `pkl eval` for schema
      validation, and Python PKGBUILD renderer for final output.
      - ~~Update `discovery.yml:41` caller: `python3 scripts/sync-package.py`.~~ Done.
      - ~~Remove `build.yml:71` `chmod +x scripts/*.sh`.~~ Done (no .sh scripts remain).
      - ~~Delete `scripts/sync-package.sh` after validation.~~ Done. (Due: 4-part plan)

- [x] **Retire `check-pkgdesc-consistency.py`**: Conftest Rule 7
      (`deny_pkgdesc_consistency` in `policies/repository.rego`) already
      enforces this across all packages via `validate-pkgbuilds-pkl.py`. The
      standalone script is fully redundant.
      - ~~Delete `scripts/check-pkgdesc-consistency.py`.~~ Done.
      - ~~Remove hook from `.pre-commit-config.yaml` (`pkl-validate` covers it).~~ Done.
      - ~~Remove call from `build.yml:73`.~~ Done.
      - ~~Update `AGENTS.md` references to point at conftest Rule 7.~~ Done. (Due: 4-part plan)

- [x] **Wire `discovery.yml` Pkl+conftest validation gate**: After the
      `sync-package.py` call loop, install pkl + conftest (static binaries)
      and run `validate-pkgbuilds-pkl.py`. If validation fails, abort before
      `git commit`/`git push` — no PR is created. Gated on `steps.sync.outputs.changed
      == 'true'` so validation only runs when updates were detected.
      Installs `python-yaml` via pacman in the archlinux builder container. (Due: 4-part plan)

- [x] **OPA/Rego Policy — `no_version_constraints` (ERROR)**: Added Rule 15 to
      `policies/repository.rego` (commit `a1305e1`). Flags version operators
      (`>=`, `<=`, `>`, `<`, `=\d`) in `depends`, `makedepends`, `checkdepends`.
      Two clause blocks: comparison operators and bare `=version`. Verified with
      synthetic manifest and full 24-package production validation.

- [x] **OPA/Rego Policy — `prefer_strong_hash` (WARN)**: Added Rule 16 to
      `policies/repository.rego` (commit `a1305e1`). Flags when `md5sums` is
      populated but no `sha256sums`, `sha512sums`, or `b2sums` present. Uses
      `has_field()` check. Verified with synthetic manifest and full 24-package
      production validation.

- [x] **.SRCINFO Version Control Policy**: Research the feasibility of treating
      `.SRCINFO` as a build artifact — generated on-demand by `aur-deploy.py`
      and `makepkg --printsrcinfo` — rather than storing it in version control.
      Considerations: (a) `aur-deploy.py` already calls `makepkg --printsrcinfo`
      as part of the AUR processing pipeline, making regeneration trivial; (b)
      `.SRCINFO` desync from PKGBUILDs is a recurring chore (this session
      required regeneration for 5 packages); (c) AUR pushes require `.SRCINFO` —
      confirm `aur-deploy.py` can produce the file and push without a committed
      copy; (d) many AUR helpers and CI workflows consume `.SRCINFO` directly
      from the AUR, not from this repo's git; (e) if removed from git, the
      `.SRCINFO` presence check in CI gates (`build.yml`, `discovery.yml`) would
      need revision. Evaluate whether a `git rm --cached` migration path is
      practical, and whether the `.gitignore` should be updated. (Due:
      Indeterminate) **(Policy document exists:
      `docs/SRCINFO-VERSION-CONTROL-POLICY.md`; implementation Phase 1-4 per
      policy doc pending.)**

## Documentation

- [x] **Bash Completion Shared Convention**: The `_comp_` namespace and
      `_comp_compgen_help` conventions are duplicated across
      `gemini-bash-completion` and `doas-bash-completion` local AGENTS.md files.
      Create a centralized reference (e.g., a
      `docs/BASH-COMPLETION-CONVENTIONS.md`) documenting the shared `_comp_`
      namespace requirement and dynamic help invocation pattern. Once published,
      evaluate whether the per-package AGENTS.md entries can be slimmed or
      removed. **(Done: `docs/BASH-COMPLETION-CONVENTIONS.md` exists;
      per-package local AGENTS.md update pending.)**
- [ ] **Packager Best Practices Audit**: Audit the
      [DeveloperWiki:How to be a packager](https://wiki.archlinux.org/title/DeveloperWiki:How_to_be_a_packager)
      against this repository's AGENTS.md, agent skills, and CI/CD outputs.
      Identify any practices not yet reflected in automation rules or
      documentation standards, and integrate them. (Due: Indeterminate)
- [x] **AGENTS.md docs/ Reference Table Staleness**: Resolved 2026-05-15 swarm
      (S8.1): all 10 missing docs added to table (18 entries total, aligned with
      actual files). Ongoing: add every new doc, remove entries for deleted
      docs.
- [ ] **manual.archlinux.page Reference**: Add
      [manual.archlinux.page](https://manual.archlinux.page/) to AGENTS.md
      foundational documentation section as the browsable reference for all
      Arch Linux manual pages (man 1/5/7/8). Serves as the web-accessible
      complement to local `man` invocations. (Due: Indeterminate)
- [x] **pkgvar Array Support Documentation**: Resolved 2026-05-15 swarm (S8.5):
      `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` now documents array variable
      support via `declare -p`, with single/multi-element examples and JSON mode
      output.

## Ready for Human (Post-Swarm 2026-05-15)

These items require human execution — chroot builds, branch management, secret
provisioning, and CI verification.

- [ ] **chroot builds — 23 packages**: Run `pkgctl build` for all packages in a
      clean chroot. Verify no build failures, dependency resolution errors, or
      namcap issues.
- [x] **fix/packages-opendoas-ranger-jules disposition**: Resolved — branch
      deleted; changes absorbed into main.
- [x] **HPA rebase onto `dev`**: Cancelled — no HPA branch exists; swarm task
      was never started.
- [ ] **AUR deployment (SSH auth)**: Configure AUR SSH keys and test
      `aur-deploy.py` push for `_deploy_aur=true` packages (amass-bin, opendoas,
      python-whois).
- [x] **oldver.json decision**: Resolved — tracked as shared nvchecker state in
      `.nvchecker.toml` `[__config__]` section.
- [ ] **CI results review**: Check discovery workflow run on `dev` branch
      (dispatched 2026-05-15). Verify the new validation gate passes.
- [x] **build.yml workflow_dispatch trigger**: Completed — `workflow_dispatch`
      added to `build.yml` (commit `28b5e16`).

## Pkl Canonical Migration (Phases 1–7)

Pkl becomes the canonical source of truth for package definitions. PKGBUILD
becomes generated output. Shrinks `pkgbuild_loader.py` (492→350 lines), retires
`pkgbuild_renderer.py` (149 lines), `pkgbuild_to_pkl.py` (49 lines),
`pkgvar` (104 lines bash), `sync-package.sh` (317 lines bash), and
`merge_policy_exceptions.py` (56 lines). Net reduction: ~1,300 lines deleted,
~180 lines added (merge.pkl).

### Architecture: Functional Core, Imperative Shell

The migration follows the FCIS pattern:

| Layer | Language | Role |
|---|---|---|
| **Functional core** | Pkl + Rego | Pure validation, type constraints, rendering, policy rules. Deterministic — same input → same output. No side effects. |
| **Imperative shell** | Python | All I/O, subprocess orchestration, network fetches, crypto hashing, filesystem writes. Calls into the core; contains no validation logic itself. |

The functional core is built and proven first (Phase 1). Then the shell is
rewired to call it (Phase 3). Then the core is incrementally improved while
the shell keeps the pipeline green (Phases 4, 5, 6). The shell shrinks as
core capabilities grow — this is why the net reduction is ~1,300 lines.

Phase 2 (hand-authored `.pkl`) was originally sequenced to run after Phase 3
shell rewiring, but was **skipped**: `sync-package.py` regenerates `.pkl` from
flat dicts on every sync, vaporizing any hand-authored Pkl constructs. Phase
6.0 (merge rearchitecture) achieves the same goal — it generates `.pkl` from
typed `Package` objects with full structural fidelity, equivalent to
hand-authoring.

### Phase 1: Verify the Pkl Renderer Produces Identical Output (Functional Core Gate)

**FCIS role**: Pure functional core. `renderPKGBUILD()` takes typed Pkl data
→ produces PKGBUILD text. No I/O, no subprocesses, no side effects. Proven
in isolation before any shell touches it.

Gate: prove `renderPKGBUILD()` in `schemas/arch_pkg.pkl` can replace
`pkgbuild_renderer.py` without regressions.

- [x] 1.1 Run `pkl eval -x 'output.value.renderPKGBUILD()'` on all 24
      `package.pkl` files. Diff each against the Python renderer output.
- [x] 1.2 Fix any differences in `_quoteString()`, field ordering, or `Listing`
      rendering in `arch_pkg.pkl`.
- [x] 1.3 Add `_`-prefixed custom variable emission (`_deploy_aur`, `_pkgname`,
      etc.) to `renderPKGBUILD()` — data-driven, sorted alphabetically, matching
      Python renderer behavior exactly.
- [x] 1.4 Verify `makepkg --printsrcinfo` succeeds on Pkl-rendered output for
      every package. (22/24 pass; 2 pre-existing failures: amass-bin, amass-git
      missing generated changelog files — not a renderer issue.)

**Exit gate**: `python3 scripts/compare-renderers.py` produces zero unexpected
diffs across all 24 packages. Gate passed 2026-06-18 — 24/24 OK, 0 diffs.

### Phase 2: Migrate PKGBUILDs to Hand-Authored `.pkl` Files — SKIPPED

**FCIS role**: Functional core improvement. Each hand-authored `package.pkl`
would replace an importer-generated one. Pure data transformation — no shell changes.

**Skipped 2026-06-18.** Rationale: `sync-package.py` calls `_validate()` →
`write_pkl_module()` on every sync, which regenerates `.pkl` from flat dicts.
Any hand-authored Pkl constructs (string interpolation, omitted defaults,
typed `new { ... }` literals) are vaporized by the next version bump. Phase
6.0 (merge rearchitecture) achieves the same goal — it generates `.pkl` from
typed `Package` objects with full structural fidelity, equivalent to
hand-authoring. Each task below is reabsorbed into Phase 6.0 or left as a
cosmetic artifact of the generated format.

~~`packages/<name>/package.pkl` becomes the canonical format. `PKGBUILD` becomes
generated output.~~

- [ ] 2.1 Hand-author a `package.pkl` for each of the 24 packages. Bash lifecycle
      functions (`prepare()`, `build()`, `check()`, `package()`) remain as raw
      Pkl strings — no structural change from current generated `.pkl` files.
- [ ] 2.2 `${pkgname}`, `${pkgver}` references in `source[]` URLs become Pkl
      string interpolation `"\(pkgname)"`, `"\(pkgver)"`.
- [ ] 2.3 `depends`, `makedepends`, `provides` arrays become
      `Listing<DependsEntry>` — already typed by the schema.
- [ ] 2.4 `# Maintainer:` / `# Contributor:` comments become `maintainer` /
      `contributor` fields.
- [ ] 2.5 Validate all 24 packages: `pkl eval packages/*/package.pkl --format json`
      must pass with zero errors.
- [ ] 2.6 Render all 24 packages: `pkl eval -x 'output.value.renderPKGBUILD()'`
      must produce valid PKGBUILD text.
- [ ] 2.7 Create a `just` recipe to regenerate PKGBUILDs from `.pkl` files:
      `pkl eval packages/*/package.pkl -x 'output.value.renderPKGBUILD()' -o '%{moduleDir}/PKGBUILD'`
- [ ] 2.8 Update `.pre-commit-config.yaml` hook: validate `.pkl` files directly
      — no import step needed.

### Phase 3: Rewire `sync-package.py` for Pkl-Native Operation (Imperative Shell)

**FCIS role**: Imperative shell rewiring. Replaces two Python modules
(`pkgbuild_loader`, `pkgbuild_renderer`) with subprocess calls into the proven
Pkl core (`pkl eval --format json` for reading, `pkl eval -x renderPKGBUILD()`
for writing). The shell contains no validation or rendering logic — it delegates
entirely to the core.

Executes after Phase 1. Uses importer-generated `package.pkl`
files (already produced by `pkgbuild_to_pkl.py` and validated by Phase 1) to get
the pipeline running end-to-end. Typed Pkl-native `.pkl` files are generated
by Phase 6.0's merge function.

The sync engine reads from `.pkl` (via `pkl eval --format json`) instead of
bash-sourced PKGBUILDs.

- [x] 3.1 New function `_load_pkl(pkg_dir)` — calls
      `pkl eval package.pkl --format json`, splits function bodies into
      `funcs` dict (renaming pkgverFunc→pkgver, packageFunc→package),
      strips 3 schema-default booleans to match loader behavior.
- [x] 3.2 Replace `load_pkgbuild(path)` call in `main()` with `_load_pkl(pkg_dir)`.
- [x] 3.3 Schema prep for `_load_pkl()`: all `_`-prefixed fields un-hidden so
      they appear in Pkl JSON output. The merge/classify/bump/checksum logic
      operates on the same dict structure — no changes needed.
- [x] 3.4 Replace `render_pkgbuild(vars_, funcs)` call with Pkl subprocess:
      `pkl eval -x 'output.value.renderPKGBUILD()'`.
- [x] 3.5 Remove `from pkgbuild_renderer import render_pkgbuild`. Keep
      `from pkgbuild_loader import load_pkgbuild` — still needed for upstream
      PKGBUILD parsing (Calls B, D, E: merged result, cached upstream, new
      upstream fetch). Full removal blocked until merge is rearchitected for
      structured data (→ Phase 6.0).
- [x] 3.6 `_check_variant_consistency` loads sibling packages via
      `_load_pkl()` instead of `load_pkgbuild()`.
- [x] 3.7 `_validate` already writes `package.pkl` and runs
      `pkl eval --format json` — unchanged. `.PKGBUILD.upstream` cache bug
      fixed (was no-op rename-to-self; now correctly updates cache after merge).
      Gate passed 2026-06-18: 24/24 _load_pkl() == load_pkgbuild() dict shape.

### Phase 4: Amends for Variant Packages (After Phase 3)

**FCIS role**: Functional core improvement. Pkl's `amends` inheritance
replaces field duplication between variant packages. Pure data modeling —
the shell (`sync-package.py`) needs no changes; it already calls `pkl eval`
per package.

Variant packages inherit from base via Pkl `amends` instead of duplicating fields.

- [ ] 4.1 Identify all variant groups (e.g., `apm` / `apm-bin` / `apm-go-git`,
      `amass-bin` / `amass-git`).
- [ ] 4.2 Designate the base package for each group (e.g., `apm`).
- [ ] 4.3 Convert variant `.pkl` files to `amends "../base-pkg/package.pkl"` —
      only override `pkgname`, `source`, `sha256sums`, `packageFunc` (or
      whatever actually differs).
- [ ] 4.4 Late binding ensures `${pkgname}` in source URLs resolves correctly
      in each variant.
- [ ] 4.5 Verify `pkl eval` on each variant produces correct `pkgname`, `pkgdesc`,
      and `source` in rendered output.

### Phase 5: Native Manifest Composition + `output.files`

**FCIS role**: Final core consolidation. One `pkl eval` invocation replaces
three Python scripts (`build_manifest()`, `merge_policy_exceptions.py`, and
`makepkg --printsrcinfo`). The shell shrinks to `pkl eval manifest.pkl →
conftest test → write files`. This is the end state of the FCIS architecture.

Pkl's import graph replaces Python's manual JSON concatenation. One `pkl eval`
invocation produces `manifest.json`, all PKGBUILDs, and all `.SRCINFO` files.

- [ ] 5.1 Create `manifest.pkl` in repo root — imports
      `packages/*/package.pkl`, outputs `Listing<Package>` to `output.value`.
      Replaces `validate-pkgbuilds-pkl.py` `build_manifest()`.
- [ ] 5.2 `manifest.pkl` merges per-package `policy_exceptions.yaml` into an
      `exceptions` field on output. Replaces `merge_policy_exceptions.py`.
- [ ] 5.3 Add `output.files` to the Package schema or manifest: `PKGBUILD` →
      `output.text`, `.SRCINFO` → generated from same data. Replaces
      `makepkg --printsrcinfo` in `aur-deploy.py`.
- [ ] 5.4 `validate-pkgbuilds-pkl.py` becomes a thin wrapper:
      `pkl eval manifest.pkl --format json > manifest.json && conftest test manifest.json`.
- [ ] 5.5 Update `.github/workflows/discovery.yml` and `build.yml` to call the
      new thin validation pipeline.

### Phase 6: Rearchitect Merge + Retire Dead Code

**FCIS role**: Close the last FCIS violation (upstream merge path) and shrink
the shell. The merge rearchitecture replaces `git merge-file` + imperative
identity restoration with a typed Pkl 3-way merge. After this, the only
remaining bash subprocess calls are: (a) parse raw upstream PKGBUILD text from
the internet (irreducible — upstream PKGBUILDs are bash scripts), and (b) run
package-local `update.sh` hooks.

#### 6.0 Rearchitect the Merge (Option C: Structured Diff + Pkl Merge)

**Why**: The merge path currently calls `load_pkgbuild()` 3 times (old upstream,
new upstream, merged result), runs `git merge-file` on PKGBUILD text, and
applies identity restoration imperatively. This is the last FCIS violation
documented in the Phase 3 gate — the functional core renders PKGBUILDs but
cannot consume them for merging.

**Design**: A new Pkl module `schemas/merge.pkl` provides two functions:

- `classifyChanges(base: Package, theirs: Package) -> ChangeSet` — typed
  field-by-field comparison across concern groups (AUTHORSHIP, IDENTITY,
  VERSION, METADATA, DEPENDS, MAKEDEPENDS, CHECKDEPENDS, OPTDEPENDS,
  SOURCES, BUILD). Returns classified change events and a `buildChanged`
  flag.
- `merge(ours: Package, base: Package, theirs: Package) -> Package` —
  typed 3-way merge with per-field resolution rules:
  - Identity fields (`pkgname`, `provides`, `conflicts`, `replaces`) → always ours
  - `ours == base AND theirs != base` → take theirs (upstream change, we didn't touch)
  - `ours != base AND theirs == base` → keep ours (our change, upstream didn't touch)
  - `ours != base AND theirs != base` → conflict → keep ours, set `_prereview`
  - Maintainer authorship → ours stays; upstream maintainer demoted to contributor
  - Build functions differ → set `_prereview` (replaces imperative `_apply_prereview_marker`)

**Bridge**: Python writes upstream dicts as temporary `.pkl` files
(`.upstream.base.pkl`, `.upstream.new.pkl`) via `write_pkl_module()`, generates
a one-shot `.merge.script.pkl` that imports all three packages and calls
`merge.merge()`, then runs `pkl eval` on the script. The JSON output is loaded
as the merged `vars_`/`funcs`.

**Migration steps**:

- [x] 6.0.1 Write `schemas/merge.pkl` — `classifyChanges()` and `merge()`
        functions with concern group definitions and typed field comparison.
        **Done 2026-06-18.** Uses idiomatic `(ours) { …when-blocks… }` amends
        pattern (Pkl LR §Amending Objects) instead of `new Package { … }` field-by-field
        reconstruction. D1/D2/D3 design decisions confirmed and implemented.
        Module-level helper functions (`_dataConflicts`, `_buildConflict`,
        `_prereviewText`) compute the prereview marker. Verified with `pkl eval -x`
        smoke script (9/9 assertions pass) and bridge-simulation JSON output.\
        Pkl `let` expressions (0.31.1) confirmed working.
- [x] 6.0.2 Write Pkl unit tests for merge.pkl — fixture packages covering:
        no-change, pkgver-bump-only, build-function-changed, conflict-both-changed,
        maintainer-demotion, identity-field-protection.
        **Done 2026-06-18.** 7 fixture packages in `schemas/test-fixtures/`;
        `schemas/merge_test.pkl` amends `pkl:test` with 13 snapshot examples
        (10 merge scenarios + 3 classifyChanges). 100% pass rate. Generated
        `pkl-expected.pcf` is committed and serves as the regression gate.
- [x] 6.0.3 Add `write_pkl_module()` support for writing to an arbitrary output
        path. ~~(currently hardcoded to `package.pkl` in the package directory).~~
        **Resolved**: `write_pkl_module()` returns a string — it never writes to disk
        (`scripts/pkl_writer.py:166`). Callers write the output wherever needed.
        No change required. PHASE-6 Chunk 4a correctly uses the return value.
- [ ] 6.0.4 In `sync-package.py` `main()`: replace the merge path (current
        lines ~487–510: classify, fetch assets, merge_with_identity, prereview
        marker) with the bridge — write temp `.pkl` files, generate merge script,
        run `pkl eval`, load result, clean up temps.
- [ ] 6.0.5 Delete from `sync-package.py`: `_IDENTITY_FIELDS`, `_CONCERN_GROUPS`,
        `_classify_changes()`, `_merge_with_identity()`, `_apply_prereview_marker()`.
- [ ] 6.0.6 Run full pipeline smoke test: `python scripts/sync-package.py <pkg> <ver>`
        for a package with and without upstream changes.
- [ ] 6.0.7 Remove `from pkgbuild_loader import load_pkgbuild` at module level.
        Replace with inline imports only where still needed (upstream PKGBUILD
        text parsing — the irreducible bash subprocess for raw internet data).

**What survives `load_pkgbuild()`**: Two calls remain for parsing raw upstream
PKGBUILD text (old cache, new fetch). These are unavoidable — upstream
PKGBUILDs contain bash constructs (`$(...)`, dynamic `pkgver()`) that require
bash sourcing to resolve. The bash subprocess is documented as the permanent
adapter layer for external data ingestion.

#### 6.1 Retire Dead Scripts

Validate each deletion by confirming the pipeline still passes end-to-end.

| Script | Lines | Action |
|---|---|---|
| `sync-package.py` (merge functions) | ~92 | Shrink — `_classify_changes`, `_merge_with_identity`, `_apply_prereview_marker`, `_IDENTITY_FIELDS`, `_CONCERN_GROUPS` deleted |
| `pkgbuild_loader.py` | 492 → ~350 | Shrink — module-level import removed from sync-package.py; kept only for upstream bash parsing (2 call sites) |
| `compare-renderers.py` | 86 | Delete — depends on `pkgbuild_renderer.py`; `makepkg --printsrcinfo` supersedes post-Phase 6 |
| `pkgbuild_renderer.py` | 149 | Delete — replaced by `renderPKGBUILD()` in schema; already unused by sync-package.py since Phase 3 |
| `pkgbuild_to_pkl.py` | 49 | Retain as one-time migration tool; remove from CI |
| `pkgvar` (bash) | 104 | Delete — after `aur-deploy.py` refactored to use `pkl eval --format json` for pkgver/pkgrel resolution; currently invoked at lines 187–188 |
| `sync-package.sh` (bash) | 317 | Delete — `sync-package.py` is the single engine |
| `merge_policy_exceptions.py` | 56 | Delete — `manifest.pkl` handles this natively |
| `validate-pkgbuilds-pkl.py` | ~100 remaining | Shrink — `build_manifest()` removed; becomes thin CLI wrapper |

Net reduction: ~1,300 lines deleted/removed, ~180 lines added (merge.pkl).
13 scripts → 6 scripts.

### Phase 7: Update Documentation & CI

- [ ] 7.1 Update `AGENTS.md` §1 — add Pkl as source of truth; remove
      bash-centric references (`pkgvar`, `pkgbuild_loader`, `sync-package.sh`).
- [ ] 7.2 Update `PKL-SCHEMA-DESIGN.md` — mark Phase 4 as implemented.
- [ ] 7.3 Update `PKL-CROSS-PHASE-EVALUATION.md` — update status to reflect
      completed migration.
- [ ] 7.4 Update `AGENTS.md` reference table — remove references to deleted
      scripts, add `manifest.pkl`.
- [ ] 7.5 Verify CI workflows still pass after all deletions and rewiring.

### Risk Registry

| Risk | Mitigation |
|---|---|
| Pkl renderer produces subtly different PKGBUILD than Python | ~~Phase 1 diff gate blocks proceed until zero-diff~~ Gate passed 2026-06-18: 24/24 identical |
| Hand-authored `.pkl` files have typos | Pkl type checker catches all structural errors at eval time |
| `makepkg` rejects Pkl-rendered PKGBUILD (quoting) | ~~Phase 1.4 gate: `makepkg --printsrcinfo` on every rendered output~~ Verified 2026-06-18: 22/24 pass (2 pre-existing changelog failures, not renderer-related) |
| CI `pkl eval` cold-start latency | Pkl native binary (~200ms); already called in current pipeline |
| `sync-package.py` merge logic assumes bash-sourced dicts, breaks on Pkl-sourced | Both produce same dict structure (proven by Phase 3 rewiring with importer-generated `.pkl`) |
| FCIS boundary leaks — validation logic creeps into shell | Phase 3 explicitly removes validation from shell (`load_pkgbuild` + `render_pkgbuild` replaced by `pkl eval` subprocess). Any new validation belongs in Pkl schema or Rego policy |
| Merge rearchitecture produces wrong merged Package | Phase 6.0.2: Pkl unit tests with fixture packages covering all merge scenarios before replacing live merge path |
| Upstream PKGBUILDs have fields not in our schema | Merge function handles missing fields gracefully (treat absent as null, skip comparison). Schema evolves to accommodate upstream drift |
| Pkl field-by-field reflection slower than Python dict comparison | Benchmark against current `_classify_changes()`. If regression >100ms, add field-level caching. Target: <500ms for 24 packages |
| `.upstream.*.pkl` temp files left behind on error | `finally` block in merge bridge or write to `/tmp/opencode/` outside packages directory |

### Execution Order

```
Phase 1 ──► Phase 3 ──► Phase 4 ──► Phase 5
(CORE)      (SHELL)     (CORE++)    (CORE++)
               │                       │
               ▼                       ▼
          Phase 6 (SHRINK) ───► Phase 7 (DOCS)
```

Phase 1 is the hard gate — if `renderPKGBUILD()` can't produce identical output,
the rest is blocked. Phase 3 wires the shell to the proven core and uses
importer-generated `.pkl` files to get the pipeline green early.
Phases 4 and 5 improve the core further. Phase 6 deletes each script as its
replacement is verified. Phase 7 updates documentation.
