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

- [ ] **Silent-failure pattern across the sync pipeline**: Nine defects found
      in one session shared a single shape — each produced a plausible
      artifact instead of a signal, so it could go unnoticed indefinitely.
      They are not nine coincidences; they are one property of this tooling.
      The instances, with what each produced instead of an error:
  1. The `unzip`-not-in-base-devel guard in `pkl-lsp` — a guard that silently
     skipped its own purpose.
  2. `amass-git`/`amass-bin` declaring `changelog=` files that never existed
     in any commit — `aur-deploy.sh` copies the changelog only `-f` it
     exists, so a PKGBUILD was shipped referencing a file the AUR repo does
     not contain.
  3. The nvchecker token gap — a `no-result` error is non-fatal, nvchecker
     exits 0, and CI filters for `updated` events, so six packages had dead
     version checks producing no output at all.
  4. The CI per-package migration — a package with no local
     `.nvchecker.toml` simply has no check, and nothing reports the absence.
  5. Version-string shape mismatches (`pkl-lsp-bin`'s hyphenated tag,
     `opendoas` missing `prefix`) — reported versions that `makepkg` rejects,
     visible only once a check actually ran.
  6. `ranger-doas`'s phantom patch files — declared in `source=()` and
     applied in `prepare()`, absent from every commit. Resolved 2026-10-16:
     the patches are removed. The change they carried is upstream
     (`ranger/ranger#3039`, merged 2025-01-03), so there was nothing to
     port. The package remains parked on `.nvchecker.toml.disabled`; whether
     to revive it is a separate question.
  7. `nvtake` requiring `newver` — `load_file` sets `ver_files` only when
     both `oldver` and `newver` are present, so the step could never have
     worked; latent because an earlier step always failed first.
  8. A 386 MB `makepkg` clone staged by `git add packages/`, rejected at
     push time — the `.gitignore` pattern `packages/*/.git` cannot match a
     clone nested one level deeper.
  9. `fetch_upstream_assets()` reading only the first source array and
     downloading colliding local names to one file, so `updpkgsums` wrote the
     x86_64 checksum into `sha512sums_aarch64` — a package that would fail
     its own checksum check on aarch64.

      The common root is that a failure in these tools yields a *result*
      rather than an *error*, so nothing escalates. Consider: making each
      stage assert its own postcondition (a check per package, a file per
      declared asset, a distinct checksum per source specifier), and failing
      loudly when an input it declares cannot be found. (Due: Indeterminate)

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
      shared nvchecker state. Config path: `oldver` in the `[__config__]` section
      that CI synthesizes into its `master.toml`.

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

- [ ] **`aur-deploy.sh` changelog guard is silent**: `scripts/aur-deploy.sh`
      copies a package's `changelog=` file only if it exists (lines 47-49 for
      the staging dir, 129-131 for the AUR clone), so a PKGBUILD declaring a
      `changelog=` that is absent is deployed **without** the file and nothing
      reports it. Found 2026-10-15: `amass-git` and `amass-bin` both declared
      changelogs that never existed in any commit (introduced by `c98db45`),
      which made `makepkg` fail outright (`changelog file (...) does not exist
      or is not a regular file`) and left the AUR copies stuck at pkgrel 1.
      Both declarations were dropped 2026-10-15. The script is being replaced on
      another branch and must not be modified here; the gap is recorded so the
      replacement does not inherit it. (Due: Indeterminate)
