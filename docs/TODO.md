# Project TODO

Outstanding architectural and documentation items requiring completion.

## Architecture

- [ ] **Package Decommissioning SOP**: Define a standard process for removing packages from the repository, including AUR dropping and discovery cleanup. (Due: Indeterminate)
- [ ] **Edge-Case Recovery Logic**: Define deterministic recovery paths for hybrid merge failures and 404 upstream assets. (Due: Upon `scripts/` directory refactor)
- [ ] **Evaluate makepkg-optimize relevance**: Assess whether `makepkg-optimize` should be integrated into the build pipeline. Evaluate its compiler flag overrides against `makepkg.conf(5)` defaults, its impact on reproducible builds (`SOURCE_DATE_EPOCH`), and whether it provides meaningful performance or security gains for this repository's package set.

## Agent Skills

- [ ] **Skill Description Trigger Validation**: The three Agent Skills (`pkg-update`, `pkg-bootstrap`, `pkg-patch-recovery`) have untested `description` fields. Per the [agentskills.io optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) guide: design 20 trigger eval queries per skill (should-trigger and should-not-trigger, including near-misses), run each query 3+ times against the agent router, and compute trigger rates. Use train/validation splits to avoid overfitting. Before implementation, research the state of the art — existing automated eval frameworks for skill description testing, prior work from [agentskills/skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator), and any trigger-testing tooling that has emerged since the spec was published.

## Engineering (CI/CD)

- [ ] **Dev Branch with CI Dry-Run Pipeline**: Establish a `dev` branch that runs CI/CD processes in dry-run/validation mode, serving as a staging gate between feature branches and `main`. The end goal is to merge `feat/auto-review` into `dev`, stabilize all automation there, then merge `dev` into `main` once stable. Tasks:
  1. **Create `dev` branch**: Branch off `main` (or `feat/auto-review` directly) and set it as the default for PRs targeting stabilization.
  2. **Dry-run pipeline mechanics**: Extend `release.yml` and `build.yml` with a `--dry-run` mode (or a separate `dry-run.yml` workflow) that:
     - Runs `aur-deploy.sh --dry-run` for every `_deploy_aur=true` package (already implemented; needs wiring)
     - Runs `pkgctl build` or `makechrootpkg` but stops before artifact publication
     - Runs `sync-package.sh` validation gates (namcap, pkgdesc consistency, provides/conflicts audit) without committing
     - Validates `.SRCINFO` regeneration against current state
  3. **Branch-specific trigger logic**: `dev` branch triggers the dry-run pipeline on push/PR; `main` triggers the production pipeline. Evaluate whether this needs a single `if: github.ref` conditional in `release.yml` or separate workflow files.
  4. **Stabilization criteria** — functionality that must be proven stable in `dev` before `main` automation is enabled:
     - **AUR deployment**: `aur-deploy.sh --dry-run` passes for all `_deploy_aur` packages with correct PKGBUILD processing (variable stripping, `.SRCINFO` generation, SSH auth, diff output matching expected state)
     - **Build integrity**: All packages build cleanly in a chroot (`pkgctl build`) with no dependency resolution failures or namcap errors
     - **Variant build correctness**: Variant PKGBUILDs produce the expected sub-architecture-targeted binaries; `_repo_subarch` conflict with `_deploy_aur` is enforced
     - **Quality gates pass**: `check-pkgdesc-consistency.sh` exit-0 bug is fixed; provides/conflicts audit (no unprovided conflicts, no self-references) passes for all packages
     - **pkgvar array support**: `scripts/pkgvar` handles array variables (see Quality Rules Engine entry above) so that provides/conflicts validation can be automated in CI
     - **Declarative cleanup coverage**: All repo-local transformations are expressible as declarative flags (`_demote_upstream_maintainer`, `_use_common_gemini_settings`) — no orphaned imperative `update.sh` scripts that might silently fail in the pipeline
     - **Deterministic idempotency**: `sync-package.sh` produces bitwise-identical output across repeated runs for the same inputs (no timestamp drift, no nonce injection); validated by `makerepropkg` or a checksum-based regression test
  5. **Merge strategy**: Once all criteria are met, `dev` merges into `main` via a standard PR; the CI trigger condition flips from dry-run to production on `main`. The `dev` branch persists as the ongoing stabilization target for future feature branches.
  (Due: Before `feat/auto-review` merges to `main`)

## Decisions Pending

- [ ] **Disposition of `TESTING_ARCHITECTURE_PLAN.md`**: Decide whether to proceed with the Python refactoring of `scripts/`, keep the plan as a reference for future consideration, or archive it as superseded. If proceeding, define acceptance criteria, resourcing, and a target milestone. If archiving, move it to a `docs/archive/` directory or add a "Status: Archived" header.

## Engineering

