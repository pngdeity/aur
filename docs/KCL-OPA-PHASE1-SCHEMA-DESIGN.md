# Phase 1 — KCL PKGBUILD Schema Design

**Date:** 2026-05-11
**Status:** Proposed
**Parent:** [`docs/KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md`](KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md) §3
**Next:** [`docs/KCL-OPA-PHASE2-POLICY-ENGINE.md`](KCL-OPA-PHASE2-POLICY-ENGINE.md)

---

## 1. Purpose & Scope

Phase 1 delivers a typed data model for `PKGBUILD(5)` — the Arch Linux build description format — expressed as a KCL schema. The schema must capture the full surface area of what a `PKGBUILD` can declare, including the 13 custom `_`-prefixed variables in use across this repository's 6 active packages.

**What this phase produces:**

| Artifact | Path | Purpose |
|----------|------|---------|
| KCL schema | `schemas/arch_pkg.k` | Typed schema for all `PKGBUILD(5)` fields + custom variables |
| Import script | `scripts/pkgbuild_to_kcl.py` | Converts existing Bash `PKGBUILD` → KCL `package.k` |
| Validation wrapper | `scripts/validate-pkgbuilds.sh` | Orchestrates import → compile → policy check loop |

**What this phase does NOT do:**
- Does not enforce policies (that's Phase 2).
- Does not render KCL back to PKGBUILD text (that's Phase 3).
- Does not modify any existing PKGBUILD files.

---

## 2. Schema Architecture

### 2.1 Design Principles

1. **Completeness over strictness**: Every field that `PKGBUILD(5)` permits must have a home in the schema, even if the type is loose (e.g., lifecycle functions stored as raw strings). Missing fields are worse than weakly-typed fields.
2. **Structural validation at the schema level**: Constraints that can be expressed in KCL's type system (enums, regex, required fields) live in the schema. Semantic validation (cross-field rules, policy checks) lives in OPA (Phase 2).
3. **Round-trip fidelity**: The schema must preserve enough information that a renderer (Phase 3) can reconstruct a functionally equivalent PKGBUILD. Comment preservation is not required.
4. **Independent compilation**: Each `packages/<name>/package.k` file must compile without requiring other package files — no cross-package schema dependencies.

### 2.2 KCL Schema Structure

The schema uses three KCL constructs:

- **`schema`** — Defines a named type with typed fields and optional `check` constraints.
- **Union types** (`int | float`) — For fields that accept multiple primitive types (e.g., `pkgrel` can be integer `1` or float `1.1` for variant builds).
- **Optional fields** (`field?`) — For every non-required PKGBUILD variable.

```
schemas/arch_pkg.k
    ├── schema SourceEntry        # Individual source URL with optional filename
    ├── schema OptDependsEntry    # Optional dependency with description
    ├── schema BuildOptions       # makepkg option flags
    └── schema Package            # Top-level PKGBUILD model
```

### 2.3 Dependency Graph

```
                    ┌─────────────┐
                    │  Package    │  (top-level schema)
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌──────────────┐
    │SourceEntry │  │OptDepEntry │  │BuildOptions  │
    └────────────┘  └────────────┘  └──────────────┘
```

No external KCL module imports. One file, self-contained.

---

## 3. Field Specification

### 3.1 Standard Fields (`PKGBUILD(5)`)

Every field defined in `PKGBUILD(5)` is present. Fields marked `(required)` are mandatory in the schema; others are optional.

#### Identity & Versioning

| Field | KCL Type | Required | PKGBUILD(5) § | Notes |
|-------|----------|----------|---------------|-------|
| `pkgname` | `str` | Yes | §7.1 | Constraint: `[a-z0-9@._+-]+` |
| `pkgver` | `str` | Yes | §7.2 | No hyphens (checked in OPA, not schema) |
| `pkgrel` | `int \| float` | Yes | §7.3 | Float for variant builds (`1.1`) |
| `epoch` | `int` | No | §7.4 | Default 0 when absent |
| `pkgdesc` | `str` | Yes | §7.5 | |
| `changelog` | `str` | No | §7.16 | Filename of changelog |

#### Architecture & Metadata

| Field | KCL Type | Required | PKGBUILD(5) § | Notes |
|-------|----------|----------|---------------|-------|
| `arch` | `[str]` | Yes | §7.7 | Enum constraint: `x86_64`, `aarch64`, `any` |
| `url` | `str` | Yes | §7.12 | |
| `license` | `[str]` | Yes | §7.13 | |
| `groups` | `[str]` | No | §7.8 | |

#### Package Relationships

| Field | KCL Type | Required | PKGBUILD(5) § | Notes |
|-------|----------|----------|---------------|-------|
| `depends` | `[str]` | No | §7.14.1 | |
| `makedepends` | `[str]` | No | §7.14.2 | |
| `checkdepends` | `[str]` | No | §7.14.3 | |
| `optdepends` | `[OptDependsEntry]` | No | §7.14.4 | See §3.2 below |
| `provides` | `[str]` | No | §7.15.1 | |
| `conflicts` | `[str]` | No | §7.15.2 | |
| `replaces` | `[str]` | No | §7.15.3 | |

#### Source & Integrity

| Field | KCL Type | Required | PKGBUILD(5) § | Notes |
|-------|----------|----------|---------------|-------|
| `source` | `[SourceEntry]` | No | §7.9 | See §3.3 below. Required if no `pkgver()` function. |
| `sha256sums` | `[str]` | No | §7.10.1 | Exactly one of `sha*sums`/`b2sums` arrays required if `source` present |
| `sha512sums` | `[str]` | No | §7.10.2 | |
| `sha224sums` | `[str]` | No | §7.10.3 | |
| `sha384sums` | `[str]` | No | §7.10.4 | |
| `b2sums` | `[str]` | No | §7.10.5 | |
| `validpgpkeys` | `[str]` | No | §7.10.6 | |
| `noextract` | `[str]` | No | §7.17 | Filenames to not extract |

#### Install & Config

| Field | KCL Type | Required | PKGBUILD(5) § | Notes |
|-------|----------|----------|---------------|-------|
| `install` | `str` | No | §7.11 | Filename of `.install` scriptlet |
| `backup` | `[str]` | No | §7.18 | |
| `options` | `[str]` | No | §7.19 | Enum constraint: `!strip`, `!debug`, `!lto`, `!staticlibs`, `!emptydirs`, `!zipman`, `!purge`, `!libtool`, `staticlibs`, `zipman`, `purge`, `libtool`, `strip`, `debug`, `lto`, `makeflags`, `buildflags` |

#### Lifecycle Functions

| Field | KCL Type | Required | PKGBUILD(5) § | Notes |
|-------|----------|----------|---------------|-------|
| `pkgver_func` | `str` | No | §8.8 | Only for VCS packages. Raw text block. |
| `prepare` | `str` | No | §8.9.1 | Raw text block |
| `build` | `str` | No | §8.9.2 | Raw text block |
| `check` | `str` | No | §8.9.3 | Raw text block |
| `package` | `str` | No | §8.9.4 | Raw text block |

### 3.2 Sub-Schema: `OptDependsEntry`

```kcl
schema OptDependsEntry:
    """A single optional dependency with its description."""
    name: str
    desc: str
```

Models entries like `'wl-clipboard: clipboard support on Wayland'`. The import script splits on the first `: ` to separate name from description.

### 3.3 Sub-Schema: `SourceEntry`

```kcl
schema SourceEntry:
    """A single source URL, optionally renamed via filename:: prefix."""
    url: str       # Full URL including VCS fragments (#tag=, #commit=, #branch=)
    filename: str  # The local filename this source will be saved as
```

Models entries like:
- `"${pkgname}::git+https://github.com/...git#tag=v${pkgver}"` → `filename = "${pkgname}"`, `url = "git+https://..."` 
- `"https://example.com/release-1.0.tar.gz"` → `filename = "release-1.0.tar.gz"`, `url = "https://..."` (identical)
- `"change-PATH.patch"` → `filename = "change-PATH.patch"`, `url = "change-PATH.patch"` (local file, same)

The import script handles the `filename::url` syntax by splitting on `::`.

### 3.4 Custom Variables (Repository-Specific)

All 13 `_`-prefixed variables documented in `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` plus the npm conventions used by `jules-tools`:

#### Orchestration Layer (used by `sync-package.sh`, `aur-deploy.sh`, CI)

| Field | KCL Type | Required | Enum/Constraint | Used By |
|-------|----------|----------|-----------------|---------|
| `_deploy_aur` | `bool` | No (default `false`) | Mutually exclusive with `_repo_subarch` (Phase 2 check) | `aur-deploy.sh`, `release.yml` |
| `_pkgname` | `str` | Conditional | Required for variant packages. Discriminator for variant groups. | `check-pkgdesc-consistency.sh` |
| `_githubname` | `str` | No | Pattern: `owner/repo` | `generate-changelog.sh` |
| `_upstream_aur_pkg` | `str` | No | Must match an AUR package name | `sync-package.sh` |
| `_upstream_arch_repo` | `str` | No | Must match a GitLab repo path | `sync-package.sh` |
| `_demote_upstream_maintainer` | `bool` | No (default `false`) | | `sync-package.sh` |
| `_auto_merge_build` | `bool` | No (default `false`) | | `sync-package.sh` |
| `_use_common_gemini_settings` | `bool` | No (default `false`) | | `sync-package.sh` |
| `_repo_subarch` | `str` | No | Enum: `x86_64_v3`, `x86_64_v4` | `arch-builder.sh`, `release.yml` |
| `_tag` | `str` | No | | `sync-package.sh` |

#### Package-Local Conventions

| Field | KCL Type | Required | Used By |
|-------|----------|----------|---------|
| `_npmscope` | `str` | No | `jules-tools` |
| `_npmname` | `str` | No | `jules-tools` |
| `_npmver` | `str` | No | `jules-tools` |

**Not modeled**: `_github_api_version` (comment-based, not a real variable assignment), `_target_arch` (internal shell function in `opencode-git`, not a variable).

### 3.5 Version Range Support

Per `PKGBUILD(5)` §7.14, dependency fields support version comparison operators (`>=`, `<=`, `=`, `>`, `<`). These are embedded in the string values (e.g., `"glibc>=2.40"`). The schema stores them as plain strings — structural validation of the version syntax is deferred to OPA (Phase 2).

---

## 4. KCL Schema Implementation

### 4.1 Complete Schema (`schemas/arch_pkg.k`)

```kcl
# PKGBUILD(5) Typed Data Model
# Covers 100% of the PKGBUILD(5) surface area plus repository-specific
# _-prefixed variables defined in docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md

schema OptDependsEntry:
    name: str
    desc: str

schema SourceEntry:
    url: str
    filename: str

schema Package:
    # ── Identity & Versioning (PKGBUILD(5) §7.1-7.5, 7.16) ──
    pkgname: str
    pkgver: str
    pkgrel: int | float
    epoch?: int = 0
    pkgdesc: str
    changelog?: str

    # ── Architecture & Metadata (PKGBUILD(5) §7.7, 7.8, 7.12, 7.13) ──
    arch: [str]
    url: str
    license: [str]
    groups?: [str]

    # ── Package Relationships (PKGBUILD(5) §7.14, 7.15) ──
    depends?: [str]
    makedepends?: [str]
    checkdepends?: [str]
    optdepends?: [OptDependsEntry]
    provides?: [str]
    conflicts?: [str]
    replaces?: [str]

    # ── Source & Integrity (PKGBUILD(5) §7.9, 7.10, 7.17) ──
    source?: [SourceEntry]
    sha256sums?: [str]
    sha512sums?: [str]
    sha224sums?: [str]
    sha384sums?: [str]
    b2sums?: [str]
    validpgpkeys?: [str]
    noextract?: [str]

    # ── Install & Config (PKGBUILD(5) §7.11, 7.18, 7.19) ──
    install?: str
    backup?: [str]
    options?: [str]

    # ── Lifecycle Functions (PKGBUILD(5) §8.8-8.9) ──
    pkgver_func?: str
    prepare?: str
    build?: str
    check?: str
    package?: str

    # ── Custom Variables (Repository-Specific) ──
    _deploy_aur?: bool = False
    _pkgname?: str
    _githubname?: str
    _upstream_aur_pkg?: str
    _upstream_arch_repo?: str
    _demote_upstream_maintainer?: bool = False
    _auto_merge_build?: bool = False
    _use_common_gemini_settings?: bool = False
    _repo_subarch?: str
    _tag?: str
    _npmscope?: str
    _npmname?: str
    _npmver?: str

    # ── Schema-Level Constraints ──
    check:
        # pkgname must match PKGBUILD(5) §7.1 pattern
        regex.match(pkgname, r'^[a-z0-9@._+\-]+$'), \
            "pkgname '{}' must match PKGBUILD(5) pattern [a-z0-9@._+-]".format(pkgname)

        # arch values must be from the known set
        all a in arch {
            a in ["x86_64", "aarch64", "any"]
        }, "arch '{}' contains unknown architecture value".format(arch)

        # pkgrel must be positive
        pkgrel > 0, "pkgrel must be positive, got {}".format(pkgrel)
```

### 4.2 Design Notes

**Union type on `pkgrel`**: KCL supports `int | float` union types. Variant builds use `pkgrel=1.1` (float), base packages use `pkgrel=1` (integer). This model preserves the distinction.

**Function bodies as strings**: Lifecycle functions (`prepare`, `build`, `check`, `package`, `pkgver_func`) are stored as raw multi-line strings. KCL supports triple-quoted strings (`"""..."""`) for multi-line content. The import script preserves exact indentation and content. No structural analysis of function bodies occurs at the schema level — OPA (Phase 2) scans for `sudo` and other patterns.

**`_repo_subarch` enum**: The value set is `x86_64_v3`, `x86_64_v4`. Additional values can be added as new sub-architectures are supported. The schema `check` block does not enforce this enum — it's enforced by OPA (Phase 2, rule 6) which can provide a descriptive error message.

**Checksum arrays**: The schema does not enforce that exactly one checksum array is present — leaving that to OPA (Phase 2, rule 10). This keeps the schema permissive and the policy strict, following the principle of structural validation in the schema, semantic validation in OPA.

---

## 5. Import Script Design (`scripts/pkgbuild_to_kcl.py`)

### 5.1 Purpose

Converts an existing Bash `PKGBUILD` into a KCL `package.k` file conforming to the schema. This is **temporary scaffolding** — needed to bootstrap the validation workflow for the 6 existing packages without requiring manual `.k` authoring. It is deprecated once Phase 4 converts packages to native `package.k`.

### 5.2 Architecture

```
PKGBUILD (Bash)
    │
    ▼
┌──────────────────────────┐
│  bash -c 'source PKGBUILD;│   Subprocess: source the PKGBUILD
│   declare -p'             │   to resolve all variable references
└──────────┬───────────────┘
           │  declare output (text)
           ▼
┌──────────────────────────┐
│  Variable Parser          │   Parse declare -p into Python dict
│  (declare -p → dict)      │   - Handle arrays: declare -a vars=([0]="val" ...)
│                           │   - Handle strings: declare -- var="val"
│                           │   - Handle integers: declare -i var="1"
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Function Extractor       │   Extract function bodies via heuristic:
│  (sed /^funcname()/,/^}/) │   - pkgver(): named block
│                           │   - prepare(), build(), check(), package()
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Source Parser            │   Parse source[] array into SourceEntry list
│  (split filename::url)    │   - Detect filename::url syntax
│                           │   - Detect VCS fragments (#tag=, #commit=)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  KCL Emitter              │   Write package.k with correct KCL syntax
│                           │   - Strings: quoted with escaping
│                           │   - Arrays: [elem1, elem2]
│                           │   - Multi-line: """..."""
│                           │   - Bools: True/False
└──────────┬───────────────┘
           │
           ▼
       package.k
```

### 5.3 Variable Resolution Strategy

The import script spawns a `bash` subprocess that:
1. Sets empty defaults for all `makepkg`-provided variables (`CARCH`, `srcdir`, `pkgdir`, `startdir`).
2. Sets `_deploy_aur=false`, `_demote_upstream_maintainer=false`, etc. (so `${_deploy_aur:-...}` resolves correctly).
3. Sources the PKGBUILD with `set -a` to export all variables.
4. Runs `declare -p` to dump all defined variables in machine-parseable form.
5. Runs `declare -f` to extract function definitions.

The Python side:
1. Parses `declare -p` output: `declare -- FOO="value"`, `declare -a ARR=([0]="a" [1]="b")`, `declare -i INT="1"`.
2. Filters to PKGBUILD-relevant variables and `_`-prefixed variables only (excludes `BASH_*`, `OLDPWD`, etc.).
3. Maps Bash variable names to KCL field names (direct 1:1 mapping — `pkgname` → `pkgname`, `_deploy_aur` → `_deploy_aur`).

### 5.4 Source Array Parsing

The `source=()` array requires special handling because it uses `filename::url` syntax:

```
source=(
    "${pkgname}::git+https://github.com/...git#tag=v${pkgver}"
    "change-PATH.patch"
)
```

Parsing logic:
1. For each element in the resolved source array:
   - If the string contains `::`, split on the first `::`: left is `filename`, right is `url`.
   - If no `::`, the entire string is both `filename` and `url`.
2. Emit as KCL `SourceEntry { filename = "...", url = "..." }`.

### 5.5 Optdepends Parsing

The `optdepends=()` array contains entries like `'package-name: description text'`:

Parsing logic:
1. For each element, split on the first `: ` (colon-space).
2. Left side is `name`, right side is `desc`.
3. If no `: ` is found, the entire string is `name` and `desc` is empty string.
4. Emit as KCL `OptDependsEntry { name = "...", desc = "..." }`.

### 5.6 Edge Cases

| Scenario | Handling |
|----------|----------|
| Variable references in source URLs (`${pkgname}`) | `declare -p` resolves them — the import script gets the expanded value |
| Dynamic variable computation (e.g., `pkgver=$(git describe)`) | Cannot be resolved statically. Flag with a comment in output: `# WARNING: pkgver computed dynamically; value shown is snapshot from `declare -p` |
| Multi-line function bodies with nested braces | Function extractor uses brace-counting, not simple `/^}/` matching. The heuristic: count `{` increments, `}` decrements, stop when count reaches 0. |
| `pkgrel=1.1` (float) for variant builds | Detected by the `.` in the value; emitted as KCL `1.1` (float literal) |
| Empty arrays (`optdepends=()`) | Emitted as `[]` in KCL; optional fields can be omitted entirely |
| Comments within source arrays (e.g., `# Live AI model catalog`) | Bash strips comments before `declare -p`. They are lost — which is fine per the schema's comment-preservation-is-not-required principle. |
| `options=('!debug' '!strip')` with `!` prefix | Stored as literal strings. OPA (Phase 2) validates against known option values. |
| `arch=('any')` vs `arch=(any)` | Both valid Bash. `declare -p` normalizes both to the array form. |
| Packages with no `source[]` (pure VCS `pkgver()` packages) | `source` field omitted. No checksum arrays generated. Valid per schema. |

---

## 6. Validation Wrapper (`scripts/validate-pkgbuilds.sh`)

### 6.1 Purpose

Single entry point for the full validation flow. Called by:
- Pre-commit hook (`.pre-commit-config.yaml`)
- CI `build.yml` validate job
- CI `discovery.yml` pre-push gate
- Local development (`./scripts/validate-pkgbuilds.sh`)

### 6.2 Implementation Logic

```bash
#!/bin/bash
set -euo pipefail

KCL_BIN="${KCL_BIN:-kcl}"
CONFTEST_BIN="${CONFTEST_BIN:-conftest}"
TMPDIR="${TMPDIR:-/tmp}/kcl-validate-$$"
PACKAGES_DIR="packages"
SCHEMA_FILE="schemas/arch_pkg.k"

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

mkdir -p "$TMPDIR"

# Find all PKGBUILDs
FAILED=0
RESULTS=""
shopt -s nullglob
for pkgbuild in "$PACKAGES_DIR"/*/PKGBUILD; do
    pkg_dir="$(dirname "$pkgbuild")"
    pkg_name="$(basename "$pkg_dir")"

    # Step 1: Import PKGBUILD → KCL (if no package.k exists)
    kcl_file="$pkg_dir/package.k"
    if [ ! -f "$kcl_file" ]; then
        python3 scripts/pkgbuild_to_kcl.py "$pkgbuild" > "$TMPDIR/${pkg_name}.k" || {
            echo "FAIL: $pkg_name — import failed"
            FAILED=1
            continue
        }
        kcl_file="$TMPDIR/${pkg_name}.k"
    fi
    KCL_FILES+=("$kcl_file")
    PKG_NAMES+=("$pkg_name")
done

if [ ${#KCL_FILES[@]} -eq 0 ]; then
    echo "No PKGBUILD files found in $PACKAGES_DIR"
    exit 0
fi

# Step 2: Compile all KCL files
MANIFEST="$TMPDIR/manifest.json"
"$KCL_BIN" run "${KCL_FILES[@]}" -o "$MANIFEST" 2>&1 || {
    echo "FAIL: KCL compilation error"
    exit 1
}

# Step 3: Run OPA policy check (if conftest is available)
# In Phase 1, this step is a no-op (no policies exist yet).
# Phase 2 activates it.
if command -v "$CONFTEST_BIN" &>/dev/null && [ -d policies ]; then
    "$CONFTEST_BIN" test "$MANIFEST" -p policies/ 2>&1 || {
        echo "FAIL: OPA policy violations"
        FAILED=1
    }
fi

exit $FAILED
```

### 6.3 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All PKGBUILDs validated successfully |
| 1 | Validation failure (import, compile, or policy) |
| 2 | Prerequisites missing (refer to stderr) |

### 6.4 Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `KCL_BIN` | `kcl` | Path to KCL compiler |
| `CONFTEST_BIN` | `conftest` | Path to Conftest binary |
| `TMPDIR` | `/tmp/kcl-validate-$$` | Working directory for generated files |
| `SKIP_OPA` | (unset) | If set to `1`, skip policy check (useful in Phase 1 before policies exist) |

---

## 7. Directory Structure After Phase 1

```
.
├── schemas/
│   └── arch_pkg.k                  # NEW — KCL schema
├── scripts/
│   ├── pkgbuild_to_kcl.py          # NEW — PKGBUILD → KCL import
│   ├── validate-pkgbuilds.sh       # NEW — validation orchestration
│   ├── pkgvar                      # existing — variable extractor (reference implementation)
│   └── ...                         # existing scripts unchanged
├── packages/
│   ├── opendoas/
│   │   ├── PKGBUILD                # unchanged
│   │   └── ...                     # existing files unchanged
│   └── ...                         # other packages unchanged
├── policies/                       # empty dir created now; populated in Phase 2
│   └── .gitkeep
├── docs/
│   ├── KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md  # NEW
│   ├── KCL-OPA-PHASE1-SCHEMA-DESIGN.md            # NEW (this document)
│   └── ...
└── .pre-commit-config.yaml         # unchanged in Phase 1 (updated in Phase 3)
```

---

## 8. Testing Strategy

### 8.1 Schema Validation Tests

Test that the schema correctly accepts and rejects inputs:

| Test Case | Expected | Rationale |
|-----------|----------|-----------|
| Minimal valid package (required fields only) | Pass | Verifies schema doesn't demand optional fields |
| `arch` with invalid value `"i686"` | Fail | Enum constraint enforcement |
| `pkgname` with uppercase `"MyPackage"` | Fail | Regex constraint `[a-z0-9@._+-]` |
| `pkgrel` as integer `1` | Pass | Union type accepts `int` |
| `pkgrel` as float `1.1` | Pass | Union type accepts `float` for variant builds |
| `pkgrel` as string `"1"` | Fail | Type mismatch |
| `_deploy_aur` as boolean `true` | Pass | Custom variable typing |
| `_deploy_aur` as string `"true"` | Fail | Type mismatch (must be bool) |
| Source with `filename::url` syntax | Pass | `SourceEntry` split handled by import script |
| Package with lifecycle functions | Pass | Functions stored as strings |
| `options` with `!strip` value | Pass | Known option, string storage |

### 8.2 Import Script Tests

Test against all 6 existing PKGBUILDs:

| Package | Complexity | What to Verify |
|---------|-----------|---------------|
| `opendoas` | Medium — patches, VCS source, `.install`, provides/conflicts/replaces | All standard fields + source parsing + function extraction |
| `opencode-git` | High — VCS pkgver(), bun build, arch branching, completions | `pkgver_func`, multi-line functions, `_target_arch` handling |
| `amass-git` | Medium — Go build, VCS source, `changelog` field | `changelog`, `pkgver_func`, `_upstream_aur_pkg` |
| `amass-bin` | Low — binary package, `changelog` field | `_upstream_aur_pkg`, `changelog` |
| `jules-tools` | Low — npm package, `noextract`, scope variables | `_npm*` variables, `noextract` field |
| `ranger-doas` | Medium — Python build, patches, `validpgpkeys`, many optdepends | `validpgpkeys`, `optdepends` parsing, `sha512sums` |

Acceptance: All 6 PKGBUILDs import without errors and the resulting KCL files compile (`kcl run` exit 0).

### 8.3 Round-Trip Preview

Run the import → compile → manual inspection loop: check that the emitted KCL looks like valid, readable configuration. This is a preview of Phase 3's full round-trip — the renderer validates that the schema captured enough information.

---

## 9. Known Limitations (Phase 1)

| Limitation | Impact | Resolution Path |
|------------|--------|----------------|
| Comments and blank lines lost during import | Readability of auto-generated `package.k` files is reduced | Acceptable — these are scaffolding files. Phase 4 manual authoring recovers readability. |
| Dynamic `pkgver` computation cannot be statically resolved | Import script captures a snapshot value that may be stale | Documented. The `pkgver_func` field preserves the computation logic; the `pkgver` field is the resolved value. |
| KCL version pin: schema syntax may drift with KCL releases | Schema may need updates when KCL introduces breaking changes | Pin KCL version in CI. Monitor KCL release notes. KCL's schema syntax has been stable since 0.7. |
| `declare -p` output format may vary across Bash versions | Import script parser needs to handle Bash 4.0+ and 5.0+ `declare` output | Test on both `ubuntu-latest` (Bash 5.x) and the `archlinux:base-devel` container (Bash 5.x). No Bash 4.x targets in this repo. |

---

## 10. Phase 1 Acceptance Criteria

- [ ] `schemas/arch_pkg.k` exists and compiles (`kcl run` with no errors on a standalone check).
- [ ] `scripts/pkgbuild_to_kcl.py` imports all 6 existing PKGBUILDs without error.
- [ ] All 6 imported KCL files compile against the schema (`kcl run` exit 0).
- [ ] `scripts/validate-pkgbuilds.sh` runs end-to-end: discovers PKGBUILDs, imports them, compiles them.
- [ ] Manual inspection confirms that all 13 custom variables are captured in the output for the packages that use them.
- [ ] The schema correctly rejects known-invalid inputs (tests from §8.1 pass).
- [ ] The import script correctly handles the edge cases listed in §5.6.
