# Autonomous Agent Swarm — Execution Plan

**Generated:** 2026-05-15 **Target Repository:** pngdeity/aur **Orchestration:**
opencode Task subagents **Total Estimated Time:** ~15 hours of agent work

---

## Repository State

**Branch:** `main` (clean, up to date with origin/main) **Packages:** 8 (11
ghost directories removed in prep)

| Package      | Current Version        | Upstream                                   |
| ------------ | ---------------------- | ------------------------------------------ |
| amass-bin    | 5.1.1-1                | 5.1.1 (current)                            |
| amass-git    | 5.1.1.r0.g79299dc-2    | 5.1.1 (current)                            |
| dnstwist     | 20250130-1             | 20250130 (current — bump pkgrel if needed) |
| jules-tools  | 0.1.42-1               | 0.1.42 (current)                           |
| opencode-git | 1.14.48.r38.gcddab63-1 | 1.15.0 (**stale**)                         |
| opendoas     | 6.8.2-1                | 6.8.2 (current)                            |
| python-whois | 0.9.6-1                | 0.9.6 (current — bump pkgrel if needed)    |
| ranger-doas  | 1.9.4-5                | 1.9.4 (current)                            |

**Available tools:** pkl (/usr/bin/pkl), conftest (/usr/bin/conftest 0.68.2),
curl, namcap, makepkg, pkgctl, nvchecker

---

## Dependency Graph

```
┌──────────────────────────────────┐
│  Batch 1 — Parallel             │
│  S1.1 opencode-git → 1.15.0    │
│  S1.2 python-whois verify       │
│  S1.3 dnstwist verify           │
│  S2    merge manifest docs      │
│  S7.1  bash-completion doc      │
│  S7.3  TESTING_ARCHITECTURE_PLAN│
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Batch 2 — Sequential           │
│  S3.1  pkgvar in sync-pkg.sh    │
│  S3.2  pkgvar in aur-deploy.sh  │
│  S3.3  pkgvar array support     │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Batch 3 — Parallel             │
│  S4.1  schemas/arch_pkg.pkl     │
│  S4.2  pkgbuild_to_pkl.py       │
│  S4.4  install-validator-tools  │
│  S7.2  SRCINFO policy doc       │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Batch 4 — Sequential           │
│  S4.3  validate-pkgbuilds-pkl.sh│
│  S4.5  import all 8 packages    │
│  S4.6  SUPERSEDED docs cleanup  │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Batch 5 — Sequential           │
│  S5.1  policies/repository.rego │
│  S5.2  policy_exceptions.yaml   │
│  S5.3  wire conftest into wrapper│
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Batch 6 — Final Integration    │
│  S6.1  output.text renderer     │
│  S6.2  pre-commit hook          │
│  S6.3  build.yml validate job   │
│  S6.4  discovery.yml gate       │
│  S7.4  slim bash-completion refs│
└──────────────────────────────────┘
```

---

## Task Specifications

### Batch 1 — Parallel (wall clock ~30 min)

#### S1.1: opencode-git → 1.15.0

- **Skill:** pkg-update
- **Command:** `bash scripts/sync-package.sh opencode-git 1.15.0`
- **Verify:** `namcap packages/opencode-git/PKGBUILD` clean
- **Verify:** `bash scripts/check-pkgdesc-consistency.sh` passes
- **Verify:** `.SRCINFO` regenerated

#### S1.2: python-whois version bump

- If already at 0.9.6, bump pkgrel:
  `sed -i 's/^pkgrel=.*/pkgrel=2/' packages/python-whois/PKGBUILD`
- **Verify:** `namcap packages/python-whois/PKGBUILD` clean
- **Verify:** `makepkg --printsrcinfo -p packages/python-whois/PKGBUILD`
  (`.SRCINFO` is gitignored per `SRCINFO-VERSION-CONTROL-POLICY.md`)

#### S1.3: dnstwist version bump

- If already at 20250130, bump pkgrel
- **Verify:** same as S1.2

#### S2: Merge manifest docs

- Merge `origin/feature/manifest-refactor` into main
- **Note:** The feature branch predates the dnstwist/python-whois hotfixes on
  main. The 3-way merge correctly preserves them (verified 2026-05-15: clean
  merge, no deletions). The `git checkout HEAD --` below is a defensive no-op.
