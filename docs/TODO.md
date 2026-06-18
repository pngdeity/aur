# Project TODO

Outstanding architectural and documentation items requiring completion.

## Architecture

- [ ] **Package Decommissioning SOP**: Define a standard process for removing
      packages from the repository, including AUR dropping and discovery
      cleanup. (Due: Indeterminate)
- [ ] **Edge-Case Recovery Logic**: Define deterministic recovery paths for
      hybrid merge failures and 404 upstream assets. (Due: Upon `scripts/`
      directory refactor)
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
      `arch-builder.sh` and `build.yml` had placeholder logic for a
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
  3. Update `arch-builder.sh` to publish built packages to the local repo before
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

- [ ] **Disposition of `TESTING_ARCHITECTURE_PLAN.md`**: Decide whether to
      proceed with the Python refactoring of `scripts/`, keep the plan as a
      reference for future consideration, or archive it as superseded. If
      proceeding, define acceptance criteria, resourcing, and a target
      milestone. If archiving, move it to a `docs/archive/` directory or add a
      "Status: Archived" header.
- [x] **Disposition of `manifest.json`**: Resolved 2026-05-15 swarm (S8.2):
      `manifest.json` added to `.gitignore` as a generated build artifact.
      Regenerated by `validate-pkgbuilds-pkl.sh` at CI time. Untracked via
      `git rm --cached` — no longer in version control.
- [x] **Disposition of `oldver.json`**: Resolved — tracked in version control as
      shared nvchecker state. Config path: `oldver` in `[__config__]` section of
      `.nvchecker.toml`.

## Engineering

- [x] ~~**pkgdesc Consistency Across Package Variants**~~: Rule documented in
      `AGENTS.md` (Variant Builds §) and
      `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` (`_pkgname` entry).
      Gemini-cli family pkgdesc + .SRCINFO synced to base. Enforcement:
      `scripts/check-pkgdesc-consistency.sh` (called by pre-commit, CI
      `build.yml`, and CI `discovery.yml` gate), with `sync-package.sh` §5
      emitting a warning. Extraction was migrated from broken
      `grep -oP | tr -d "'"` to `scripts/pkgvar` (sandboxed bash-source utility
      that resolves all variables including `_pkgname=$_npmname`).
      **Verification passed** (exit 0, all variant groups consistent). Remaining
      follow-up work:
  - **Broader pkgvar adoption**: Five `grep | cut | tr`/`grep -oP` extraction
    points remain in `sync-package.sh` (lines 176, 177, 264, 268, 273) and two
    in `aur-deploy.sh` (lines 96, 97). These work correctly today with
    string-literal values but would silently fail if any PKGBUILD used variable
    references in those fields. Adopting `pkgvar` here would eliminate that
    future risk.
  - **Files created/modified**: `scripts/pkgvar` (new),
    `scripts/check-pkgdesc-consistency.sh`, `scripts/sync-package.sh`,
    `.pre-commit-config.yaml` (new), `.github/workflows/build.yml`,
    `.github/workflows/discovery.yml`, `AGENTS.md`,
    `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md`, `docs/TODO.md`,
    `packages/gemini-cli-git/PKGBUILD`, `packages/gemini-cli-git/.SRCINFO`,
    `packages/gemini-cli-preview/PKGBUILD`,
    `packages/gemini-cli-preview/.SRCINFO`,
    `packages/gemini-cli-nightly/PKGBUILD`,
    `packages/gemini-cli-nightly/.SRCINFO`.

