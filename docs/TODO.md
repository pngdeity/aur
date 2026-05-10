# Project TODO

Outstanding architectural and documentation items requiring completion.

## Architecture

- [ ] **Package Decommissioning SOP**: Define a standard process for removing packages from the repository, including AUR dropping and discovery cleanup. (Due: Indeterminate)
- [ ] **Edge-Case Recovery Logic**: Define deterministic recovery paths for hybrid merge failures and 404 upstream assets. (Due: Upon `scripts/` directory refactor)
- [ ] **Evaluate makepkg-optimize relevance**: Assess whether `makepkg-optimize` should be integrated into the build pipeline. Evaluate its compiler flag overrides against `makepkg.conf(5)` defaults, its impact on reproducible builds (`SOURCE_DATE_EPOCH`), and whether it provides meaningful performance or security gains for this repository's package set.

## Agent Skills

- [ ] **Skill Description Trigger Validation**: The three Agent Skills (`pkg-update`, `pkg-bootstrap`, `pkg-patch-recovery`) have untested `description` fields. Per the [agentskills.io optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) guide: design 20 trigger eval queries per skill (should-trigger and should-not-trigger, including near-misses), run each query 3+ times against the agent router, and compute trigger rates. Use train/validation splits to avoid overfitting. Before implementation, research the state of the art — existing automated eval frameworks for skill description testing, prior work from [agentskills/skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator), and any trigger-testing tooling that has emerged since the spec was published.

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

## Documentation

- [ ] **Bash Completion Shared Convention**: The `_comp_` namespace and `_comp_compgen_help` conventions are duplicated across `gemini-bash-completion` and `doas-bash-completion` local AGENTS.md files. Create a centralized reference (e.g., a `docs/BASH-COMPLETION-CONVENTIONS.md`) documenting the shared `_comp_` namespace requirement and dynamic help invocation pattern. Once published, evaluate whether the per-package AGENTS.md entries can be slimmed or removed.
- [ ] **Packager Best Practices Audit**: Audit the [DeveloperWiki:How to be a packager](https://wiki.archlinux.org/title/DeveloperWiki:How_to_be_a_packager) against this repository's AGENTS.md, agent skills, and CI/CD outputs. Identify any practices not yet reflected in automation rules or documentation standards, and integrate them. (Due: Indeterminate)