- Command: `git merge origin/feature/manifest-refactor --no-commit --no-ff`
- Then: `git checkout HEAD -- packages/dnstwist packages/python-whois`
  (defensive no-op — git merged correctly)
- Then:
  `git commit -m "docs: merge manifest validation architecture TDDs from feature/manifest-refactor"`
- **Verify:** `git diff HEAD~1 --stat` shows only docs added — no package
  modifications or deletions

#### S7.1: Bash completion conventions

- Create `docs/BASH-COMPLETION-CONVENTIONS.md`
- Centralize `_comp_` namespace + `_comp_compgen_help` patterns
- Source: packages/doas-bash-completion/AGENTS.md and
  packages/gemini-bash-completion/AGENTS.md from `feat/auto-review` branch
- **Verify:** file exists, covers both packages

#### S7.3: TESTING_ARCHITECTURE_PLAN.md disposition

- Add
  `**Status: Reference** — retained for design rationale. No active Python refactoring is underway.`
  header to `docs/TESTING_ARCHITECTURE_PLAN.md`
- **Verify:** header present

---

### Batch 2 — Sequential (~2 hrs)

#### S3.1: pkgvar in sync-package.sh

- Replace 5 `grep | cut | tr` / `grep -oP` extraction points:
  - L176: `_upstream_arch_repo` extraction
  - L177: `_upstream_aur_pkg` extraction
  - L264: `_githubname` extraction
  - L268: `_tag` extraction
  - L273: `_github_api_version` extraction
- Replace each with: `$("$SCRIPT_DIR/pkgvar" PKGBUILD <variable_name>)`
- **Verify:** Run `sync-package.sh` on a package with `_upstream_*` set, confirm
  identical output

#### S3.2: pkgvar in aur-deploy.sh

- Replace 2 `grep` extraction points (L96, L97) with `pkgvar` calls
- **Verify:** `aur-deploy.sh --dry-run` on a deploy_aur package produces
  identical output

#### S3.3: pkgvar array support

- Extend `scripts/pkgvar` to handle Bash array variables
- Use `declare -p <var>` after sourcing to serialize arrays
- Parse `declare -p` output to extract all elements
- **Verify:** `./scripts/pkgvar packages/opendoas/PKGBUILD provides` returns all
  elements: `doas`
- **Verify:** `./scripts/pkgvar packages/opendoas/PKGBUILD conflicts` returns:
  `doas`

---

### Batch 3 — Parallel (~4 hrs)

#### S4.1: schemas/arch_pkg.pkl

- Create `schemas/` directory
- Write `schemas/arch_pkg.pkl` — full Package class
- Reference: `docs/KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md` §4.1 (complete
  implementation provided)
- Must cover:
  - 33 standard PKGBUILD(5) fields
  - 13 `hidden` custom `_`-prefixed variables
  - `SourceEntry` and `OptDependsEntry` sub-classes
  - `KnownArchitecture` and `KnownOption` typealiases
  - Regex constraints on `pkgname` and `_githubname`
  - `Number(this > 0)` on `pkgrel`
  - `packageFunc` (not `package` — Pkl reserved word)
  - `output.text` renderer (also satisfies S6.1)
- **Verify:** `pkl eval schemas/arch_pkg.pkl` exits 0 (validates the module
  itself)

#### S4.2: scripts/pkgbuild_to_pkl.py

- PKGBUILD → Pkl import script
- Spawn `bash -c 'source PKGBUILD; declare -p; declare -f'` subprocess
- Parse declare output into Python dict
- Emit `amends "schemas/arch_pkg.pkl"` module
- Handle: `package` → `packageFunc` keyword mapping, `SourceEntry` filename::url
  split, multiline `"""..."""` strings, float pkgrel
- Reference: `docs/KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md` §5.4 for output format
- **Verify:**
  `python3 scripts/pkgbuild_to_pkl.py packages/opendoas/PKGBUILD > /tmp/opendoas.pkl && pkl eval /tmp/opendoas.pkl --format json`
  exits 0
- **Note:** Import logic is now split: `pkgbuild_loader.py` (loading, bash
  subprocess, parsing) + `pkl_writer.py` (Pkl formatting) + `pkgbuild_to_pkl.py`
  (thin orchestrator).

#### S4.4: scripts/install-validator-tools.sh

- `yay -S pkl-bin` and `yay -S conftest` are already installed at system level
- Script should verify: `which pkl && which conftest` and print versions
- If missing, attempt: `yay -S --noconfirm pkl-bin conftest`
- **Verify:** `bash scripts/install-validator-tools.sh` exits 0, prints versions

