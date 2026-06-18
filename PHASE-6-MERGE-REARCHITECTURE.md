# Phase 6 Implementation: Merge Rearchitecture + Retire Dead Code

Five implementation chunks. Chunks 1–2 are the riskiest (new Pkl, untested merge logic); Chunks 3–5 are mechanical. Chunk 6 (Phase 6.1: delete scripts) is a separate session.

**Phase 2 absorption**: Phase 2 (hand-authored `.pkl` files) was skipped — `write_pkl_module()` regenerates `.pkl` from flat dicts on every sync, vaporizing hand-authored constructs. This merge rearchitecture achieves the same goal: the merge function generates `.pkl` from typed `Package` objects with full structural fidelity, equivalent to hand-authoring. No separate hand-authoring phase is needed.

## Dependency Graph

```
Chunk 1 (merge.pkl)
    ↓
Chunk 2 (tests) ← can develop in parallel after Chunk 1 body complete
    ↓
Chunk 3 (refactor _load_pkl)
    ↓
Chunk 4 (bridge + delete dead code) ← tests must pass first
    ↓
Chunk 5 (smoke test + import cleanup)
    ↓
Chunk 6 (retire dead scripts)
```

---

---

## Design Decisions (Resolved — Confirm Before Implementing Chunk 1)

**D1: `_auto_merge_build` gate** — **CONFIRMED: gated.**  
Build-function diffs only set `_prereview` when `ours._auto_merge_build == false`.  
If `_auto_merge_build` is true, build changes merge silently (no PREREVIEW marker).  
Matches current `_apply_prereview_marker` behavior (`sync-package.py:275-285`).  
Rationale: packages with `_auto_merge_build=true` (e.g., `go-regal-bin`) trust upstream
build logic; spurious markers would break their CI/CD automation.

**D2: `_demote_upstream_maintainer`** — **CONFIRMED: gated.**  
Upstream maintainer appended to `contributor` only when `ours._demote_upstream_maintainer == true`.  
Otherwise upstream maintainer is dropped (schema's `maintainer` is a single `String` —  
cannot hold two maintainers; ours always wins).  
Matches current `_merge_with_identity` behavior (`sync-package.py:248`).  
Rationale: the flag's purpose is to opt in to upstream-author credit preservation.

**D3: Identity-field semantics change** — **CONFIRMED: accept the change.**  
`pkgver`, `pkgrel`, `source`, `pkgverFunc` move from always-ours (via current  
`_IDENTITY_FIELDS`) to 3-way pick in the new merge.  
`_bump_version` overwrites `pkgver` afterward anyway, so upstream version flows are  
harmless. `source` URL changes from upstream now flow through (improvement — current  
code blocks them). `pkgverFunc` changes affect `-git` packages (`amass-git`,  
`apm-go-git`, `opencode-git`).  
Rationale: the new design is more correct — upstream changes to these fields should  
be visible for downstream processing, not silently discarded.

---

## Chunk 1: `schemas/merge.pkl` — The Typed Merge Core

New file. Approximately 400 lines of Pkl (grew beyond initial 150-line estimate due to module-level helper functions `_dataConflicts`/`_buildConflict`/`_prereviewText`, per-function `when` generators for all build functions, and detailed documentation).

### Data Types

```pkl
class ChangeSet {
  events: Listing<String>
  buildChanged: Boolean
}
```

No reflection needed at runtime — each concern group compares its fields at compile time.

### `classifyChanges(base: Package, theirs: Package) -> ChangeSet`

Fixed concern groups with direct field comparisons:

```
IDENTITY:    base.pkgname != theirs.pkgname OR base.provides != theirs.provides OR
             base.conflicts != theirs.conflicts OR base.replaces != theirs.replaces
VERSION:     base.pkgver != theirs.pkgver OR base.pkgrel != theirs.pkgrel OR
             base.epoch != theirs.epoch
METADATA:    base.pkgdesc != theirs.pkgdesc OR base.url != theirs.url OR
             base.license != theirs.license OR base.arch != theirs.arch OR
             base.backup != theirs.backup OR base.install != theirs.install OR
             base.options != theirs.options
DEPENDS:     base.depends != theirs.depends
MAKEDEPENDS: base.makedepends != theirs.makedepends
CHECKDEPENDS: base.checkdepends != theirs.checkdepends
OPTDEPENDS:  base.optdepends != theirs.optdepends
SOURCES:     base.source != theirs.source OR base.sha256sums != theirs.sha256sums OR
             base.sha512sums != theirs.sha512sums OR base.sha224sums != theirs.sha224sums OR
             base.sha384sums != theirs.sha384sums OR base.b2sums != theirs.b2sums OR
             base.source_x86_64 != theirs.source_x86_64 OR
             base.source_aarch64 != theirs.source_aarch64 OR
             base.sha512sums_x86_64 != theirs.sha512sums_x86_64 OR
             base.sha512sums_aarch64 != theirs.sha512sums_aarch64
BUILD:       base.verify != theirs.verify OR base.pkgverFunc != theirs.pkgverFunc OR
             base.prepare != theirs.prepare OR base.build != theirs.build OR
             base.check != theirs.check OR base.packageFunc != theirs.packageFunc
AUTHORSHIP:  base.maintainer != theirs.maintainer OR
             base.contributor != theirs.contributor
```