- [ ] **Withdrawn-maintainership audit**: `_deploy_aur=true` was found on four
      packages whose AUR entries are now ABSENT — `apm`, `apm-go-git`,
      `python-azure-ai-inference`, `python-llm-github-models`. All four flags
      were removed 2026-10-15. The root cause is that `packages/` holds three
      categories of package (owned AUR entries, custom variants of
      other-maintainer AUR packages, custom variants of official repo packages)
      and nothing detected when a package crossed from owned to not-owned.
      `aur-deploy.sh` would have attempted to push over packages this
      repository does not own. Mitigated by policy text in `AGENTS.md` §AUR
      Deployment Gate and `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md`, but a
      mechanical check (compare `_deploy_aur=true` set against the live AUR
      API's `Maintainer` field) is not yet implemented. (Due: Indeterminate)
- [x] **Emoji Removal**: Remove all emoji and pictographic glyphs from repository
      prose and script output. Resolved 2026-10-15. `TASKS.md` section headings now
      express completion textually (e.g. `(done)`), `scripts/check-pkgdesc-consistency.sh`
      prints `OK`/`FAIL`, and `docs/KCL-OPA-PHASE3-RENDERER-CI.md` shows `OK`/`ERR`.
      Typographic arrows (`→`) and dashes are not emoji and are out of scope.
      (Due: Indeterminate)
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

## `python-whois` Package

- [ ] **Upstream issue/PR status check**: We filed issue #325 and opened PR #326
      against `richardpenman/whois` (2026-10-16) — the lapsed `нарояци.com`
      fixture in `test/test_query.py::TestQuery::test_simple_unicode_domain`.
      Check periodically whether the PR was merged, rejected, or is going stale.
      If merged, the eventual options on our side are to keep our `--deselect`
      in `check()` as belt-and-braces, or drop it once we package a release
      containing the fix. Either way the PKGBUILD comment can gain
      `https://github.com/richardpenman/whois/issues/325` in place of the
      `python-requests` precedent it cites today. (Due: Indeterminate)

## `pkl-lsp` Package (2026-06-18)

All items below refer to `packages/pkl-lsp/` (build-from-source via GraalVM
native-image from `apple/pkl-lsp` source). The package builds and works; these
are quality improvements deferred from initial development.

### Before AUR Deployment

- [x] **`pkgctl build` chroot validation**: Completed 2026-06-19. No dependency
      resolution errors, build failures, or namcap issues.

### Native-Image Flags

- [x] **`-H:+UnlockExperimentalVMOptions`**: Added 2026-06-19. Scoped around
      `-H:+StripDebugInfo` (remains experimental). `-H:+ForeignAPISupport` removed
      (default-on in GraalVM 25.0+). Warnings reduced from 7 to expected 1-2.
- [x] **Remove dead flags**: `--no-fallback` (deprecated, no effect) and
      `-H:-ParseRuntimeOptions` (unnecessary) removed.

### Build Quality

- [x] **Tighten `-H:IncludeResources`**: Removed `'.*'`; rely on agent-generated
      `reachability-metadata.json` resources section (84 resources, 10 MiB).
      Binary: 328 MiB → 60 MiB (–82%), compressed: 107 MiB → 19 MiB (–82%).
      Build time: 5m 36s → 2m 56s (–47%).
- [x] **Verify reflection surfaces**: Fixed 2026-10-15. The old driver spawned
      the JAR as a subprocess, so the tracing agent saw only wire traffic and
      lsp4j's launcher reflection surface never executed in the traced JVM —
      0 of 565 lsp4j classes were registered, and a well-formed `initialize`
      carrying `workspaceFolders` crashed with
      `MissingReflectionRegistrationError` on `WorkspaceFolder`. Replaced with
      upstream's two-step mechanism: `RunLspAgent.java` (client and server in one
      JVM, mirroring upstream `simpleclientrunner`) plus
      `merge-lsp4j-metadata.py` (classgraph equivalent, registers every
      `org.eclipse.lsp4j` class in the fat JAR). Final metadata: 626 reflection
      entries, 5 proxies, 1 foreign, 12 resources. `run-lsp-agent.py` deleted.
- [x] **Metadata injection path**: Found and fixed 2026-10-15. native-image only
      scans `META-INF/native-image/<group>/<artifact>/*.json`; a file placed
      directly at `META-INF/native-image/reachability-metadata.json` is silently
      ignored, so the correct metadata never reached the image builder and the
      binary died on the `PklLanguageClient`/`Endpoint` proxy. Verified by probe:
      direct-child path emits no `Apply jar:...` line under `--verbose`; one- and
      two-level subdirectories both do. Recipe stages to
      `META-INF/native-image/${pkgname}/${pkgname}/` and verifies the result.
- [x] **Injection guard must not assume `unzip`**: Found 2026-10-15 in the first
      successful clean-chroot run (`pkgctl build`), which failed with
      `/startdir/PKGBUILD: line 111: unzip: command not found`. `unzip` is not in
      base-devel, so the guard could never have run for any AUR user. It also
      turned up a trap while replacing it: `jar` has no stdout-extract mode, and
      `jar --extract` exits **0 even when it matches nothing**, so its exit status
      cannot be the check. The guard now extracts to `${srcdir}/jar-verify` and
      tests for the file on disk before grepping `"proxy"` out of it. Verified in
      both directions: a bogus path leaves no file and trips the guard, and the
      real injected entry yields the expected 5 proxy entries. No extra
      `makedepends` are needed — only `jar`, `mkdir`, `rm`, `grep`.
