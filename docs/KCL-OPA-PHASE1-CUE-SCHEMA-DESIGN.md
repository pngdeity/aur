**Status: SUPERSEDED by Pkl.** See PKL-CROSS-PHASE-EVALUATION.md. Retained as rationale artifact only. **Do not implement from this document.**

# Phase 1 (CUE) — CUE PKGBUILD Schema Design

**Date:** 2026-05-11
**Status:** Proposed
**Parent:** [`docs/KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md`](KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md) §3 (CUE variant)
**Sibling:** [`docs/KCL-OPA-PHASE1-SCHEMA-DESIGN.md`](KCL-OPA-PHASE1-SCHEMA-DESIGN.md) (KCL variant)
**Language:** CUE ([cuelang.org](https://cuelang.org/))

---

## 1. Purpose & Scope

Phase 1 delivers a typed data model for `PKGBUILD(5)` — the Arch Linux build description format — expressed as a CUE definition. The schema must capture the full surface area of what a `PKGBUILD` can declare, including the 13 custom `_`-prefixed variables in use across this repository's 6 active packages.

**Why CUE**: CUE is an open-source data validation language with roots in logic programming. Unlike KCL's imperative `check` blocks, CUE embeds constraints directly into the type system via bounds (`>0`, `<100`), regex patterns (`=~"^[a-z]+$"`), disjunctions (`int | string`), and definitions (closed structs prefixed with `#`). CUE unifies types and values — `"x86_64"` is both a type and a value — eliminating the type/value dichotomy found in schema languages that separate validation logic from structural typing.

**What this phase produces:**

| Artifact | Path | Purpose |
|----------|------|---------|
| CUE definition | `schemas/arch_pkg.cue` | Typed definition for all `PKGBUILD(5)` fields + custom variables |
| CUE package files | `packages/<name>/package.cue` | Per-package CUE data files (Phase 4+; Phase 1 produces via import) |
| Import script | `scripts/pkgbuild_to_cue.py` | Converts existing Bash `PKGBUILD` → CUE `package.cue` |
| Validation wrapper | `scripts/validate-pkgbuilds-cue.sh` | Orchestrates import → `cue vet` → policy check loop |

**What this phase does NOT do:**
- Does not enforce policies (that's Phase 2 — OPA/Conftest against exported JSON).
- Does not render CUE back to PKGBUILD text (that's Phase 3).
- Does not modify any existing PKGBUILD files.

---

## 2. CUE Schema Architecture

### 2.1 CUE Conceptual Model vs. KCL

CUE takes a fundamentally different approach to schema definition than KCL:

| Concept | KCL | CUE |
|---------|-----|-----|
| Schema keyword | `schema Package:` | `#Package: { ... }` (definition) |
| Type declaration | `field: str` | `field: string` |
| Constraints | `check:` block with function calls | Inline bounds, regex, disjunctions |
| Enum | `field in ["a", "b"]` in `check:` | `field: "a" | "b"` (disjunction) |
| Regex | `regex.match(field, r"^pattern$")` in `check:` | `field: =~"^pattern$"` (regex bound) |
| Optional | `field?: str` | `field?: string` |
| Required | (all fields by default; optional with `?`) | `field!: string` (required), `field: string` (regular — must be concrete on export) |
| Default | `field?: str = "val"` | `*3 | int` (default marker in disjunction) |
| Closed struct | `schema` is open | Definitions (`#`) are closed by default |
| Union types | `int \| float` | `int | float` |
| Output | `kcl run --format json` | `cue export --out json` |
| Validation-only | `kcl run` doesn't enforce concreteness | `cue vet` validates without requiring concreteness (`-c=false`) |

### 2.2 Design Principles

1. **Completeness over strictness**: Every field that `PKGBUILD(5)` permits must have a home in the definition, even if the type is loose (e.g., lifecycle functions stored as raw strings). Missing fields are worse than weakly-typed fields.
2. **Structural validation inline**: Constraints are embedded in field types using CUE's native operators (bounds, regex, disjunctions). No separate validation block.
3. **Definitions are closed**: Using `#Package` ensures no undeclared fields can appear in package data — CUE's closed structs catch typos at compile time.
4. **Round-trip fidelity**: The definition must preserve enough information that a renderer (Phase 3) can reconstruct a functionally equivalent PKGBUILD.
5. **Independent evaluation**: Each `packages/<name>/package.cue` file must evaluate without requiring other package files — no cross-package definition dependencies.

### 2.3 Definition Structure

```
schemas/arch_pkg.cue
    ├── #SourceEntry       # Source URL with optional filename override
    ├── #OptDependsEntry   # Optional dependency with description
    ├── #Package           # Top-level PKGBUILD definition (closed struct)
    │   ├── Identity fields (pkgname, pkgver, pkgrel, epoch, pkgdesc)
    │   ├── Metadata fields (arch, url, license, groups)
    │   ├── Relationship fields (depends, makedepends, checkdepends, optdepends, provides, conflicts, replaces)
    │   ├── Source fields (source, sha256sums, etc.)
    │   ├── Config fields (backup, install, options, noextract, validpgpkeys)
    │   ├── Lifecycle functions (pkgver, prepare, build, check, package) — raw strings
    │   └── Custom variables (13 _-prefixed fields)
    └── package: #Package  # Schema export path for cue vet -d '#Package'
```

### 2.4 Dependency Graph

```
                    ┌──────────┐
                    │ #Package │  (top-level definition)
                    └────┬─────┘
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
    ┌───────────┐ ┌───────────┐ ┌──────────┐
    │#SourceEntry│ │#OptDepEntry│ │ (bounds, │
    └───────────┘ └───────────┘ │  regex)  │
                                 └──────────┘
```

All sub-definitions are in the same file. No external CUE module imports in Phase 1.

---

## 3. Field Specification

### 3.1 Standard Fields (`PKGBUILD(5)`)

Every field defined in `PKGBUILD(5)` is present.

#### Identity & Versioning

| Field | CUE Type | Required? | PKGBUILD(5) § | Constraint |
|-------|----------|-----------|---------------|------------|
| `pkgname` | `string` | Required (`!`) | §7.1 | `=~"^[a-z0-9@._+\\-]+$"` |
| `pkgver` | `string` | Required (`!`) | §7.2 | (no hyphens — enforced in OPA Phase 2) |
| `pkgrel` | `number` | Required (`!`) | §7.3 | `>0` (variant builds use `1.1`) |
| `epoch` | `int` | Optional (`?`) | §7.4 | `>=0` |
| `pkgdesc` | `string` | Required (`!`) | §7.5 | |
| `changelog` | `string` | Optional (`?`) | §7.16 | |

#### Architecture & Metadata

| Field | CUE Type | Required? | PKGBUILD(5) § | Constraint |
|-------|----------|-----------|---------------|------------|
| `arch` | `[...string]` | Required (`!`) | §7.7 | Elements: `"x86_64" \| "aarch64" \| "any"` |
| `url` | `string` | Required (`!`) | §7.12 | |
| `license` | `[...string]` | Required (`!`) | §7.13 | |
| `groups` | `[...string]` | Optional (`?`) | §7.8 | |

#### Package Relationships

| Field | CUE Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `depends` | `[...string]` | Optional (`?`) | §7.14.1 | Version constraints embedded in strings (e.g., `"glibc>=2.40"`) |
| `makedepends` | `[...string]` | Optional (`?`) | §7.14.2 | |
| `checkdepends` | `[...string]` | Optional (`?`) | §7.14.3 | |
| `optdepends` | `[...#OptDependsEntry]` | Optional (`?`) | §7.14.4 | See §3.2 |
| `provides` | `[...string]` | Optional (`?`) | §7.15.1 | |
| `conflicts` | `[...string]` | Optional (`?`) | §7.15.2 | |
| `replaces` | `[...string]` | Optional (`?`) | §7.15.3 | |

#### Source & Integrity

| Field | CUE Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `source` | `[...#SourceEntry]` | Optional (`?`) | §7.9 | Required if no `pkgver` function. See §3.3. |
| `sha256sums` | `[...string]` | Optional (`?`) | §7.10.1 | Exactly one checksum array required if `source` present (enforced in OPA Phase 2) |
| `sha512sums` | `[...string]` | Optional (`?`) | §7.10.2 | |
| `sha224sums` | `[...string]` | Optional (`?`) | §7.10.3 | |
| `sha384sums` | `[...string]` | Optional (`?`) | §7.10.4 | |
| `b2sums` | `[...string]` | Optional (`?`) | §7.10.5 | |
| `validpgpkeys` | `[...string]` | Optional (`?`) | §7.10.6 | |
| `noextract` | `[...string]` | Optional (`?`) | §7.17 | |

#### Install & Config

| Field | CUE Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `install` | `string` | Optional (`?`) | §7.11 | Filename of `.install` scriptlet |
| `backup` | `[...string]` | Optional (`?`) | §7.18 | |
| `options` | `[...string]` | Optional (`?`) | §7.19 | Elements: `"!strip" \| "!debug" \| "!lto" \| "!staticlibs" \| "!emptydirs" \| "!zipman" \| "!purge" \| "!libtool" \| "staticlibs" \| "zipman" \| "purge" \| "libtool" \| "strip" \| "debug" \| "lto" \| "makeflags" \| "buildflags"` |

#### Lifecycle Functions

All function bodies are stored as raw strings. CUE does not validate Bash syntax — the string type constraint ensures the data is a string, and the content is opaque to CUE.

| Field | CUE Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `pkgver` | `string` | Optional (`?`) | §8.8 | Function body text. Only for VCS packages. |
| `prepare` | `string` | Optional (`?`) | §8.9.1 | |
| `build` | `string` | Optional (`?`) | §8.9.2 | |
| `check` | `string` | Optional (`?`) | §8.9.3 | |
| `package` | `string` | Optional (`?`) | §8.9.4 | |

### 3.2 Sub-Definition: `#OptDependsEntry`

Models entries like `'wl-clipboard: clipboard support on Wayland'`:

```cue
#OptDependsEntry: {
    name: string  // package name
    desc: string  // description after the ": "
}
```

The import script splits on the first `: ` to separate name from description. The renderer (Phase 3) reassembles them.

### 3.3 Sub-Definition: `#SourceEntry`

Models entries like `"${pkgname}::git+https://github.com/...git#tag=v${pkgver}"`:

```cue
#SourceEntry: {
    url:      string  // Full URL including VCS fragments (#tag=, #commit=, #branch=)
    filename: string  // Local filename this source will be saved as
    raw_url?: string  // Raw unexpanded text from PKGBUILD (for rendering fidelity)
}
```

**`filename::url` syntax**: The import script splits on `::`. When `filename != url`, the renderer reconstructs `"filename::url"`. When equal, it renders just `"filename"`. The `raw_url` field preserves the original `${pkgname}::...` text for exact rendering when the import script can detect variable references before Bash expansion.

### 3.4 Custom Variables (Repository-Specific)

All 13 `_`-prefixed variables documented in `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md` plus npm conventions. In CUE, identifiers can start with `_` — these are ordinary field names.

#### Orchestration Layer (used by `sync-package.sh`, `aur-deploy.sh`, CI)

| Field | CUE Type | Default | Constraint | Used By |
|-------|----------|---------|------------|---------|
| `_deploy_aur` | `bool` | `*false \| true` | Mutually exclusive with `_repo_subarch` (Phase 2) | `aur-deploy.sh`, `release.yml` |
| `_pkgname` | `string` | — | Discriminator for variant groups | `check-pkgdesc-consistency.sh` |
| `_githubname` | `string` | — | Pattern: `=~"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"` | `generate-changelog.sh` |
| `_upstream_aur_pkg` | `string` | — | | `sync-package.sh` |
| `_upstream_arch_repo` | `string` | — | | `sync-package.sh` |
| `_demote_upstream_maintainer` | `bool` | `*false \| true` | | `sync-package.sh` |
| `_auto_merge_build` | `bool` | `*false \| true` | | `sync-package.sh` |
| `_use_common_gemini_settings` | `bool` | `*false \| true` | | `sync-package.sh` |
| `_repo_subarch` | `string` | — | `"x86_64_v3" \| "x86_64_v4"` | `arch-builder.sh`, `release.yml` |
| `_tag` | `string` | — | | `sync-package.sh` |

#### Package-Local Conventions

| Field | CUE Type | Used By |
|-------|----------|---------|
| `_npmscope` | `string` | `jules-tools` |
| `_npmname` | `string` | `jules-tools` |
| `_npmver` | `string` | `jules-tools` |

**Not modeled**: `_github_api_version` (comment-based, not a real variable assignment), `_target_arch` (internal shell function in `opencode-git`, not a variable).

---

## 4. CUE Definition Implementation

### 4.1 Complete Definition (`schemas/arch_pkg.cue`)

```cue
// PKGBUILD(5) Typed Data Model (CUE)
// Covers 100% of the PKGBUILD(5) surface area plus repository-specific
// _-prefixed variables defined in docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md
//
// Usage:
//   cue vet -d '#Package' packages/<name>/package.cue
//   cue export --out json -e package packages/<name>/package.cue

package schemas

// ── Sub-Definitions ──

#SourceEntry: {
    url:      string   // Full URL including VCS fragments (#tag=, #commit=)
    filename: string   // Local filename
    raw_url?: string   // Raw unexpanded text from PKGBUILD (for rendering)
}

#OptDependsEntry: {
    name: string       // Package name
    desc: string       // Description after ": "
}

// ── Top-Level Package Definition ──

#Package: {
    // Identity & Versioning (PKGBUILD(5) §7.1-7.5, 7.16)
    pkgname!:   =~"^[a-z0-9@._+\\-]+$"  // required, must match PKGBUILD(5) pattern
    pkgver!:    string                    // required
    pkgrel!:    >0                        // required, positive number (int or float)
    epoch?:     int & >=0                 // optional
    pkgdesc!:   string                    // required
    changelog?: string                    // optional

    // Architecture & Metadata (PKGBUILD(5) §7.7, 7.8, 7.12, 7.13)
    arch!: [..."x86_64" | "aarch64" | "any"]
    url!:     string
    license!: [...string]
    groups?:  [...string]

    // Package Relationships (PKGBUILD(5) §7.14, 7.15)
    depends?:      [...string]
    makedepends?:  [...string]
    checkdepends?: [...string]
    optdepends?:   [...#OptDependsEntry]
    provides?:     [...string]
    conflicts?:    [...string]
    replaces?:     [...string]

    // Source & Integrity (PKGBUILD(5) §7.9, 7.10, 7.17)
    source?:       [...#SourceEntry]
    sha256sums?:   [...string]
    sha512sums?:   [...string]
    sha224sums?:   [...string]
    sha384sums?:   [...string]
    b2sums?:       [...string]
    validpgpkeys?: [...string]
    noextract?:    [...string]

    // Install & Config (PKGBUILD(5) §7.11, 7.18, 7.19)
    install?: string
    backup?:  [...string]
    options?: [...(
        "!strip" | "!debug" | "!lto" | "!staticlibs" | "!emptydirs" |
        "!zipman" | "!purge" | "!libtool" | "staticlibs" | "zipman" |
        "purge" | "libtool" | "strip" | "debug" | "lto" |
        "makeflags" | "buildflags"
    )]

    // Lifecycle Functions (PKGBUILD(5) §8.8-8.9)
    // Stored as raw strings — CUE validates type but not Bash content.
    pkgver?:  string
    prepare?: string
    build?:   string
    check?:   string
    package?: string

    // Custom Variables (Repository-Specific)
    _deploy_aur?:                 *false | true
    _pkgname?:                    string
    _githubname?:                 =~"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"
    _upstream_aur_pkg?:           string
    _upstream_arch_repo?:         string
    _demote_upstream_maintainer?: *false | true
    _auto_merge_build?:           *false | true
    _use_common_gemini_settings?: *false | true
    _repo_subarch?:               "x86_64_v3" | "x86_64_v4"
    _tag?:                        string
    _npmscope?:                   string
    _npmname?:                    string
    _npmver?:                     string
}
```

### 4.2 Design Notes

**`*false | true` for boolean defaults**: CUE uses the default marker `*` within disjunctions. `*false | true` means: if no value is specified, default to `false`; if a value IS specified, it must be `true` or `false`. On export (`cue export`), the default `false` is selected and rendered. On validation-only (`cue vet -c=false`), the disjunction remains unresolved without error.

**`[...X]` for open lists**: CUE uses `[...X]` to declare an open list constrained to elements of type `X`. This allows any number of elements. The definition is closed (via `#Package`) so no extra fields can appear, but lists remain open-ended in length.

**`pkgrel!: >0`**: This combines the required marker (`!`) with a numeric bound (`>0`). It requires the field to be present AND greater than 0, accepting both `int` and `float` (CUE's `number` type) — supporting variant builds' `1.1` format.

**Regex as inline bound**: `pkgname!: =~"^[a-z0-9@._+\\-]+$"` uses CUE's regex bound operator. The `=~` prefix (without a left operand) creates a unary regex constraint — any string unified with this field must match the pattern. RE2 syntax applies (Golang-compatible). Note: the hyphen `-` is double-escaped (`\\-`) because CUE strings interpret `\-` as an escape sequence first.

**Closed structs via definitions**: `#Package` is a definition (prefixed with `#`). Definitions are closed by default — any field not listed in the definition triggers a `field not allowed` error. This is the primary defense against PKGBUILD typos and undeclared variables.

**Function bodies as strings**: Lifecycle functions (`pkgver`, `prepare`, `build`, `check`, `package`) are stored as raw strings. When importing, the script preserves the exact function body text including newlines. CUE strings support multi-line content natively — newlines within `"..."` are valid.

**`arch` list constraint**: `[..."x86_64" | "aarch64" | "any"]` declares an open list where each element must be one of the three allowed strings. This uses CUE's disjunction type syntax within a list constraint.

**`options` list constraint**: Similar to `arch` but with the full set of known `makepkg` option flags.

---

## 5. Import Script Design (`scripts/pkgbuild_to_cue.py`)

### 5.1 Purpose

Converts an existing Bash `PKGBUILD` into a CUE `package.cue` file conforming to the `#Package` definition. This is **temporary scaffolding** — needed to bootstrap the validation workflow for the 6 existing packages. It is deprecated once Phase 4 converts packages to native `package.cue`.

### 5.2 Architecture

```
PKGBUILD (Bash)
    │
    ▼
┌──────────────────────────┐
│  bash -c 'source PKGBUILD;│   Subprocess: source the PKGBUILD
│   declare -p; declare -f'  │   to resolve all variable references
└──────────┬───────────────┘
           │  declare output (text)
           ▼
┌──────────────────────────┐
│  Variable Parser          │   Parse declare -p into Python dict
│  (declare -p → dict)      │   - Arrays: declare -a vars=([0]="val" ...)
│                           │   - Strings: declare -- var="val"
│                           │   - Integers: declare -i var="1"
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Function Extractor       │   Extract function bodies via heuristic:
│  (declare -f output)      │   - pkgver(), prepare(), build(), check(), package()
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Source Parser            │   Parse source[] array into #SourceEntry list
│  (split filename::url)    │   - Detect filename::url syntax
│                           │   - Detect VCS fragments (#tag=, #commit=)
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  CUE Emitter              │   Write package.cue with correct CUE syntax
│                           │   - Strings: quoted with escaping
│                           │   - Lists: [...elem1, elem2]
│                           │   - Booleans: true/false
│                           │   - Multi-line: """...""" or inline \n
│                           │   - Wraps in package: #Package & { ... }
└──────────┬───────────────┘
           │
           ▼
       package.cue
```

### 5.3 Variable Resolution Strategy

The import script spawns a `bash` subprocess that:
1. Sets empty defaults for all `makepkg`-provided variables (`CARCH`, `srcdir`, `pkgdir`, `startdir`).
2. Sets `_deploy_aur=false`, `_demote_upstream_maintainer=false`, etc. (so `${_deploy_aur:-...}` resolves correctly).
3. Sources the PKGBUILD with `set -a` to export all variables.
4. Runs `declare -p` to dump all defined variables in machine-parseable form.
5. Runs `declare -f` to extract function definitions.

The Python side:
1. Parses `declare -p` output (same parser as the KCL import variant).
2. Filters to PKGBUILD-relevant variables and `_`-prefixed variables (excludes `BASH_*`, `OLDPWD`, etc.).
3. Maps Bash variable names to CUE field names (direct 1:1 mapping).

### 5.4 Source Array Parsing

Same logic as the KCL variant (§5.4 of [KCL-OPA-PHASE1-SCHEMA-DESIGN.md](KCL-OPA-PHASE1-SCHEMA-DESIGN.md)):

1. For each element, split on first `::`: left = filename, right = url.
2. If no `::`, the entire string is both filename and url.
3. Detect `${VAR}` references in the original PKGBUILD source array (pre-expansion) and store in `raw_url`.

### 5.5 CUE Emitter Output Format

Each imported package produces a `package.cue` file:

```cue
package archpkg

_pkg: schemas.#Package & {
    pkgname: "opendoas"
    pkgver:  "6.8.2"
    pkgrel:  1
    pkgdesc: "Run commands as super user or another user (patched version)"
    arch:    ["x86_64"]
    url:     "https://github.com/Duncaen/OpenDoas"
    license: ["custom:ISC"]
    depends: ["pam"]
    makedepends: ["git"]
    provides: ["doas"]
    conflicts: ["doas"]
    replaces: ["doas"]
    install: "opendoas.install"
    backup: ["etc/pam.d/doas"]
    source: [
        schemas.#SourceEntry & {
            url:      "git+https://github.com/Duncaen/OpenDoas.git#tag=v6.8.2"
            filename: "opendoas"
        },
        schemas.#SourceEntry & {
            url:      "change-PATH.patch"
            filename: "change-PATH.patch"
        },
        // ... more sources
    ]
    sha256sums: [
        "43b4c2de1aaa31aac1d322b98883334b864c606783c4dfb3ddbfa0d88af9332b",
        "d1784db14976a9988666d27c96cd3ab09f91c3435eb06efd01374712982ff8f8",
        // ...
    ]
    // Lifecycle functions
    pkgver: #"""
        cd "$pkgname"
        git describe --long --tags | sed 's,^v,,; s|-\(.*\)-g|.r\1.g|'
        """#
    prepare: #"""
        cd "$pkgname"

        patch -Np1 -i ../change-PATH.patch
        patch -Np1 -i ../rowhammer.patch
        // ...
        """#
    build:   #"""
        cd "$pkgname"
        ./configure --prefix=/usr --with-timestamp
        make
        """#
    package: #"""
        cd "$pkgname"
        make DESTDIR="$pkgdir" install
        install -Dm644 LICENSE -t "$pkgdir/usr/share/licenses/$pkgname"
        """#
}
```

**Multi-line string syntax**: CUE supports `#"""...#"""` for raw multi-line strings where backslashes and quotes are literal. This preserves Bash function bodies without escaping. The import script uses `#"""` when the function body exceeds one line.

**Object syntax**: Each package is an instance of `schemas.#Package` created via unification: `_pkg: schemas.#Package & { ... }`. The `&` operator unifies the concrete data with the definition, triggering validation.

### 5.6 Edge Cases

| Scenario | Handling |
|----------|----------|
| Variable references in source URLs (`${pkgname}`) | `declare -p` resolves them — store expanded value. Detect `${...}` in original PKGBUILD for `raw_url` capture. |
| Dynamic version computation (`pkgver=$(git describe)`) | Captured as function body in `pkgver` field. Snapshot of resolved value in `pkgver` field (may be stale). |
| Multi-line function bodies | Emitted as `#"""...#"""` raw strings. |
| `pkgrel=1.1` (float) for variant builds | Detected by `.` in value; emitted as `1.1` (valid CUE number). |
| Empty arrays (`optdepends=()`) | Emitted as empty list `[]` or omitted (optional field). |
| Comments within source arrays | Lost during Bash expansion. Not preserved (acceptable — renderer reconstructs from data). |
| `options=('!debug' '!strip')` | Emitted as `[..."!debug", "!strip"]`. Disjunction constraint validates values. |
| `arch=('any')` vs `arch=(any)` | Both valid Bash. `declare -p` normalizes. |
| Packages with no `source[]` | `source` field omitted. No checksum arrays. Valid per definition. |
| Boolean `_deploy_aur` default | If not set in PKGBUILD, emitted with `*false` — CUE selects false on export. |

---

## 6. Validation Wrapper (`scripts/validate-pkgbuilds-cue.sh`)

### 6.1 Purpose

Single entry point for CUE-based validation. Called by:
- Pre-commit hook
- CI `build.yml` validate job
- Local development

### 6.2 Implementation Logic

```bash
#!/bin/bash
set -euo pipefail

CUE_BIN="${CUE_BIN:-cue}"
TMPDIR="${TMPDIR:-/tmp}/cue-validate-$$"
PACKAGES_DIR="packages"
SCHEMA_FILE="schemas/arch_pkg.cue"
FAILED=0

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

mkdir -p "$TMPDIR"

# Find all PKGBUILDs
shopt -s nullglob
for pkgbuild in "$PACKAGES_DIR"/*/PKGBUILD; do
    pkg_dir="$(dirname "$pkgbuild")"
    pkg_name="$(basename "$pkg_dir")"

    cue_file="$pkg_dir/package.cue"
    if [ ! -f "$cue_file" ]; then
        python3 scripts/pkgbuild_to_cue.py "$pkgbuild" > "$TMPDIR/${pkg_name}.cue" || {
            echo "FAIL: $pkg_name — import failed"
            FAILED=1
            continue
        }
        cue_file="$TMPDIR/${pkg_name}.cue"
    fi
    CUE_FILES+=("$cue_file")
done

if [ ${#CUE_FILES[@]} -eq 0 ]; then
    echo "No PKGBUILD files found in $PACKAGES_DIR"
    exit 0
fi

# Step 1: Validate all packages against the schema
# cue vet returns non-zero on any error (type mismatch, missing required field, etc.)
if ! "$CUE_BIN" vet -c=false "$SCHEMA_FILE" "${CUE_FILES[@]}" 2>&1; then
    echo "FAIL: CUE validation errors"
    exit 1
fi

# Step 2: Export to JSON for OPA policy check (Phase 2)
# Phase 1: export is informational only
for cue_file in "${CUE_FILES[@]}"; do
    pkg_name=$(basename "$cue_file" .cue)
    "$CUE_BIN" export --out json -e _pkg "$cue_file" > "$TMPDIR/${pkg_name}.json" 2>&1 || {
        echo "WARNING: $pkg_name — export failed (may have non-concrete values)"
    }
done

echo "OK: All packages validated"
exit $FAILED
```

### 6.3 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All PKGBUILDs validated successfully |
| 1 | Validation failure (import or `cue vet` errors) |
| 2 | Prerequisites missing (`cue` binary not found) |

### 6.4 CUE CLI Commands Used

| Command | Purpose | Phase |
|---------|---------|-------|
| `cue vet -c=false schema.cue pkg.cue` | Validate without requiring concreteness | Phase 1 |
| `cue export --out json -e _pkg pkg.cue` | Export concrete JSON for OPA | Phase 2+ |

**`-c=false` flag**: By default, `cue vet` requires the result to be concrete (no incomplete values). `-c=false` allows unresolved disjunctions and optional fields to remain — useful in Phase 1 where we want structural validation without requiring every optional field to be specified.

---

## 7. Directory Structure After Phase 1 (CUE Variant)

```
.
├── schemas/
│   └── arch_pkg.cue               # NEW — CUE definition
├── scripts/
│   ├── pkgbuild_to_cue.py          # NEW — PKGBUILD → CUE import
│   ├── validate-pkgbuilds-cue.sh   # NEW — CUE validation orchestration
│   ├── pkgvar                      # existing — variable extractor (reference implementation)
│   └── ...                         # existing scripts unchanged
├── packages/
│   ├── opendoas/
│   │   ├── PKGBUILD                # unchanged
│   │   ├── package.cue             # NEW — generated by import (first run) or manually authored
│   │   └── ...                     # existing files unchanged
│   └── ...                         # other packages unchanged
├── docs/
│   ├── KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md
│   ├── KCL-OPA-PHASE1-SCHEMA-DESIGN.md             # KCL variant
│   ├── KCL-OPA-PHASE1-CUE-SCHEMA-DESIGN.md         # NEW — CUE variant (this document)
│   └── ...
└── .pre-commit-config.yaml         # updated in Phase 3
```

---

## 8. CUE vs. KCL Tradeoffs for Phase 1

This document is an orthogonal design to `KCL-OPA-PHASE1-SCHEMA-DESIGN.md`. Both satisfy the same functional requirements. The choice between them involves these tradeoffs:

| Dimension | CUE | KCL |
|-----------|-----|-----|
| **Constraint style** | Inline (bounds, regex, disjunctions embedded in types) | Separate `check` blocks with function calls |
| **Type/value unification** | `"x86_64" | "aarch64"` is both an enum and a type constraining a field | Requires `field in ["x86_64", "aarch64"]` in a separate `check` block |
| **Closedness** | Definitions (`#`) are closed by default — catches typos | `schema` is open by default — requires explicit constraints for field allowlisting |
| **Defaults** | `*false | true` — default marker in disjunctions | `field?: bool = false` — inline default syntax |
| **Required fields** | `field!: type` — explicit required marker | All fields required by default; optional with `?` |
| **CLI ecosystem** | `cue vet`, `cue export`, `cue eval`, `cue fmt` — mature tooling | `kcl run`, `kcl lint`, `kcl fmt` — growing tooling |
| **Binary size** | ~25 MB (Go static binary) | ~40 MB (Rust static binary, via LLVM) |
| **Arch repos** | `extra/cue` — in official Arch repos | Not in Arch repos — GitHub releases only |
| **Community** | CNCF Sandbox project, broader adoption | KCL-specific ecosystem, cloud-native focused |
| **Documentation** | Interactive tour, language spec, tutorials | Comprehensive docs with code examples |

**When to prefer CUE**: If you want inline constraints (no separate validation block), stronger compile-time safety through closed structs, availability in official Arch repos, and a more mature ecosystem.

**When to prefer KCL**: If you prefer explicit `check` blocks with readable error messages, schema-level comment/documentation conventions, and a Rust-based toolchain.

---

## 9. Testing Strategy

### 9.1 CUE Definition Validation Tests

| Test Case | Expected | Rationale |
|-----------|----------|-----------|
| Minimal valid package (required fields only) | Pass (`cue vet -c=false`) | Definition doesn't demand optional fields |
| `arch` with invalid value `"i686"` | Fail | Disjunction constraint `"x86_64" \| "aarch64" \| "any"` |
| `pkgname` with uppercase `"MyPackage"` | Fail | Regex constraint `=~"^[a-z0-9@._+\\-]+$"` |
| `pkgrel` as integer `1` | Pass | `>0` accepts both int and float |
| `pkgrel` as float `1.1` | Pass | `>0` applies to number type |
| `pkgrel` as string `"1"` | Fail | Type mismatch (string vs number) |
| `pkgrel` as 0 | Fail | Bound `>0` rejects zero |
| `_deploy_aur` as boolean `true` | Pass | Disjunction `*false \| true` accepts true |
| `_deploy_aur` as string `"true"` | Fail | Type mismatch (string vs bool) |
| Extra undeclared field | Fail | `#Package` is closed — no extra fields |
| Source with `filename::url` syntax | Pass | `#SourceEntry` struct handles both fields |
| Package with lifecycle functions | Pass | Functions stored as strings |
| `options` with `!strip` | Pass | In disjunction list |
| `options` with unknown value `"!foobar"` | Fail | Not in options disjunction |

### 9.2 Import Script Tests

Test against all 6 existing PKGBUILDs. Same test cases and acceptance criteria as the KCL variant (see [KCL-OPA-PHASE1-SCHEMA-DESIGN.md](KCL-OPA-PHASE1-SCHEMA-DESIGN.md) §8.2).

Acceptance: All 6 PKGBUILDs import without errors and pass `cue vet -c=false`.

---

## 10. Phase 1 Acceptance Criteria (CUE Variant)

- [ ] `schemas/arch_pkg.cue` exists and is syntactically valid (`cue vet schemas/arch_pkg.cue` succeeds).
- [ ] `scripts/pkgbuild_to_cue.py` imports all 6 existing PKGBUILDs without error.
- [ ] All 6 imported CUE files pass `cue vet -c=false schemas/arch_pkg.cue package.cue` (exit 0).
- [ ] `scripts/validate-pkgbuilds-cue.sh` runs end-to-end: discovers PKGBUILDs, imports them, validates them.
- [ ] Manual inspection confirms all 13 custom variables are captured in the output for packages that use them.
- [ ] The definition correctly rejects known-invalid inputs (tests from §9.1 pass).
- [ ] `cue export --out json` produces valid JSON for each package (Phase 2 input format).
