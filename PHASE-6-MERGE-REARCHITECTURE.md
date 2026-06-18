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

## Chunk 1: `schemas/merge.pkl` — The Typed Merge Core

New file. Approximately 150 lines of Pkl.

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
BUILD:       base.prepare != theirs.prepare OR base.build != theirs.build OR
             base.check != theirs.check OR base.package != theirs.package OR
             base.pkgver != theirs.pkgver OR base.verify != theirs.verify
AUTHORSHIP:  base.maintainer != theirs.maintainer OR
             base.contributor != theirs.contributor
```

Returns `ChangeSet { events = ["VERSION", "METADATA"]; buildChanged = false }` for a typical upstream update.

### `merge(ours: Package, base: Package, theirs: Package) -> Package`

Constructs a new `Package` object field by field. Three resolution rules cover every field:

| Rule | Applies to | Logic |
|---|---|---|
| **Always ours** | `pkgname`, `provides`, `conflicts`, `replaces`, `_deploy_aur`, `_repo_subarch`, `_upstream_aur_pkg`, `_upstream_arch_repo`, `_githubname`, `_tag`, `_*scope`, `_npmname`, `_npmver`, `_name`, `_projectname`, `_sourcedirectory`, `_github_api_version`, `_auto_merge_build`, `_demote_upstream_maintainer`, `_use_common_gemini_settings` | `ours.field` |
| **3-way pick** | `pkgver`, `pkgrel`, `epoch`, `pkgdesc`, `url`, `license`, `arch`, `depends`, `makedepends`, `checkdepends`, `optdepends`, `source`, `source_x86_64`, `source_aarch64`, `sha256sums`, `sha512sums`, `sha224sums`, `sha384sums`, `b2sums`, `sha512sums_x86_64`, `sha512sums_aarch64`, `validpgpkeys`, `noextract`, `install`, `backup`, `options`, `groups`, `changelog`, `pkgbase` | `ours == base AND theirs != base` → theirs; `ours != base AND theirs == base` → ours; both changed → ours + set `_prereview` |
| **Authorship** | `maintainer`, `contributor` | `ours.maintainer`; upstream maintainer(s) appended to contributor list |

Build functions (`prepare`, `build`, `check`, `pkgverFunc`, `packageFunc`, `verify`) use rule 2 but additionally set `_prereview` when the function body differs between ours and theirs.

The output is a `new Package { ... }` object literal with approximately 50 field lines. Verbose but straightforward — each field is a conditional expression or direct assignment. No loops, no reflection, no runtime indirection.

### Edge Cases

- **Missing fields**: if a field exists in `base` but not `theirs` (or vice versa), treat the absent value as equal to the present one — the `!=` comparison catches the difference.
- **Null vs empty Listing**: `null != new {}`. The `!=` operator on Pkl objects handles structural equality correctly.
- **`_prereview` format**: set to `"upstream build functions changed (see diff)"` for build-function conflicts; set to `"upstream conflicts: <field names>"` for data-field conflicts. The shell no longer needs `_apply_prereview_marker()`.

---

## Chunk 2: Pkl Unit Tests for merge.pkl

Fixture packages in `schemas/test-fixtures/` — minimal `.pkl` files importing `arch_pkg.pkl`:

```
schemas/test-fixtures/
  pkg-base.pkl         # Package with pkgname="test", pkgver="1.0", pkgrel=1
  pkg-bump.pkl         # Same but pkgver="1.1"
  pkg-build-diff.pkl   # Same but build function body differs
  pkg-desc-conflict.pkl # pkgdesc="C" (conflicting change)
  pkg-name-diff.pkl    # pkgname="other" (identity field — must be ignored)
  pkg-new-maintainer.pkl # Different maintainer (must be demoted)
  pkg-new-depends.pkl  # Adds depends=["foo"]
```

| Test | Scenario | Expected merge result |
|---|---|---|
| `no-change` | base == theirs | ours unchanged |
| `pkgver-bump` | base.pkgver="1.0", theirs.pkgver="1.1" | merged.pkgver="1.1" |
| `build-changed` | base.build != theirs.build | merged has `_prereview` set; ours.build kept |
| `desc-conflict` | base.pkgdesc="A", ours.pkgdesc="B", theirs.pkgdesc="C" | ours.pkgdesc="B"; `_prereview` set |
| `identity-protection` | theirs.pkgname="different" | merged.pkgname = ours.pkgname (unchanged) |
| `maintainer-demotion` | theirs has new maintainer | new maintainer appended to contributor; ours.maintainer kept |
| `new-depends` | base.depends=[], theirs.depends=["foo"] | merged.depends=["foo"] (taken from theirs) |
| `our-change-preserved` | ours.pkgdesc="ours-only", base.pkgdesc="base", theirs.pkgdesc="base" | merged.pkgdesc="ours-only" (our change, upstream didn't touch) |

Test framework: Pkl's built-in test functions. Run with `pkl test schemas/merge.pkl`. Each test creates 3 `Package` objects from the fixtures, calls `merge()`, and asserts specific field values.

---

## Chunk 3: Extract `_json_to_vars_funcs()` Helper

Refactor `_load_pkl()` in `sync-package.py` — extract the JSON→tuple conversion so the merge bridge can reuse it:

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

Replace lines ~487–510 in `sync-package.py` (the classify → fetch assets → merge_with_identity → prereview marker block) with:

```python
if fetched and changed and cache.exists():
    _log("  -> Upstream PKGBUILD changed, classifying and merging via Pkl...")

    # Parse upstream PKGBUILDs (unavoidable bash — raw text from internet)
    old_vars, old_funcs = load_pkgbuild(str(pkg_dir / ".PKGBUILD.upstream"))
    new_vars, new_funcs = load_pkgbuild(str(pkg_dir / "PKGBUILD.new"))

    # Download new upstream assets before merge
    _fetch_assets((pkg_dir / "PKGBUILD.new").read_text(), base_url, pkg_dir)

    # Write upstream dicts as temporary .pkl files
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
   python scripts/sync-package.py bifrost 1.0.0
   ```
   Expected: "Upstream PKGBUILD unchanged." — merge path not triggered.

2. **Simulated upstream change** — manually edit `.PKGBUILD.upstream` to change `pkgdesc`, then run sync again:
   ```
   python scripts/sync-package.py bifrost 1.0.0
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