- [x] **`--initialize-at-build-time=` removal**: The empty argument means
      *initialize all packages*; with lsp4j registered it ran `com.sun.jna`'s
      `Cleaner` static initializer at build time and failed with
      `Detected a started Thread in the image heap. Thread name: JNA Cleaner.`
      Flag removed; upstream passes neither build-time nor run-time init flags.
- [x] **Upstream bug documented**: `PklLspServer.kt:79` throws `NullPointerException`
      in `initialized()` when the client's `initialize` omits the `workspace`
      capability. Upstream Kotlin defect in tag `0.7.1`; not addressable in a
      PKGBUILD.
- [x] **Dead flag audit (`-H:+RemoveUnusedSymbols`, `-H:+ReportExceptionStackTraces`)**:
      Both closed 2026-10-15 against `native-image --expert-options-all`.
      `RemoveUnusedSymbols` is already on by default ("Default: + (enabled)").
      `ReportExceptionStackTraces` is a plain expert `-H:±` option needing no
      experimental unlock; kept on deliberately (build-time-only verbosity, no
      image impact).
- [x] **`$srcdir` leak**: Closed 2026-10-15 as cosmetic. `-H:-PathInStackTrace`
      does not exist in GraalVM 25, and `-H:±RemoveSaturatedTypeFlows` is already
      default-on. The absolute paths arrive from the **zig** toolchain's bundled
      libc headers during the tree-sitter native build
      (`.../zig-linux-amd64-0.16.0/lib/libc/include/generic-glibc/*.h`,
      `build/repos/tree-sitter`), so no native-image flag can remove them.
- [x] **`--exact-reachability-metadata` verification**: Closed 2026-10-15 as not
      applicable. All reflection entries now come from the merged agent +
      classgraph sweep (626 entries), and the broad lsp4j registration is
      deliberately non-exact: many of the 565 `org.eclipse.lsp4j` classes cannot
      be proven reachable by static analysis. Running the image builder in
      exact mode would reject exactly the registrations this fix depends on.
      For the same reason `--future-defaults=all` is declined — one of its
      sub-options is `exact-reflection`.
- [ ] **Test aarch64 build**: `sha512sums_aarch64` generated and GraalVM aarch64
      tarball exists in source array, but the build has only been tested on
      x86_64. Blocked — no ARM hardware available.

### Optimization

- [x] **Binary size**: 60 MiB unstripped / 19 MiB compressed (was 328/107 MiB).
      Primary reduction done (14d: removed `-H:IncludeResources`,
      rely on agent metadata). Secondary: `-R:MaxHeapSize=1g` caps runtime heap.
- [x] **`-H:+FullRelro`**: Added `-H:NativeLinkerOption=-Wl,-z,relro,-z,now`.
      Fixes the only namcap warning (`ELF file lacks FULL RELRO`).

### Completeness

- [x] **`check()` function**: Added 2026-09-29 as a smoke test. Upstream tests are
      JUnit 5 (Jupiter) with two custom test engines — `ParserSnippetTestEngine`
      and `DiagnosticsSnippetTestEngine` — that parse `.pkl` snippet files with
      embedded assertions from `src/test/files/`.
      Dependencies: `assertj` 3.27.7, `junit-jupiter` 6.1.0, plus a native
      Pkl CLI binary (`pklCli`, ~95 MB) downloaded as a test dependency and passed
      via `-DpklExecutable=`. Tests also require `--enable-native-access=ALL-UNNAMED`.
      Not suitable for `check()` — it requires network access for the Pkl CLI
      download and pulls heavy `checkdepends`. The recipe therefore ships the
      smoke test only (`pkl-lsp --version`); the full Gradle test suite is
      deferred to CI or manual verification.
- [x] **Update `package.json` / `package.pkl`**: Regenerated 2026-09-29 via
      `scripts/validate-pkgbuilds-pkl.sh` (now passes, exit 0). Required a
      `pkl_writer.py` fix so local helper variables such as `_graalvm_ver` are
      no longer emitted.