- [x] ~~**pkgdesc Consistency Across Package Variants**~~: Rule documented in `AGENTS.md` (Variant Builds §) and `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` (`_pkgname` entry). Gemini-cli family pkgdesc + .SRCINFO synced to base. Enforcement: `scripts/check-pkgdesc-consistency.sh` (called by pre-commit, CI `build.yml`, and CI `discovery.yml` gate), with `sync-package.sh` §5 emitting a warning. Extraction was migrated from broken `grep -oP | tr -d "'"` to `scripts/pkgvar` (sandboxed bash-source utility that resolves all variables including `_pkgname=$_npmname`). **Verification passed** (exit 0, all variant groups consistent). Remaining follow-up work:
  - **Broader pkgvar adoption**: Five `grep | cut | tr`/`grep -oP` extraction points remain in `sync-package.sh` (lines 176, 177, 264, 268, 273) and two in `aur-deploy.sh` (lines 96, 97). These work correctly today with string-literal values but would silently fail if any PKGBUILD used variable references in those fields. Adopting `pkgvar` here would eliminate that future risk.
   - **Files created/modified**: `scripts/pkgvar` (new), `scripts/check-pkgdesc-consistency.sh`, `scripts/sync-package.sh`, `.pre-commit-config.yaml` (new), `.github/workflows/build.yml`, `.github/workflows/discovery.yml`, `AGENTS.md`, `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md`, `docs/TODO.md`, `packages/gemini-cli-git/PKGBUILD`, `packages/gemini-cli-git/.SRCINFO`, `packages/gemini-cli-preview/PKGBUILD`, `packages/gemini-cli-preview/.SRCINFO`, `packages/gemini-cli-nightly/PKGBUILD`, `packages/gemini-cli-nightly/.SRCINFO`.

- [ ] **PKGBUILD Quality Rules Engine**: Research implementation of a programmatic PKGBUILD quality checker using `scripts/pkgvar` (sandboxed sourcing) as the resolver foundation. Requirements:
  1. **Array variable support**: Extend `pkgvar` to handle Bash array variables (`provides`, `conflicts`, `depends`, `source`, etc.). Sourcing resolves them but the current `printf "${!4:-}"` dereference only captures the first element. Options: `declare -p` serialization, IFS-delimited output with a sentinel separator, or per-element invocation via `${var[@]}` counted by `${#var[@]}`.
  2. **Rule encoding**: Define a rule format (YAML, JSON schema, or a Bash DSL) that codifies the checks identified to date — no unprovided conflicts, no self-references in provides/conflicts, variant provides/conflicts symmetry, valid package names — plus the existing `_pkgname`-based pkgdesc consistency rule (currently in `scripts/check-pkgdesc-consistency.sh`; opportunity to unify). Evaluate whether rules should live in a config file or be hardcoded in a checker script.
  3. **Integration**: Wire the rules engine into `scripts/` for use by CI (`build.yml`), pre-commit hooks, and `sync-package.sh` validation gates.
  4. **Performance**: Benchmark the subshell approach at scale. One bash invocation per variable per PKGBUILD is O(n²) — batch resolution (source once, dump all vars) should be evaluated against `declare -p` overhead. Profile across the full 30+ package corpus.
  5. **Prior work**: Survey existing tools — `namcap` rule architecture, Arch `devtools` (checkpkg, diffpkg), AUR helpers with analysis features, and any prior art in PKGBUILD static analysis or Bash sandboxing libraries — to avoid reinventing the wheel and to identify reusable patterns.
  (Due: Indeterminate)

- [ ] **.SRCINFO Version Control Policy**: Research the feasibility of treating `.SRCINFO` as a build artifact — generated on-demand by `aur-deploy.sh` and `makepkg --printsrcinfo` — rather than storing it in version control. Considerations: (a) `aur-deploy.sh` already calls `makepkg --printsrcinfo` as part of the AUR processing pipeline, making regeneration trivial; (b) `.SRCINFO` desync from PKGBUILDs is a recurring chore (this session required regeneration for 5 packages); (c) AUR pushes require `.SRCINFO` — confirm `aur-deploy.sh` can produce the file and push without a committed copy; (d) many AUR helpers and CI workflows consume `.SRCINFO` directly from the AUR, not from this repo's git; (e) if removed from git, the `.SRCINFO` presence check in CI gates (`build.yml`, `discovery.yml`) would need revision. Evaluate whether a `git rm --cached` migration path is practical, and whether the `.gitignore` should be updated. (Due: Indeterminate)

## Documentation

- [ ] **Bash Completion Shared Convention**: The `_comp_` namespace and `_comp_compgen_help` conventions are duplicated across `gemini-bash-completion` and `doas-bash-completion` local AGENTS.md files. Create a centralized reference (e.g., a `docs/BASH-COMPLETION-CONVENTIONS.md`) documenting the shared `_comp_` namespace requirement and dynamic help invocation pattern. Once published, evaluate whether the per-package AGENTS.md entries can be slimmed or removed.
- [ ] **Packager Best Practices Audit**: Audit the [DeveloperWiki:How to be a packager](https://wiki.archlinux.org/title/DeveloperWiki:How_to_be_a_packager) against this repository's AGENTS.md, agent skills, and CI/CD outputs. Identify any practices not yet reflected in automation rules or documentation standards, and integrate them. (Due: Indeterminate)