#### S7.2: SRCINFO policy document

- Create `docs/SRCINFO-VERSION-CONTROL-POLICY.md`
- Analyze: pro (already generated by aur-deploy.sh, desync is recurring chore),
  con (AUR helpers consume from AUR git, CI gates check presence)
- Recommendation with rationale
- **Verify:** file exists with clear recommendation

---

### Batch 4 — Sequential (~3 hrs)

#### S4.3: scripts/validate-pkgbuilds-pkl.sh

- Orchestration wrapper
- Find all PKGBUILDs → import via pkgbuild_to_pkl.py → `pkl eval --format json`
  → merge to manifest.json
- Exit 0 on success, 1 on validation failure, 2 on missing prerequisites
- Reference: `docs/KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md` §6.2
- **Verify:** `bash scripts/validate-pkgbuilds-pkl.sh` discovers 8 packages,
  exits 0

#### S4.5: Import all 8 packages

- Run validate-pkgbuilds-pkl.sh
- Each package must produce valid JSON from `pkl eval --format json`
- **Verify:** 8 packages discovered, 8 validated, 0 failures

#### S4.6: SUPERSEDED headers on KCL/CUE docs (post-merge)

- After Batch 1 S2 merges the manifest docs, these files will exist:
  - `docs/KCL-OPA-PHASE1-SCHEMA-DESIGN.md`
  - `docs/KCL-OPA-PHASE1-CUE-SCHEMA-DESIGN.md`
  - `docs/KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md`
- Add to KCL/CUE schema docs:
  `**Status: SUPERSEDED by Pkl.** See PKL-CROSS-PHASE-EVALUATION.md. Retained as rationale artifact only. **Do not implement from this document.**`
- Add to master plan line 1:
  `**Note:** Pkl selected as schema language per PKL-CROSS-PHASE-EVALUATION.md. KCL references in this document are historical.`
- **Verify:** headers present

---

### Batch 5 — Sequential (~3 hrs)

#### S5.1: policies/repository.rego

- Create `policies/` directory
- Write `policies/repository.rego` — 12 OPA rules
- Reference: `docs/KCL-OPA-PHASE2-POLICY-ENGINE.md` §3 (full Rego
  implementations provided)
- Rules: enforce_https, privilege_escalation, architecture_mismatch,
  no_unprovided_conflicts, no_self_reference, deploy_aur_subarch_mutex,
  pkgdesc_consistency, valid_architectures, required_fields, source_integrity,
  vcs_skip, deny_missing_maintainer
- **Verify:** `conftest test` against the manifest from S4.5 produces results
  (not just errors about missing package data)

#### S5.2: policy_exceptions.yaml

- Create `packages/<name>/policy_exceptions.yaml` for packages that have
  justified violations
- Each file: `exceptions: [{rule: "<name>", reason: "..."}]`
- Known exceptions:
  - `amass-bin`: vcs_skip (binary package, no VCS sources)
  - `amass-git`: vcs_skip (git source, has SKIP checksums per VCS guidelines)
  - `opencode-git`: vcs_skip (git source, has SKIP checksums)
  - `opendoas`: vcs_skip (VCS source, uses git+ with concrete hashes per tagged
    release). privilege_escalation — VERIFY FIRST: check `change-PATH.patch` and
    PKGBUILD for sudo/setuid references before creating exception. If none
    found, do NOT create privilege_escalation exception.
- **Verify:** conftest test with exceptions suppresses only the registered rules

#### S5.3: Wire conftest into validate wrapper

- Update `scripts/validate-pkgbuilds-pkl.sh` to invoke `conftest test` after
  `pkl eval`
- Pass per-package exceptions via `--data` flags or merged JSON
- **Verify:** `bash scripts/validate-pkgbuilds-pkl.sh` runs full pipeline:
  import → pkl → conftest

---

### Batch 6 — Final Integration (~2 hrs)

#### S6.1: output.text renderer in arch_pkg.pkl

- Already included in S4.1's `schemas/arch_pkg.pkl`
- The `renderPKGBUILD()` method + `output.text` block
- Maps: `packageFunc` → `package()` in output
- Field ordering per Phase 3 TDD §2.4
- **Verify:**
  `pkl eval schemas/arch_pkg.pkl -p packages/opendoas/package.pkl > /tmp/test.PKGBUILD && bash -n /tmp/test.PKGBUILD`
  passes syntax check

