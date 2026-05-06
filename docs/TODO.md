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

## Documentation

- [ ] **Bash Completion Shared Convention**: The `_comp_` namespace and `_comp_compgen_help` conventions are duplicated across `gemini-bash-completion` and `doas-bash-completion` local AGENTS.md files. Create a centralized reference (e.g., a `docs/BASH-COMPLETION-CONVENTIONS.md`) documenting the shared `_comp_` namespace requirement and dynamic help invocation pattern. Once published, evaluate whether the per-package AGENTS.md entries can be slimmed or removed.