Returns `ChangeSet { events = ["VERSION", "METADATA"]; buildChanged = false }` for a typical upstream update.

### `merge(ours: Package, base: Package, theirs: Package) -> Package`

Returns `(ours) { ... }` — the idiomatic Pkl "copy with overrides" pattern. Starts from
`ours` (so all "always ours" identity fields are correct by construction — zero
assignments) and uses `when` clauses to override only the fields where `theirs`
wins a 3-way comparison. The `Package` class has no `fixed` data properties, so
all fields are overridable. Three resolution rules:

| Rule | Applies to | Logic |
|---|---|---|
| **Always ours** | `pkgname`, `provides`, `conflicts`, `replaces`, `maintainer`, and all `_`-prefixed control vars (`_deploy_aur`, `_repo_subarch`, `_upstream_*`, `_githubname`, `_tag`, `_npm*`, `_name`, `_projectname`, `_sourcedirectory`, `_github_api_version`, `_auto_merge_build`, `_demote_upstream_maintainer`, `_use_common_gemini_settings`, `_pkgname`) | Already correct in `ours` — no override needed |
| **3-way pick** | `pkgver`, `pkgrel`, `epoch`, `pkgdesc`, `url`, `license`, `arch`, `depends`, `makedepends`, `checkdepends`, `optdepends`, `source`, `source_x86_64`, `source_aarch64`, all `*sums*`, `validpgpkeys`, `noextract`, `install`, `backup`, `options`, `groups`, `changelog`, `pkgbase` | `when (ours.f == base.f && theirs.f != base.f) { f = theirs.f }` — only emit an override where theirs wins. No override when we changed it (ours != base) — our change is preserved |
| **Authorship** | `contributor` | `when (ours._demote_upstream_maintainer)` → append upstream maintainer to `contributor`; otherwise upstream maintainer is dropped (schema's `maintainer` is single-string, ours always wins) |

Build functions (`prepare`, `build`, `check`, `pkgverFunc`, `packageFunc`, `verify`):
use rule 2 (3-way pick) but additionally set `_prereview` when the function body
differs between ours and theirs — **gated on `!_auto_merge_build`**. If
`_auto_merge_build` is true, build-function changes merge silently without a
PREREVIEW marker, matching the current `_apply_prereview_marker` behavior
(`sync-package.py:275-285`).

Conflict detection (both ours and theirs changed from base, for any 3-way-pick
field) also sets `_prereview = "upstream conflicts: <field names>"`. The data-field
and build-function `_prereview` strings are distinct for legibility.

The body is ~30 `when` blocks — one per 3-way-pick field + 5 build-function
blocks + conflict-detection logic. No `new Package` reconstruction, no risk of
omitting a required field, and idiomatic Pkl (amends is the canonical "copy with
overrides" pattern per the Pkl language reference §Amending Objects).

### Verified Against Pkl 0.31.1 Language Reference

External documentation research confirms:

- **Module-level functions** are supported (LR §Methods): *"Pkl methods can be defined on classes and modules using the `function` keyword."* Modules are regular objects; importing a module exposes its members. `merge.merge(...)` resolves correctly.
- **`==`/`!=` structural equality** works as assumed (LR §Properties): `"Objects that differ only in hidden property values are considered equal."` `arch_pkg.pkl` has no hidden data fields, so all fields participate. `Listing` equality is order-sensitive.
- **No built-in 3-way merge/diff**: Only `+` on `Map` (right-biased) and `amends` (2-way prototypical inheritance). `merge.pkl` is novel, not reinventing.
- **`pkl:test` is snapshot-based**, not assertion-based (CLI docs). See Chunk 2 redesign note.

### Edge Cases

- **Missing fields**: if a field exists in `base` but not `theirs` (or vice versa), treat the absent value as equal to the present one — the `!=` comparison catches the difference.
- **Null vs empty Listing**: `null != new {}`. The `!=` operator on Pkl objects handles structural equality correctly.
- **`_prereview` format**: `"upstream build functions changed (see diff)"` for build-function conflicts (gated on `!_auto_merge_build`); `"upstream conflicts: <field names>"` for data-field conflicts. The shell no longer needs `_apply_prereview_marker()`.
- **`_auto_merge_build` gate** (D1): build-function diffs only set `_prereview` when `ours._auto_merge_build == false`. Matches current `sync-package.py:275-285` behavior.
- **`_demote_upstream_maintainer` gate** (D2): upstream maintainer demoted to contributor only when `ours._demote_upstream_maintainer == true`. Otherwise dropped (schema's `maintainer` is single-string). Matches current behavior (`sync-package.py:248`).
- **Identity semantics change** (D3): `pkgver`, `pkgrel`, `source`, `pkgverFunc` move from always-ours (current `_IDENTITY_FIELDS`) to 3-way pick. Upstream source/version changes now flow through; `_bump_version` overwrites `pkgver` afterward. Affects `-git` packages (`amass-git`, `apm-go-git`, `opencode-git`) which carry `pkgverFunc`.

### Chunk 1 Verification (pkl eval -x)

1. `pkl eval schemas/merge.pkl` — parses and type-checks (no `output` block needed).
2. Smoke script in `/tmp/opencode/smoke.pkl`: imports `merge.pkl` + three hand-built
   `pkg.Package` literals (base/theirs/ours). Then verify via `pkl eval -x`:
   - `merge.merge(ours, base, theirs).pkgver` → theirs.pkgver (bump case)
   - `merge.merge(ours, base, theirs).pkgname` → ours.pkgname (identity protection)
   - `merge.merge(ours, base, theirs)._prereview` → null (no conflicts) / set (conflict)
   - `classifyChanges(base, theirs).buildChanged` → expected boolean
3. Confirm JSON output passes through `_json_to_vars_funcs()` shape (Chunk 3/4 compat).
4. Full fixture suite is Chunk 2 (out of scope).

---

## Chunk 2: Pkl Unit Tests for merge.pkl — REDESIGN REQUIRED

**Prefatory note**: External documentation research confirms `pkl:test` is an
**example/snapshot** framework, not assertion-based. CLI docs: *"The module must
extend `pkl:test`"* and uses `examples { ["name"] { expr } }` blocks whose rendered
output is compared against committed `pkl-expected.pcf` files. "Tests that result
in writing `pkl-expected.pcf` files are considered failing tests."

The original design below (assertion-based, running `pkl test` directly on
`merge.pkl`) is incorrect on two counts: (1) `merge.pkl` is a library module, not
a test module — `pkl test` requires `extends "pkl:test"`; (2) `pkl:test` has no
`assertEqual` or similar assertion API — it snapshots rendered output.

**Revised approach for Chunk 2** (to be finalized during implementation):

Create `schemas/merge_test.pkl` that `amends "pkl:test"`, imports `merge.pkl`,
and defines `examples { ... }` blocks that call `merge()` / `classifyChanges()`
and expose the relevant property values. Example:

```pkl
amends "pkl:test"
import "merge.pkl" as merge
import "test-fixtures/pkg-base.pkl"

examples {
  ["pkgver bump"] { merge.merge(ours, base, theirs).pkgver }
  ["identity protection"] { merge.merge(ours, base, theirs).pkgname }
}
```

Run with `pkl test schemas/merge_test.pkl`. First run generates
`pkl-expected.pcf` files; subsequent runs compare against them. Committed
`.pcf` files make regressions visible in code review.

Fixture packages in `schemas/test-fixtures/` — minimal `.pkl` files importing `arch_pkg.pkl`:

```
schemas/test-fixtures/
  pkg-base.pkl          # Package with pkgname="test", pkgver="1.0", pkgrel=1
  pkg-bump.pkl          # Same but pkgver="1.1"
  pkg-build-diff.pkl    # Same but build function body differs
  pkg-desc-conflict.pkl # pkgdesc="C" (conflicting change)
  pkg-name-diff.pkl     # pkgname="other" (identity field — must be ignored)
  pkg-new-maintainer.pkl # Different maintainer + _demote_upstream_maintainer=true
  pkg-new-depends.pkl   # Adds depends=["foo"]
```

| Test | Scenario | Expected merge result |
|---|---|---|
| `no-change` | base == theirs | ours unchanged |
| `pkgver-bump` | base.pkgver="1.0", theirs.pkgver="1.1" | merged.pkgver="1.1" |
| `build-changed` | base.build != theirs.build | merged has `_prereview` set; ours.build kept |
| `build-changed-auto-merge` | base.build != theirs.build, _auto_merge_build=true | merged.build = theirs.build; `_prereview` null |
| `desc-conflict` | base.pkgdesc="A", ours.pkgdesc="B", theirs.pkgdesc="C" | ours.pkgdesc="B"; `_prereview` set |
| `identity-protection` | theirs.pkgname="different" | merged.pkgname = ours.pkgname (unchanged) |
| `maintainer-demotion` | theirs has new maintainer, _demote_upstream_maintainer=true | new maintainer appended to contributor; ours.maintainer kept |
| `no-demotion` | theirs has new maintainer, _demote_upstream_maintainer=false | upstream maintainer dropped; ours.maintainer kept |
| `new-depends` | base.depends=[], theirs.depends=["foo"] | merged.depends=["foo"] (taken from theirs) |
| `our-change-preserved` | ours.pkgdesc="ours-only", base.pkgdesc="base", theirs.pkgdesc="base" | merged.pkgdesc="ours-only" (our change, upstream didn't touch) |
| `classify-pkgver-bump` | base vs bump fixture | `events.contains("VERSION") == true` |
| `classify-build-changed` | base vs build-diff fixture | `buildChanged == true` |
| `classify-build-event` | base vs build-diff fixture | `events.contains("BUILD") == true` |

---

## Chunk 3: Extract `_json_to_vars_funcs()` Helper

Refactor `_load_pkl()` in `scripts/sync-package.py` (current definition at lines 92–128). Extract the JSON→tuple conversion from the function body so the merge bridge can reuse it:

```python
def _json_to_vars_funcs(data: dict) -> tuple[dict, dict]:
    """Convert Pkl JSON output to (vars_, funcs) tuple.

    Splits function body keys from the flat JSON dict, renames
    pkgverFunc→pkgver / packageFunc→package, and strips schema-default
    booleans that the loader would only capture when true.
    """
    funcs: dict = {}
    for pkl_key, bash_key in [
        ("verify", "verify"),
        ("pkgverFunc", "pkgver"),
        ("prepare", "prepare"),
        ("build", "build"),
        ("check", "check"),
        ("packageFunc", "package"),
    ]:
        if pkl_key in data:
            funcs[bash_key] = data.pop(pkl_key)

    for key in (
        "_auto_merge_build",
        "_demote_upstream_maintainer",
        "_use_common_gemini_settings",
    ):
        if data.get(key) is False:
            del data[key]

    return data, funcs


def _load_pkl(pkg_dir: Path) -> tuple[dict, dict]:
    """Load a package's package.pkl via pkl eval --format json."""
    result = subprocess.run(
        ["pkl", "eval", str(pkg_dir / "package.pkl"), "--format", "json"],
        capture_output=True,
        text=True,
    )
    return _json_to_vars_funcs(json.loads(result.stdout))
```

No behavioral change — existing `_load_pkl()` callers are unaffected.

---

## Chunk 4: Wire the Bridge + Delete Dead Code

### 4a. Replace the merge path in `main()`

Replace lines 490–510 of `scripts/sync-package.py` (the `if fetched and changed and cache.exists():` block — classify, fetch assets, merge_with_identity, prereview marker) with:

```python
if fetched and changed and cache.exists():
    _log("  -> Upstream PKGBUILD changed, classifying and merging via Pkl...")

    # Parse upstream PKGBUILDs (unavoidable bash — raw text from internet)
    from pkgbuild_loader import load_pkgbuild  # inline — only for raw upstream text
    old_vars, old_funcs = load_pkgbuild(str(pkg_dir / ".PKGBUILD.upstream"))
    new_vars, new_funcs = load_pkgbuild(str(pkg_dir / "PKGBUILD.new"))

    # Download new upstream assets before merge
    _fetch_assets((pkg_dir / "PKGBUILD.new").read_text(), base_url, pkg_dir)

    # Write upstream dicts as temporary .pkl files
    # `write_pkl_module` is already imported at sync-package.py line 28
    (pkg_dir / ".upstream.base.pkl").write_text(
        write_pkl_module(old_vars, old_funcs)
    )
    (pkg_dir / ".upstream.new.pkl").write_text(
        write_pkl_module(new_vars, new_funcs)
    )

    # Generate one-shot merge script
    merge_script = (
        'import "package.pkl" as ourMod\n'
        'import ".upstream.base.pkl" as baseMod\n'
        'import ".upstream.new.pkl" as newMod\n'
        'import "../../schemas/merge.pkl" as merge\n'
        '\n'
        'output {\n'
        '  value = merge.merge(ourMod.output.value, baseMod.output.value, newMod.output.value)\n'
        '}\n'
    )
    (pkg_dir / ".merge.script.pkl").write_text(merge_script)

    # Run Pkl merge
    result = subprocess.run(
        ["pkl", "eval", str(pkg_dir / ".merge.script.pkl"), "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    vars_, funcs = _json_to_vars_funcs(json.loads(result.stdout))

    # Update cache with new upstream content
    old_cache = pkg_dir / ".PKGBUILD.upstream"
    old_cache.unlink(missing_ok=True)
    (pkg_dir / "PKGBUILD.new").rename(old_cache)

    # Clean up temp Pkl files
    for name in (".upstream.base.pkl", ".upstream.new.pkl", ".merge.script.pkl"):
        (pkg_dir / name).unlink(missing_ok=True)

    upstream_changed = True
```

### 4b. Delete dead functions and constants

Remove from `sync-package.py`:

| Item | Lines (approx) |
|---|---|
| `_IDENTITY_FIELDS` tuple | 34–42 |
| `_CONCERN_GROUPS` dict | 44–62 |
| `_classify_changes()` | 134–145 |
| `_merge_with_identity()` | 224–272 |
| `_apply_prereview_marker()` | 275–285 |
| **Total** | ~92 |

### 4c. Retained upstream parsing

Two `load_pkgbuild()` calls remain — one for the cached upstream, one for the newly fetched upstream. These parse raw PKGBUILD text from the internet. Both are inside the merge bridge block (not at module level).

---

## Chunk 5: Smoke Test + Import Cleanup

### 5a. Smoke test

1. **Baseline sync** — run on a package with `_upstream_aur_pkg` that has no upstream changes:
   ```
   python scripts/sync-package.py amass-bin 0.0.0
   ```
   Expected: "Upstream PKGBUILD unchanged." — merge path not triggered.
   (Use an impossible version `0.0.0` so `_bump_version` doesn't change pkgver.)

2. **Simulated upstream change** — manually edit `.PKGBUILD.upstream` to change `pkgdesc`, then run sync again:
   ```
   python scripts/sync-package.py amass-bin 0.0.0
   ```
   Expected: Pkl merge picks up the change, merged `pkgdesc` reflects upstream value, no conflict markers, no crash.

3. **Identity protection** — manually edit `.PKGBUILD.upstream` to change `pkgname`, run sync. Expected: merged package retains original `pkgname`.

4. **Compare output** — diff the generated PKGBUILD against the current on-disk PKGBUILD (baseline sync). Should be identical except for checksum recency.

### 5b. Import cleanup

Remove `from pkgbuild_loader import load_pkgbuild` at module level. Replace with inline import inside the merge bridge:

```python
if fetched and changed and cache.exists():
    from pkgbuild_loader import load_pkgbuild  # inline — only for raw upstream text
    old_vars, old_funcs = load_pkgbuild(...)
    new_vars, new_funcs = load_pkgbuild(...)
```

The module-level import removal makes the remaining dependency explicit and documentable.

### 5c. Update TODO.md

Mark items 6.0.1–6.0.7 as complete. Verify the structural comparison (`_load_pkl()` == `load_pkgbuild()`, 24/24) still passes — the merge output passes through `_json_to_vars_funcs()`, which is the same converter used by `_load_pkl()`.

---

## Chunk 6: Retire Dead Scripts (Phase 6.1)

Separate session — validate end-to-end pipeline after deletions.

| Script | Lines | Action | Verification |
|---|---|---|---|
| `pkgbuild_renderer.py` | 149 | Delete | `sync-package.py` no longer imports it (since Phase 3). `compare-renderers.py` must also be deleted (depends on it) |
| `compare-renderers.py` | 86 | Delete | Depends on deleted `pkgbuild_renderer.py` |
| `pkgbuild_loader.py` | 492 → ~350 | Shrink — remove module-level import; keep only bash-sourcing and parsing functions (used by the 2 upstream parse calls in the merge bridge) |
| `pkgvar` (bash) | 104 | Delete — after `aur-deploy.py` refactored to use `pkl eval --format json` for pkgver/pkgrel resolution; currently invoked at lines 187–188 |
| `sync-package.sh` (bash) | 317 | Delete | Already replaced by `sync-package.py`. `discovery.yml` and `build.yml` already updated |
| `merge_policy_exceptions.py` | 56 | Delete | Replace with `manifest.pkl` (Phase 5 dependency — may need to wait) |
| `validate-pkgbuilds-pkl.py` | ~100 remaining | Shrink — remove `build_manifest()`; becomes thin CLI wrapper calling `pkl eval manifest.pkl` |

Net reduction: ~1,300 lines deleted, ~180 lines added. 13 scripts → 6 scripts.