### GraalVM Migration

- [x] **Switch to stable GraalVM**: Migrated 2026-09-29 to `_graalvm_ver=25.4.4.1.1`
      on `graalvm/graalvm-ce-builds` (the dev tag `25.1.3-dev-20260619_0111` was
      pruned upstream and 404s). Checksums regenerated via `updpkgsums`; both
      linux tarballs verified to contain `bin/native-image`; local `makepkg`
      build succeeds and the binary reports `pkl-lsp version 0.7.1-dev+`.

## `pkl-lsp-bin` Package

The `packages/pkl-lsp-bin/` package is deferred and marked DEPRECATED in its
PKGBUILD header. It still points at a native binary release from the
`colelawrence/pkl-lsp` fork at version `0.6.0-native.20260518.5`; `_deploy_aur`
has been removed so the stale fork is never pushed to the AUR.

Upstream status (checked 2026-10-15): [issue #60](https://github.com/apple/pkl-lsp/issues/60)
closed 2026-08-04 as completed, and PR #226 "Add native executable" landed that
same hour. Releases are still unchanged — every tag through 0.8.0 ships exactly
one asset, the JAR — because `main` is 30 commits ahead of the newest tag. The
`release.yml` workflow now publishes `pkl-lsp-{linux-amd64,linux-aarch64,macos-*,
windows-amd64,alpine-linux-amd64}` alongside `build/libs/*`, so the rebase
becomes possible as soon as a release includes #226. Note that
`packages/pkl-lsp` has now backported the metadata half of #226 (see 14c), so
the source build no longer depends on waiting for it.

Metadata hygiene items below were completed 2026-09-29; the source rebase
remains blocked until Apple publishes native binaries (issue #60):

- [x] **Update maintainer format**: `pngdeity <pngdeity@tutanota.com>`.
- [x] **Add `_pkgname` variable**: `_pkgname=pkl-lsp`; `provides`/`conflicts`
      now derive from it.
- [x] **Fix `license=`**: Verified Apache-2.0 upstream.
- [ ] **Rebase to `apple/pkl-lsp`**: Switch from `colelawrence/pkl-lsp` fork to
      official `apple/pkl-lsp` releases. Blocked — releases still ship only a
      JAR through 0.8.0. When a release containing #226 appears, repoint the
      sources, add `options=('!strip')` and set `_deploy_aur=true`.

## Ready for Human (Post-Swarm 2026-05-15)

These items require human execution — chroot builds, branch management, secret
provisioning, and CI verification.

- [ ] **chroot builds — remaining packages**: Run `pkgctl build` for all packages
      in a clean chroot. Verify no build failures, dependency resolution errors,
      or namcap issues. (`pkl-lsp` 0.7.1-5 is now validated; the rest are not.)
- [x] **fix/packages-opendoas-ranger-jules disposition**: Resolved — branch
      deleted; changes absorbed into main.
- [x] **HPA rebase onto `dev`**: Cancelled — no HPA branch exists; swarm task
      was never started.
- [x] **AUR deployment (SSH auth)**: Resolved — AUR SSH auth is working and
      verified live. `amass-bin` (5.1.1-1) and `python-whois` (0.9.6-3) are
      published on the AUR, and `pkl-lsp` 0.7.1-5 was pushed manually
      2026-10-15. Note the item's premise is superseded: `scripts/aur-deploy.sh`
      cannot deploy packages whose `source[]` carries local files. `opendoas`
      `_deploy_aur` is unset for that reason, not because of auth.
- [x] **oldver.json decision**: Resolved — tracked as shared nvchecker state, its
      path declared as `oldver` in the `[__config__]` section CI synthesizes.
- [ ] **CI results review**: Check discovery workflow run on `dev` branch
      (dispatched 2026-05-15). Verify the new validation gate passes.
- [x] **build.yml workflow_dispatch trigger**: Completed — `workflow_dispatch`
      added to `build.yml` (commit `28b5e16`).
- [ ] **CI/CD maintenance burden reduction**: 12 items identified in the
      2026-06-18 CI/CD maintenance audit. Tasks are documented in
      [`TASKS.md`](../TASKS.md) at the repository root. Priorities: extract
      duplicated configuration (#1), centralize version pins (#2), add
      unknown-change guard to concern classifier (#3).
