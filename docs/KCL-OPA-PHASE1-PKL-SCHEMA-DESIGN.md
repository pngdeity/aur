# Phase 1 (Pkl) — Pkl PKGBUILD Schema Design

**Date:** 2026-05-11
**Status:** Proposed
**Parent:** [`docs/KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md`](KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md) §3 (Pkl variant)
**Sibling:** [`docs/KCL-OPA-PHASE1-SCHEMA-DESIGN.md`](KCL-OPA-PHASE1-SCHEMA-DESIGN.md) (KCL variant), [`docs/KCL-OPA-PHASE1-CUE-SCHEMA-DESIGN.md`](KCL-OPA-PHASE1-CUE-SCHEMA-DESIGN.md) (CUE variant)
**Language:** Pkl ([pkl-lang.org](https://pkl-lang.org/main/current/index.html))

---

## 1. Purpose & Scope

Phase 1 delivers a typed data model for `PKGBUILD(5)` — the Arch Linux build description format — expressed as a Pkl module with class definitions. The schema must capture the full surface area of what a `PKGBUILD` can declare, including the 13 custom `_`-prefixed variables in use across this repository's 6 active packages.

**Why Pkl**: Pkl is an embeddable configuration language from Apple that treats types and values as unified concepts. Its distinguishing characteristics for this use case are:

- **Type constraints as predicates**: `Int(this > 0)` constrains a value in-line without a separate validation block. Pkl uses `(this > 0)` predicates on types — the `this` keyword refers to the value being constrained.
- **Amends-based inheritance**: Pkl objects use prototypical inheritance via `amends` declarations. A variant PKGBUILD can amend a base PKGBUILD, overriding only changed fields — resembling Bash `source "../base/PKGBUILD.common"`.
- **Late binding**: Object properties are lazily evaluated and late-bound, meaning `pkgname = "\(_pkgname)-git"` will re-evaluate when `_pkgname` changes — directly modeling how PKGBUILD variable references work.
- **Closed typed objects**: Classes define closed structs — no undeclared fields are permitted (unless `...` is specified). Catches typos at evaluation time.
- **Renderable output**: Pkl modules have built-in `output.text` / `output.files` properties. A converter can render the model to PKGBUILD text.
- **Imports/amends model**: Pkl's `import` + `amends` pattern naturally maps to variant PKGBUILDs that share a common base definition.

**Pkl vs. KCL vs. CUE** (conceptual mapping):

| Concept | Pkl | KCL | CUE |
|---------|-----|-----|-----|
| Schema keyword | `class Package { ... }` | `schema Package:` | `#Package: { ... }` |
| Type declaration | `field: String` | `field: str` | `field: string` |
| Constraints | `Int(this > 0)` — inline predicate | `check:` block with function calls | `>0` — inline bounds |
| Regex | `String(matches(Regex(#"^[a-z]+$"#)))` | `regex.match(field, r"^...")` in `check:` | `=~"^pattern$"` |
| Enum | `"x86_64"\|"aarch64"\|"any"` (union type) | `field in ["a","b"]` in `check:` | `"a" \| "b" \| "c"` |
| Optional | `field?: String` | `field?: str` | `field?: string` |
| Default | `field: String = "val"` | `field?: str = "val"` | `*"val" \| string` |
| Closed struct | Class (by default) | `schema` (open by default) | `#Definition` (closed by default) |
| Inheritance | `amends "base.pkl"` | N/A (use composition) | Unification `&` |
| Late binding | Yes (object properties) | No | Yes (struct fields) |
| Output | `pkl eval --format json` | `kcl run --format json` | `cue export --out json` |

**What this phase produces:**

| Artifact | Path | Purpose |
|----------|------|---------|
| Pkl module | `schemas/arch_pkg.pkl` | Typed class for all `PKGBUILD(5)` fields + custom variables |
| Pkl package files | `packages/<name>/package.pkl` | Per-package Pkl data files (Phase 4+; Phase 1 produces via import) |
| Import script | `scripts/pkgbuild_to_pkl.py` | Converts existing Bash `PKGBUILD` → Pkl `package.pkl` |
| Validation wrapper | `scripts/validate-pkgbuilds-pkl.sh` | Orchestrates import → `pkl eval` → policy check loop |

**What this phase does NOT do:**
- Does not enforce policies (that's Phase 2 — OPA/Conftest against exported JSON).
- Does not render Pkl back to PKGBUILD text (that's Phase 3).
- Does not modify any existing PKGBUILD files.

---

## 2. Pkl Schema Architecture

### 2.1 Pkl Conceptual Model

Pkl's type system is built on classes, type constraints, and the `amends` mechanism. Key concepts:

**Classes**: Define the shape of typed objects. A class body declares properties with type annotations and optional default values. Classes are closed by default — new properties cannot be added to instances.

**Type Constraints**: Written as predicates on a type. `Int(this > 0)` defines a type "integer greater than 0". The `this` keyword refers to the value being constrained. Chaining: `String(matches(Regex(#"^[a-z]+$"#)))` defines a type "string matching the given regex".

**Union Types**: Written as `A|B|C`. A property typed as `"x86_64"|"aarch64"|"any"` accepts only those literal strings. Union types serve as enums.

**Nullable Types**: Written as `String?`. Equivalent to `String|Null`. Used for optional class fields.

**Hidden Properties**: Declared with the `hidden` modifier. They are accessible within the class but omitted from rendered output and exported JSON. Custom variables that are internal to the build system (not rendered in PKGBUILD output) can use `hidden`.

**Amends**: The mechanism for creating a new object based on an existing one. `amends "base.pkl"` creates a copy of the base module's properties that can be selectively overridden. This maps naturally to variant PKGBUILDs.

**Late Binding**: Object properties are evaluated lazily and re-evaluate when their dependencies change. This means `pkgname = "\(_pkgname)-git"` will automatically update when `_pkgname` is amended to a different value.

### 2.2 Design Principles

1. **Completeness over strictness**: Every field that `PKGBUILD(5)` permits must have a home in the class, even if the type is loose (e.g., lifecycle functions stored as raw strings).
2. **Type constraints for structural validation**: Use Pkl's inline type constraints (`Int(this > 0)`, `String(matches(Regex(...)))`) for field-level validation. Cross-field validation (provides/conflicts symmetry) is deferred to OPA (Phase 2).
3. **Closed classes for typo protection**: Classes are closed by default. Undeclared fields are rejected at evaluation time.
4. **Hidden properties for metadata**: Custom `_`-prefixed variables used by `sync-package.sh` and CI, but not rendered in PKGBUILD output, are declared `hidden`.
5. **Amends for variant packages**: Variant PKGBUILDs (e.g., `amass-git` amending `amass`) can use `amends` to inherit the base definition and override only changed fields.
6. **Output renderer**: A custom `output` block generates PKGBUILD text via Pkl's [value renderer](https://pkl-lang.org/main/current/language-reference/index.html#module-output) API.

### 2.3 Module Structure

```
schemas/arch_pkg.pkl
    ├── class SourceEntry        # Source URL with filename override
    ├── class OptDependsEntry    # Optional dependency with description
    ├── class Package            # Top-level PKGBUILD class (closed struct)
    │   ├── Identity fields
    │   ├── Metadata fields
    │   ├── Relationship fields
    │   ├── Source fields
    │   ├── Config fields
    │   ├── Lifecycle functions (String fields)
    │   └── Custom variables (hidden properties)
    └── output { ... }           # Module output renderer (Phase 3 wiring)
```

### 2.4 Dependency Graph

```
          ┌────────────────┐
          │  class Package │  (top-level class)
          └───────┬────────┘
     ┌────────────┼────────────┐
     ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│SourceEntry│ │OptDepEntry│ │ type         │
│          │ │          │ │ constraints   │
│  url     │ │  name    │ │ (regex,       │
│  filename│ │  desc    │ │  bounds,      │
└──────────┘ └──────────┘ │  unions)      │
                           └──────────────┘
```

All classes are in one file. Per-package data files use `amends "schemas/arch_pkg.pkl"`.

---

## 3. Field Specification

### 3.1 Standard Fields (`PKGBUILD(5)`)

Every field defined in `PKGBUILD(5)` is present.

#### Identity & Versioning

| Field | Pkl Type | Required? | PKGBUILD(5) § | Constraint |
|-------|----------|-----------|---------------|------------|
| `pkgname` | `String` | Yes | §7.1 | `String(matches(Regex(#"^[a-z0-9@._+\-]+$"#)))` |
| `pkgver` | `String` | Yes | §7.2 | (no hyphens — enforced in OPA Phase 2) |
| `pkgrel` | `Number` | Yes | §7.3 | `Number(this > 0)` (accepts int or float for variant builds) |
| `epoch` | `Int?` | No | §7.4 | `Int(this >= 0)` when present |
| `pkgdesc` | `String` | Yes | §7.5 | |
| `changelog` | `String?` | No | §7.16 | Filename of changelog |

#### Architecture & Metadata

| Field | Pkl Type | Required? | PKGBUILD(5) § | Constraint |
|-------|----------|-----------|---------------|------------|
| `arch` | `Listing<String>` | Yes | §7.7 | Elements: `"x86_64"\|"aarch64"\|"any"` |
| `url` | `String` | Yes | §7.12 | |
| `license` | `Listing<String>` | Yes | §7.13 | |
| `groups` | `Listing<String>?` | No | §7.8 | |

#### Package Relationships

| Field | Pkl Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `depends` | `Listing<String>?` | No | §7.14.1 | Version constraints embedded in strings (e.g., `"glibc>=2.40"`) |
| `makedepends` | `Listing<String>?` | No | §7.14.2 | |
| `checkdepends` | `Listing<String>?` | No | §7.14.3 | |
| `optdepends` | `Listing<OptDependsEntry>?` | No | §7.14.4 | See §3.2 |
| `provides` | `Listing<String>?` | No | §7.15.1 | |
| `conflicts` | `Listing<String>?` | No | §7.15.2 | |
| `replaces` | `Listing<String>?` | No | §7.15.3 | |

#### Source & Integrity

| Field | Pkl Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `source` | `Listing<SourceEntry>?` | No | §7.9 | Required if no `pkgver` function |
| `sha256sums` | `Listing<String>?` | No | §7.10.1 | Exactly one checksum listing required if `source` present (enforced in OPA Phase 2) |
| `sha512sums` | `Listing<String>?` | No | §7.10.2 | |
| `sha224sums` | `Listing<String>?` | No | §7.10.3 | |
| `sha384sums` | `Listing<String>?` | No | §7.10.4 | |
| `b2sums` | `Listing<String>?` | No | §7.10.5 | |
| `validpgpkeys` | `Listing<String>?` | No | §7.10.6 | |
| `noextract` | `Listing<String>?` | No | §7.17 | |

#### Install & Config

| Field | Pkl Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `install` | `String?` | No | §7.11 | Filename of `.install` scriptlet |
| `backup` | `Listing<String>?` | No | §7.18 | |
| `options` | `Listing<String>?` | No | §7.19 | Elements constrained to known `makepkg` options (see union type in §4.1) |

#### Lifecycle Functions

All function bodies are stored as `String` fields. Pkl validates that they are strings but does not parse Bash syntax.

| Field | Pkl Type | Required? | PKGBUILD(5) § | Notes |
|-------|----------|-----------|---------------|-------|
| `pkgverFunc` | `String?` | No | §8.8 | Function body text (only for VCS packages). Named `pkgverFunc` to avoid clash with `pkgver` field. |
| `prepare` | `String?` | No | §8.9.1 | |
| `build` | `String?` | No | §8.9.2 | |
| `check` | `String?` | No | §8.9.3 | |
| `packageFunc` | `String?` | No | §8.9.4 | Named `packageFunc` to avoid clash with Pkl's `package` keyword. |

**Note on reserved word handling**: Pkl has `package` as a keyword. The `package()` function body is stored in `packageFunc`. The renderer (Phase 3) writes it as `package()` in the output. Similarly, `class` is a Pkl keyword — if any field needs to use it as a property name, backtick escaping is used (`` `class` ``).

### 3.2 Sub-Class: `OptDependsEntry`

Models entries like `'wl-clipboard: clipboard support on Wayland'`:

```pkl
class OptDependsEntry {
    /// The package name (before the ": ")
    name: String
    
    /// The description (after the ": ")
    desc: String = ""
}
```

### 3.3 Sub-Class: `SourceEntry`

Models entries like `"${pkgname}::git+https://github.com/...git#tag=v${pkgver}"`:

```pkl
class SourceEntry {
    /// Full URL including VCS fragments (#tag=, #commit=, #branch=)
    url: String
    
    /// Local filename this source will be saved as
    filename: String
    
    /// Raw unexpanded text from PKGBUILD (for rendering fidelity)
    raw_url: String?
}
```

### 3.4 Custom Variables (Repository-Specific)

All 13 `_`-prefixed variables. In Pkl, identifiers can start with `_`. Declared as `hidden` so they are accessible within the class but omitted from JSON output:

#### Orchestration Layer

| Field | Pkl Type | Default | Constraint | Used By |
|-------|----------|---------|------------|---------|
| `_deploy_aur` | `Boolean` | `false` | Mutually exclusive with `_repo_subarch` (Phase 2) | `aur-deploy.sh` |
| `_pkgname` | `String?` | — | Discriminator for variant groups | `check-pkgdesc-consistency.sh` |
| `_githubname` | `String?` | — | Pattern: `owner/repo` via `String(matches(Regex(#"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"#)))` | `generate-changelog.sh` |
| `_upstream_aur_pkg` | `String?` | — | | `sync-package.sh` |
| `_upstream_arch_repo` | `String?` | — | | `sync-package.sh` |
| `_demote_upstream_maintainer` | `Boolean` | `false` | | `sync-package.sh` |
| `_auto_merge_build` | `Boolean` | `false` | | `sync-package.sh` |
| `_use_common_gemini_settings` | `Boolean` | `false` | | `sync-package.sh` |
| `_repo_subarch` | `String?` | — | `"x86_64_v3"\|"x86_64_v4"` | `arch-builder.sh` |
| `_tag` | `String?` | — | | `sync-package.sh` |

#### Package-Local Conventions

| Field | Pkl Type | Used By |
|-------|----------|---------|
| `_npmscope` | `String?` | `jules-tools` |
| `_npmname` | `String?` | `jules-tools` |
| `_npmver` | `String?` | `jules-tools` |

**Not modeled**: `_github_api_version` (comment-based), `_target_arch` (internal shell function).

---

## 4. Pkl Class Implementation

### 4.1 Complete Module (`schemas/arch_pkg.pkl`)

```pkl
/// PKGBUILD(5) Typed Data Model (Pkl)
/// Covers 100% of the PKGBUILD(5) surface area plus repository-specific
/// _-prefixed variables defined in docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md
///
/// Usage:
///   pkl eval packages/<name>/package.pkl --format json  →  JSON for OPA
///   pkl eval packages/<name>/package.pkl                →  PKGBUILD text (Phase 3)
///
/// References:
///   - PKGBUILD(5):       https://man.archlinux.org/man/PKGBUILD.5
///   - Pkl Language Ref:  https://pkl-lang.org/main/current/language-reference/index.html
///   - Pkl Type Constraint: https://pkl-lang.org/main/current/language-reference/index.html#type-constraints

module schemas.arch_pkg

/// A single source entry, optionally renamed via filename::url syntax.
/// Example: "opendoas::git+https://github.com/Duncaen/OpenDoas.git#tag=v6.8.2"
class SourceEntry {
    /// Full URL including VCS fragments (#tag=, #commit=, #branch=)
    url: String
    
    /// Local filename this source will be saved as
    filename: String
    
    /// Raw unexpanded text from PKGBUILD source array (for rendering fidelity).
    /// Set when the import script detects `${VAR}` references before Bash expansion.
    raw_url: String?
}

/// A single optional dependency with its description.
/// PKGBUILD entry: 'wl-clipboard: clipboard support on Wayland'
class OptDependsEntry {
    /// Package name (before the ": ")
    name: String
    
    /// Description (after the ": ")
    desc: String = ""
}

/// Known makepkg option flags (PKGBUILD(5) §7.19)
typealias KnownOption = "!strip"|"!debug"|"!lto"|"!staticlibs"|"!emptydirs"
                       |"!zipman"|"!purge"|"!libtool"
                       |"staticlibs"|"zipman"|"purge"|"libtool"
                       |"strip"|"debug"|"lto"|"makeflags"|"buildflags"

/// Known architecture values (PKGBUILD(5) §7.7)
typealias KnownArchitecture = "x86_64"|"aarch64"|"any"

/// Top-level PKGBUILD class.
/// Closed by default — no undeclared properties are permitted.
class Package {
    // ── Identity & Versioning (PKGBUILD(5) §7.1-7.5, 7.16) ──
    
    /// Package name matching PKGBUILD(5) pattern
    pkgname: String(matches(Regex(#"^[a-z0-9@._+\-]+$"#)))
    
    /// Software version number
    pkgver: String
    
    /// Packaging revision index. Positive number, floats allowed for variant builds (e.g., 1.1).
    pkgrel: Number(this > 0)
    
    /// Epoch (only set when version numbering changes)
    epoch: Int(this >= 0)?
    
    /// Package description
    pkgdesc: String
    
    /// Changelog filename
    changelog: String?
    
    // ── Architecture & Metadata (PKGBUILD(5) §7.7, 7.8, 7.12, 7.13) ──
    
    /// Target architectures
    arch: Listing<KnownArchitecture>
    
    /// Upstream URL
    url: String
    
    /// Software licenses
    license: Listing<String>
    
    /// Package groups (rarely used)
    groups: Listing<String>?
    
    // ── Package Relationships (PKGBUILD(5) §7.14, 7.15) ──
    
    /// Runtime dependencies
    depends: Listing<String>?
    
    /// Build-time dependencies
    makedepends: Listing<String>?
    
    /// Test-only dependencies
    checkdepends: Listing<String>?
    
    /// Optional dependencies with descriptions
    optdepends: Listing<OptDependsEntry>?
    
    /// Virtual packages provided
    provides: Listing<String>?
    
    /// Conflicting packages
    conflicts: Listing<String>?
    
    /// Replaced packages
    replaces: Listing<String>?
    
    // ── Source & Integrity (PKGBUILD(5) §7.9, 7.10, 7.17) ──
    
    /// Download sources
    source: Listing<SourceEntry>?
    
    sha256sums: Listing<String>?
    sha512sums: Listing<String>?
    sha224sums: Listing<String>?
    sha384sums: Listing<String>?
    b2sums:     Listing<String>?
    
    /// Valid PGP key fingerprints
    validpgpkeys: Listing<String>?
    
    /// Source files to not extract
    noextract: Listing<String>?
    
    // ── Install & Config (PKGBUILD(5) §7.11, 7.18, 7.19) ──
    
    /// .install scriptlet filename
    install: String?
    
    /// Configuration files to preserve on upgrade
    backup: Listing<String>?
    
    /// makepkg option flags
    options: Listing<KnownOption>?
    
    // ── Lifecycle Functions (PKGBUILD(5) §8.8-8.9) ──
    // Stored as raw Bash text. Named with "Func" suffix to avoid Pkl keyword conflicts.
    
    /// pkgver() dynamic version function (VCS packages only)
    pkgverFunc: String?
    
    /// prepare() — source preparation
    prepare: String?
    
    /// build() — compilation
    build: String?
    
    /// check() — test suite
    check: String?
    
    /// package() — packaging. Named "packageFunc" because "package" is a Pkl keyword.
    packageFunc: String?
    
    // ── Custom Variables (Repository-Specific) ──
    // Declared as "hidden" — accessible within the class, omitted from JSON output.
    // These drive build system behavior but are not part of the rendered PKGBUILD.
    
    /// AUR deployment gate. Mutually exclusive with _repo_subarch.
    hidden _deploy_aur: Boolean = false
    
    /// Canonical software name (without variant suffix). Discriminator for variant groups.
    hidden _pkgname: String?
    
    /// GitHub owner/repo for changelog generation
    hidden _githubname: String(matches(Regex(#"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"#)))?
    
    /// AUR package name for upstream merge
    hidden _upstream_aur_pkg: String?
    
    /// Arch GitLab repo path for upstream merge
    hidden _upstream_arch_repo: String?
    
    /// Convert upstream maintainer to contributor
    hidden _demote_upstream_maintainer: Boolean = false
    
    /// Auto-adopt upstream build logic changes
    hidden _auto_merge_build: Boolean = false
    
    /// Synchronize shared gemini settings asset
    hidden _use_common_gemini_settings: Boolean = false
    
    /// Sub-architecture target (variant builds only)
    hidden _repo_subarch: ("x86_64_v3"|"x86_64_v4")?
    
    /// Custom tag pattern for changelog generation
    hidden _tag: String?
    
    // ── Package-Local Conventions ──
    
    /// npm package scope (e.g., "@google")
    hidden _npmscope: String?
    
    /// npm package name
    hidden _npmname: String?
    
    /// npm pinned version
    hidden _npmver: String?
}
```

### 4.2 Design Notes

**`Listing<T>` vs. `List<T>`**: Pkl recommends `Listing` for literal data specification (lazy, amendable) and `List` for computed/transformed data (eager). Our schema uses `Listing` because package data is written literally in `package.pkl` files. The similarity to `PKGBUILD` array syntax is coincidental but convenient.

**`Number(this > 0)` for `pkgrel`**: Pkl's `Number` type is the common supertype of `Int` and `Float`. The constraint `this > 0` ensures positivity. This naturally accepts both `1` (integer) and `1.1` (float for variant builds).

**Regex via `Regex(#"..."#)`**: Pkl uses custom string delimiters (`#"..."#`) for regex patterns to avoid double-escaping. The `Regex` constructor expects a regex pattern string. The `String(matches(Regex(...)))` constraint ensures the string matches the pattern.

**`Type?` for optional fields**: The `?` suffix creates a nullable type (`String?` means `String|Null`). Unset optional properties default to `null`.

**`hidden` for build-system metadata**: Custom `_`-prefixed variables drive `sync-package.sh`, `aur-deploy.sh`, and CI behavior. They are not part of the rendered PKGBUILD output. The `hidden` modifier excludes them from `output` rendering and JSON export — this is correct for variables like `_deploy_aur`, `_pkgname`, `_githubname`, etc.

**`typealias` for known value sets**: `KnownArchitecture` and `KnownOption` are union type aliases defining the allowed string literals. They improve readability and are reusable across the schema.

**Reserved word handling**: In PKGBUILD, `package()` is a lifecycle function. In Pkl, `package` is a keyword. The class field is named `packageFunc` — the renderer (Phase 3) maps it to `package()` in output. No field uses `class` as a property name, but if one did (e.g., a software with "class" in its package name), backtick escaping (`` `class` ``) would be used.

---

## 5. Import Script Design (`scripts/pkgbuild_to_pkl.py`)

### 5.1 Purpose

Converts an existing Bash `PKGBUILD` into a Pkl `package.pkl` file conforming to the `Package` class. **Temporary scaffolding** — deprecated once Phase 4 converts packages to native `package.pkl`.

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
│  (declare -p → dict)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Function Extractor       │   Extract function bodies via declare -f
│                           │   - Map pkgver → pkgverFunc
│                           │   - Map package → packageFunc
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Source Parser            │   Parse source[] array into SourceEntry list
│  (split filename::url)    │   - Detect filename::url syntax
│                           │   - Capture raw_url for variable references
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Pkl Emitter              │   Write package.pkl with correct Pkl syntax
│                           │   - Strings: quoted with escaping
│                           │   - Listings: new { ... } blocks
│                           │   - Multi-line: """...""" strings
│                           │   - Booleans: true/false
│                           │   - amends header to schemas/arch_pkg.pkl
└──────────┬───────────────┘
           │
           ▼
       package.pkl
```

### 5.3 Variable Resolution

Same strategy as the KCL and CUE variants: spawn a `bash` subprocess, source the PKGBUILD, capture `declare -p` and `declare -f` output, parse into Python objects, emit as Pkl.

### 5.4 Pkl Emitter Output Format

Each imported package produces a `package.pkl` file using Pkl's amends syntax:

```pkl
/// opendoas — Run commands as super user or another user (patched version)
/// Auto-generated from PKGBUILD. Do not edit manually.
amends "schemas/arch_pkg.pkl"

pkgname = "opendoas"
pkgver = "6.8.2"
pkgrel = 1
pkgdesc = "Run commands as super user or another user (patched version)"
arch = new Listing { "x86_64" }
url = "https://github.com/Duncaen/OpenDoas"
license = new Listing { "custom:ISC" }
depends = new Listing { "pam" }
makedepends = new Listing { "git" }
provides = new Listing { "doas" }
conflicts = new Listing { "doas" }
replaces = new Listing { "doas" }
install = "opendoas.install"
backup = new Listing { "etc/pam.d/doas" }

source = new Listing {
    new SourceEntry {
        url = "git+https://github.com/Duncaen/OpenDoas.git#tag=v6.8.2"
        filename = "opendoas"
    }
    new SourceEntry {
        url = "change-PATH.patch"
        filename = "change-PATH.patch"
    }
    // ... more sources
}

sha256sums = new Listing {
    "43b4c2de1aaa31aac1d322b98883334b864c606783c4dfb3ddbfa0d88af9332b"
    "d1784db14976a9988666d27c96cd3ab09f91c3435eb06efd01374712982ff8f8"
    // ... more checksums
}

pkgverFunc = """
    cd "$pkgname"
    git describe --long --tags | sed 's,^v,,; s|-\(.*\)-g|.r\1.g|'
    """
prepare = """
    cd "$pkgname"
    
    patch -Np1 -i ../change-PATH.patch
    patch -Np1 -i ../rowhammer.patch
    // ...
    """
build = """
    cd "$pkgname"
    ./configure --prefix=/usr --with-timestamp
    make
    """
packageFunc = """
    cd "$pkgname"
    make DESTDIR="$pkgdir" install
    install -Dm644 LICENSE -t "$pkgdir/usr/share/licenses/$pkgname"
    """
```

**`amends` declaration**: `amends "schemas/arch_pkg.pkl"` tells Pkl this module inherits the `Package` class structure. All property values are validated against the class definition. This is equivalent to `object = (schemas.arch_pkg.Package) { ... }` but more idiomatic.

**Multi-line strings**: Pkl uses triple-double-quote (`"""..."""`) for multi-line string literals. The indentation of the closing `"""` controls the common leading whitespace that is stripped from each content line — this is identical to how the PKGBUILD renderer will format function bodies.

**`new Listing { ... }`**: For non-null Listing fields, elements are specified using `new Listing { ... }` blocks. The renderer (Phase 3) converts these to Bash array syntax `('elem1' 'elem2')`.

### 5.5 Edge Cases

| Scenario | Handling |
|----------|----------|
| Variable references in source URLs (`${pkgname}`) | `declare -p` resolves them; `raw_url` captures pre-expansion text |
| Dynamic `pkgver` computation | Captured as `pkgverFunc` body; `pkgver` field holds snapshot |
| Multi-line function bodies | Emitted as `"""..."""` strings |
| `pkgrel=1.1` (float) for variant builds | Emitted as `1.1` (valid Pkl Float) |
| Empty arrays (`optdepends=()`) | Emitted as `optdepends = null` or omitted (optional field) |
| Comments within source arrays | Lost during Bash expansion (acceptable) |
| `options=('!debug' '!strip')` | Emitted as `new Listing { "!debug"; "!strip" }` |
| `arch=('any')` vs `arch=(any)` | `declare -p` normalizes both |
| Reserved Pkl keywords | `package` → `packageFunc`, `class` → escaped as `` `class` `` |
| `changelog` field | Emitted as `changelog = "filename"` (string, not file reference) |

---

## 6. Validation Wrapper (`scripts/validate-pkgbuilds-pkl.sh`)

### 6.1 Purpose

Single entry point for Pkl-based validation. Called by pre-commit hook, CI validate job, and local development.

### 6.2 Implementation Logic

```bash
#!/bin/bash
set -euo pipefail

PKL_BIN="${PKL_BIN:-pkl}"
TMPDIR="${TMPDIR:-/tmp}/pkl-validate-$$"
PACKAGES_DIR="packages"
SCHEMA_FILE="schemas/arch_pkg.pkl"
FAILED=0

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

mkdir -p "$TMPDIR"

# Find all PKGBUILDs
shopt -s nullglob
for pkgbuild in "$PACKAGES_DIR"/*/PKGBUILD; do
    pkg_dir="$(dirname "$pkgbuild")"
    pkg_name="$(basename "$pkg_dir")"

    pkl_file="$pkg_dir/package.pkl"
    if [ ! -f "$pkl_file" ]; then
        python3 scripts/pkgbuild_to_pkl.py "$pkgbuild" > "$TMPDIR/${pkg_name}.pkl" || {
            echo "FAIL: $pkg_name — import failed"
            FAILED=1
            continue
        }
        pkl_file="$TMPDIR/${pkg_name}.pkl"
    fi
    PKL_FILES+=("$pkl_file")
done

if [ ${#PKL_FILES[@]} -eq 0 ]; then
    echo "No PKGBUILD files found in $PACKAGES_DIR"
    exit 0
fi

# Step 1: Validate all packages
# pkl eval validates type constraints and produces output.
# Exit non-zero on evaluation error.
for pkl_file in "${PKL_FILES[@]}"; do
    pkg_name=$(basename "$pkl_file" .pkl)
    if ! "$PKL_BIN" eval "$pkl_file" --format json > "$TMPDIR/${pkg_name}.json" 2>&1; then
        echo "FAIL: $pkg_name — Pkl validation error"
        FAILED=1
    fi
done

if [ $FAILED -ne 0 ]; then
    exit 1
fi

# Step 2: Export combined JSON manifest for OPA (Phase 2)
# Merge individual package JSON files into a combined array
echo "[" > "$TMPDIR/manifest.json"
first=true
for json_file in "$TMPDIR"/*.json; do
    if [ "$first" = true ]; then first=false; else echo "," >> "$TMPDIR/manifest.json"; fi
    if [ "$(wc -c < "$json_file")" -gt 0 ]; then
        cat "$json_file" >> "$TMPDIR/manifest.json"
    fi
done
echo "]" >> "$TMPDIR/manifest.json"

echo "OK: All packages validated"
echo "Manifest: $TMPDIR/manifest.json"
exit 0
```

### 6.3 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All PKGBUILDs validated successfully |
| 1 | Validation failure (import or `pkl eval` errors) |
| 2 | Prerequisites missing (`pkl` binary not found) |

### 6.4 Pkl CLI Commands Used

| Command | Purpose | Phase |
|---------|---------|-------|
| `pkl eval --format json package.pkl` | Evaluate module and export as JSON | Phase 1+ |
| `pkl eval --format pcf package.pkl` | Evaluate module and export as PCF | Phase 3 (renderer input) |

**`--format json`**: Produces JSON output suitable for OPA/Conftest consumption. Hidden properties (custom `_`-prefixed variables) are excluded from JSON output by default — which is correct behavior for the validation layer (these are build-system metadata, not PKGBUILD content).

---

## 7. Directory Structure After Phase 1 (Pkl Variant)

```
.
├── schemas/
│   └── arch_pkg.pkl               # NEW — Pkl module with Package class
├── scripts/
│   ├── pkgbuild_to_pkl.py          # NEW — PKGBUILD → Pkl import
│   ├── validate-pkgbuilds-pkl.sh   # NEW — Pkl validation orchestration
│   ├── pkgvar                      # existing — variable extractor (reference implementation)
│   └── ...                         # existing scripts unchanged
├── packages/
│   ├── opendoas/
│   │   ├── PKGBUILD                # unchanged
│   │   ├── package.pkl             # NEW — generated by import (first run) or manually authored
│   │   └── ...                     # existing files unchanged
│   └── ...                         # other packages unchanged
├── docs/
│   ├── KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md
│   ├── KCL-OPA-PHASE1-SCHEMA-DESIGN.md             # KCL variant
│   ├── KCL-OPA-PHASE1-CUE-SCHEMA-DESIGN.md         # CUE variant
│   ├── KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md         # NEW — Pkl variant (this document)
│   └── ...
└── .pre-commit-config.yaml         # updated in Phase 3
```

---

## 8. Pkl Suitability Assessment

### 8.1 Strengths for This Use Case

| Strength | Relevance |
|----------|-----------|
| **Late binding** | Directly models PKGBUILD variable references — `pkgname = "\(_pkgname)-git"` automatically stays in sync |
| **Amends/inheritance** | Variant PKGBUILDs naturally use `amends` to inherit base fields and override specific ones |
| **Type constraints inline** | `Number(this > 0)`, `String(matches(Regex(...)))` — no separate validation block needed |
| **Closed classes** | Catches undeclared fields at evaluation time |
| **Hidden properties** | Custom `_`-prefixed variables are hidden from JSON output — exactly the right semantics |
| **Multi-format output** | `--format json` for OPA, `--format pcf` for the renderer, custom `output` for PKGBUILD text |
| **Homebrew/CLI availability** | `brew install pkl` on macOS/Linux; native binaries via GitHub releases |
| **IDE support** | IntelliJ, VS Code, Neovim plugins with autocomplete and inline error reporting |

### 8.2 Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Not in Arch repos** | Requires downloading native binary from GitHub releases | `scripts/install-validator-tools.sh` handles download; binary is self-contained |
| **`package` is a reserved word** | PKGBUILD's `package()` function needs mapping | Store as `packageFunc`; renderer outputs `package()` |
| **`Listing` to `List` impedance** | Pkl uses its own collection types | No issue — `Listing` maps 1:1 to Bash array semantics |
| **Late binding may surprise** | Amending a parent object changes child objects | This is actually a strength — it matches how PKGBUILD variables work |
| **JVM dependency for Java executable** | Native executable is preferred but not available for all platforms | Linux amd64 native binary exists; Alpine Linux native binary exists; aarch64 Linux native binary exists |

### 8.3 Pkl vs. KCL vs. CUE (Full Comparison)

| Dimension | Pkl | KCL | CUE |
|-----------|-----|-----|-----|
| **Constraint style** | Inline on type (`Int(this > 0)`) | `check:` block with function calls | Inline bounds (`>0`), regex (`=~`) |
| **Schema keyword** | `class Package { }` | `schema Package:` | `#Package: { }` |
| **Late binding** | Yes (object properties) | No | Yes (struct unification) |
| **Inheritance** | `amends` (prototypical) | Composition only | Unification `&` |
| **Closedness** | Classes closed by default | `schema` open by default | Definitions (`#`) closed by default |
| **Regex** | `String(matches(Regex(#"..."#)))` — RE2 | `regex.match()` in check block | `=~"pattern"` — RE2 |
| **Nullable/optional** | `String?` (with `?` suffix) | `field?: str` | `field?: string` |
| **Default values** | `field: Type = default` | `field?: type = default` | `*default \| type` |
| **Hidden metadata** | `hidden property` modifier | No built-in concept | Definitions are separate from data |
| **CLI binary** | Native (macOS/Linux/Windows) + Java jar | Rust binary | Go binary |
| **In Arch repos** | No (brew/download) | No (download) | Yes (`extra/cue`) |
| **IDE support** | IntelliJ, VS Code, Neovim + LSP | VS Code plugin | Limited editor support |
| **Maturity** | Apple-backed, v0.31.1 | CNCF Sandbox, v0.12 | CNCF Sandbox, v0.11 |
| **Documentation** | Comprehensive user manual + tutorial + API docs | Comprehensive docs + examples | Interactive tour + language spec |

### 8.4 Recommendation

Pkl is well-suited for this use case, particularly if variant PKGBUILDs are common. Its `amends` inheritance model naturally maps to variant packages that share a base definition. The late binding semantics directly model how `PKGBUILD(5)` variable references work. The main drawback is that Pkl is not in Arch repos, requiring binary download — but this is a one-time CI setup cost.

**When to prefer Pkl over KCL or CUE**:
- When variant packages will use `amends` to inherit from base definitions
- When late-bound variable references (like `${_pkgname}-git`) are common
- When `hidden` property semantics (internal metadata omitted from output) is valuable
- When native CLI performance matters (Pkl's native binaries start instantly)

---

## 9. Testing Strategy

### 9.1 Pkl Class Validation Tests

| Test Case | Expected | Rationale |
|-----------|----------|-----------|
| Minimal valid package (required fields only) | Pass (`pkl eval` exit 0) | Class doesn't demand optional fields |
| `arch` with invalid value `"i686"` | Fail | Union type `"x86_64"\|"aarch64"\|"any"` |
| `pkgname` with uppercase `"MyPackage"` | Fail | Regex constraint |
| `pkgrel` as integer `1` | Pass | `Number(this > 0)` accepts int |
| `pkgrel` as float `1.1` | Pass | `Number(this > 0)` accepts float |
| `pkgrel` as string `"1"` | Fail | Type mismatch (String vs Number) |
| `pkgrel` as 0 | Fail | `this > 0` rejects zero |
| `_deploy_aur` set to `true` | Pass | Boolean field, hidden |
| `_deploy_aur` set to string `"true"` | Fail | Type mismatch |
| Extra undeclared field | Fail | Class is closed |
| Source with `filename::url` syntax | Pass | `SourceEntry` class handles both fields |
| Package with lifecycle functions | Pass | Functions stored as strings |
| `options` with `!strip` | Pass | In `KnownOption` typealias |
| `options` with unknown value `"!foobar"` | Fail | Not in union type |
| Hidden property exclusion in JSON | Pass | `hidden` properties not in `--format json` output |

### 9.2 Import Script Tests

Test against all 6 existing PKGBUILDs. Same test cases and acceptance criteria as the KCL variant.

Acceptance: All 6 PKGBUILDs import without errors and pass `pkl eval --format json`.

---

## 10. Phase 1 Acceptance Criteria (Pkl Variant)

- [ ] `schemas/arch_pkg.pkl` exists and is syntactically valid (`pkl eval` succeeds).
- [ ] `scripts/pkgbuild_to_pkl.py` imports all 6 existing PKGBUILDs without error.
- [ ] All 6 imported Pkl files pass `pkl eval --format json` (exit 0, valid JSON output).
- [ ] `scripts/validate-pkgbuilds-pkl.sh` runs end-to-end: discovers PKGBUILDs, imports them, validates them.
- [ ] Manual inspection confirms all 13 custom variables are captured in the output for packages that use them (accessible within the module even if hidden from JSON output).
- [ ] The class correctly rejects known-invalid inputs (tests from §9.1 pass).
- [ ] `pkl eval --format json` produces valid, complete JSON for each package (Phase 2 input format).