#### S6.2: Pre-commit hook

- Add `pkl-validate` hook to `.pre-commit-config.yaml` (create file if not
  exists)
- Entry: `bash scripts/validate-pkgbuilds-pkl.sh`
- Trigger: `^packages/.*/(PKGBUILD|package\.pkl)$`
- **Verify:** YAML syntactically valid

#### S6.3: build.yml validate job

- Add `validate` job to `.github/workflows/build.yml` before `execute`
- Runs on `ubuntu-latest` (not builder container)
- Installs pkl + conftest, runs validate-pkgbuilds-pkl.sh
- `execute` job gets `needs: validate`
- **Verify:** YAML syntactically valid, conditional logic traceable

#### S6.4: discovery.yml gate

- Add Pkl validation gate to `.github/workflows/discovery.yml`
- After existing pkgdesc check, before `git push`
- Failure blocks the push with `::error::`
- **Verify:** YAML syntactically valid

#### S7.4: Slim bash-completion AGENTS.md references

- After Batch 1 S7.1 creates the centralized doc
- **Note:** Bash-completion packages (`doas-bash-completion`,
  `gemini-bash-completion`) exist only on `feat/auto-review`, not on `main`. If
  no bash-completion AGENTS.md files exist on main, this task is a no-op —
  report "nothing to update" and pass.
- If per-package AGENTS.md files exist for bash-completion packages, update them
  to reference the centralized doc
- **Verify:** references point to `docs/BASH-COMPLETION-CONVENTIONS.md`

---

## Verification Summary

| Batch | Key Verification                                                      | Severity if Fails                                 |
| ----- | --------------------------------------------------------------------- | ------------------------------------------------- |
| 1     | `namcap` clean, `.SRCINFO` regenerated, no package deletions in merge | ERROR — fix before continuing                     |
| 2     | `diff` before/after pkgvar adoption identical                         | WARN — continue if output is functionally correct |
| 3     | `pkl eval --format json` exits 0 for all 8 packages                   | ERROR — fix schema before OPA rules               |
| 4     | Full pipeline: import → pkl → conftest exits 0                        | ERROR — fix before CI integration                 |
| 5     | OPA rules produce expected violations, exceptions suppress correctly  | ERROR — fix before CI integration                 |
| 6     | `bash -n` passes on rendered output, YAML valid                       | WARN — human needs to verify in live CI           |

---

## Fallback Instructions

| Failure                                       | Response                                                                                                                                                  |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `updpkgsums` fails (unreachable source)       | Verify source URL is reachable. If 404, flag for human — possible re-rolled release.                                                                      |
| `namcap` warnings                             | Evaluate each warning. Package-specific exceptions may justify ignoring.                                                                                  |
| Merge conflict on S2                          | Abort merge (`git merge --abort`), report the conflicting files, skip S2 and continue with other tasks.                                                   |
| `pkl eval` fails on a package                 | Read the error message. If schema issue, fix `schemas/arch_pkg.pkl`. If import issue, fix `pkgbuild_loader.py`, `pkl_writer.py`, or `pkgbuild_to_pkl.py`. |
| `conftest test` unexpected violations         | Read violation. If rule is correct, create exception in `policy_exceptions.yaml`. If rule is wrong, fix the Rego.                                         |
| Subagent (Task tool) returns empty/incomplete | Re-run that specific task. Check the subagent's verification output.                                                                                      |

---

## Progress Report Format

After all batches complete, produce a summary:

```
## Swarm Execution Report — 2026-05-16

### Completed
- [x] S1.1: opencode-git → 1.15.0 (namcap clean, .SRCINFO regenerated)
- [x] S1.2: python-whois verified (pkgrel bumped to 2)
...

### Skipped
- [ ] S2: merge conflict on docs/KCL-OPA-PHASE2-POLICY-ENGINE.md — needs human

### Failed
- [ ] S5.1: conftest test produces 3 unexpected violations — needs human review

### Ready for Human
1. pkgctl build (chroot) — 8 packages
2. Live CI trigger — push to test dev branch
3. Dev branch creation + merge strategy
4. fix/packages-opendoas-ranger-jules disposition
5. HPA rebase onto dev
6. AUR deployment (SSH auth)
7. nvc_versions.json decision (commit or gitignore)
```