- [ ] **PKGBUILD Quality Rules Engine**: Research implementation of a
      programmatic PKGBUILD quality checker using `scripts/pkgvar` (sandboxed
      sourcing) as the resolver foundation. Requirements:
  1. **Array variable support**: Extend `pkgvar` to handle Bash array variables
     (`provides`, `conflicts`, `depends`, `source`, etc.). Sourcing resolves
     them but the current `printf "${!4:-}"` dereference only captures the first
     element. Options: `declare -p` serialization, IFS-delimited output with a
     sentinel separator, or per-element invocation via `${var[@]}` counted by
     `${#var[@]}`.
  2. **Rule encoding**: Define a rule format (YAML, JSON schema, or a Bash DSL)
     that codifies the checks identified to date — no unprovided conflicts, no
     self-references in provides/conflicts, variant provides/conflicts symmetry,
     valid package names — plus the existing `_pkgname`-based pkgdesc
     consistency rule (currently in `scripts/check-pkgdesc-consistency.sh`;
     opportunity to unify). Evaluate whether rules should live in a config file
     or be hardcoded in a checker script.
  3. **Integration**: Wire the rules engine into `scripts/` for use by CI
     (`build.yml`), pre-commit hooks, and `sync-package.sh` validation gates.
  4. **Performance**: Benchmark the subshell approach at scale. One bash
     invocation per variable per PKGBUILD is O(n²) — batch resolution (source
     once, dump all vars) should be evaluated against `declare -p` overhead.
     Profile across the full 30+ package corpus.

5. **Prior work**: Survey existing tools — `namcap` rule architecture, Arch
   `devtools` (checkpkg, diffpkg), AUR helpers with analysis features, and any
   prior art in PKGBUILD static analysis or Bash sandboxing libraries — to avoid
   reinventing the wheel and to identify reusable patterns. (Due: Indeterminate)

- [ ] **OPA/Rego Policy — `no_version_constraints` (ERROR)**: Add a Rego rule to
      deny version operators (`>=`, `<=`, `>`, `<`, `=`) embedded in `depends`,
      `makedepends`, and `checkdepends` strings. Pacman does not enforce version
      ranges — they are non-functional noise. Example violation:
      `depends=('glibc>=2.35')`. Pkl pipeline preserves literal dep strings,
      making this a straightforward `re_match` check.

- [ ] **OPA/Rego Policy — `prefer_strong_hash` (WARN)**: Add a Rego rule to warn
      when `md5sums` is populated but `sha256sums`, `sha512sums`, or `b2sums`
      are not. `md5` is cryptographically broken per Arch Wiki guidelines; the
      standard is at least SHA-256. Example violation: `md5sums=('f0d26bc...')`
      with no `sha256sums` array present.

- [x] **.SRCINFO Version Control Policy**: Research the feasibility of treating
      `.SRCINFO` as a build artifact — generated on-demand by `aur-deploy.sh`
      and `makepkg --printsrcinfo` — rather than storing it in version control.
      Considerations: (a) `aur-deploy.sh` already calls `makepkg --printsrcinfo`
      as part of the AUR processing pipeline, making regeneration trivial; (b)
      `.SRCINFO` desync from PKGBUILDs is a recurring chore (this session
      required regeneration for 5 packages); (c) AUR pushes require `.SRCINFO` —
      confirm `aur-deploy.sh` can produce the file and push without a committed
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
      `aur-deploy.sh` push for `_deploy_aur=true` packages (amass-bin, opendoas,
      python-whois).
- [x] **oldver.json decision**: Resolved — tracked as shared nvchecker state in
      `.nvchecker.toml` `[__config__]` section.
- [ ] **CI results review**: Check discovery workflow run on `dev` branch
      (dispatched 2026-05-15). Verify the new validation gate passes.
- [x] **build.yml workflow_dispatch trigger**: Completed — `workflow_dispatch`
      added to `build.yml` (commit `28b5e16`).
- [ ] **CI/CD maintenance burden reduction**: 12 items identified in the
      2026-06-18 CI/CD maintenance audit. Tasks are documented in
      [`TASKS.md`](../TASKS.md) at the repository root. Priorities: extract
      duplicated configuration (#1), centralize version pins (#2), add
      unknown-change guard to concern classifier (#3).
