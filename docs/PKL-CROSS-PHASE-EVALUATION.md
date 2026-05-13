# Pkl Cross-Phase Evaluation — PKGBUILD Validation Architecture

**Date:** 2026-05-13
**Status:** Proposed
**Parent:** [`docs/KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md`](KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md)
**Sibling:** [`docs/KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md`](KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md) (Phase 1 only — schema design)
**Language Evaluated:** Pkl v0.31.1 ([pkl-lang.org](https://pkl-lang.org))

---

## 0. Executive Summary

This document evaluates Pkl against the full set of functional requirements defined in the KCL+OPA validation architecture (Phases 1–3), complementing the Phase-1-only schema design already documented in `KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md`.

**Verdict per phase:**

| Phase | Pkl Suitability | Key Differentiator vs. KCL |
|-------|----------------|---------------------------|
| Phase 1 (Schema) | Strong — superior | Late binding + amends + hidden properties |
| Phase 2 (Policy) | Adequate — still needs OPA | Pkl type constraints cover 3 of 12 rules natively (vs. KCL's 2) |
| Phase 3 (Renderer) | Strong — simplifies | `output.text` eliminates Python renderer script |

**Decision:** Pkl is selected over KCL and CUE (see §7 for rationale). The Pkl schema design in `KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md` becomes the canonical Phase 1 reference. KCL and CUE variant documents are retained as design alternatives and rationale artifacts.

**Architectural impact:** Pkl reduces the toolchain from 3 languages (KCL + OPA/Rego + Python renderer) to 2 (Pkl + OPA/Rego). The Python import script remains necessary for bootstrapping but the renderer is eliminated.

---

## 1. Phase 1 — Schema Design: Detailed Analysis

### 1.1 Requirements Recap

| # | Requirement | Source |
|---|------------|--------|
| R1 | Typed data model covering 100% of `PKGBUILD(5)` surface area | Phase 1 §3 |
| R2 | 13 custom `_`-prefixed variables | Phase 1 §3.4 |
| R3 | Closed structs — reject undeclared fields | Phase 1 §2.1 |
| R4 | Regex constraints on `pkgname` (`[a-z0-9@._+-]`) | Phase 1 §3.1 |
| R5 | Enum constraints on `arch` (`x86_64`, `aarch64`, `any`) | Phase 1 §3.1 |
| R6 | Union type on `pkgrel` (`int | float`) for variant builds | Phase 1 §3.1 |
| R7 | Optional fields with defaults | Phase 1 §3.1 |
| R8 | `SourceEntry` sub-schema with `filename::url` parsing | Phase 1 §3.3 |
| R9 | `OptDependsEntry` sub-schema (`name: desc`) | Phase 1 §3.2 |
| R10 | Lifecycle functions stored as raw multi-line strings | Phase 1 §3.1 |
| R11 | Export to JSON for OPA consumption | Phase 1 §2 |
| R12 | Import script to bootstrap from existing PKGBUILDs | Phase 1 §5 |
| R13 | JSON export excludes build-system metadata (`_`-prefixed vars) | Phase 1 §3.4 (implied) |

### 1.2 Pkl vs. KCL: Feature Matrix

| Requirement | Pkl | KCL | Winner |
|-------------|-----|-----|--------|
| R1 — Typed model | `class Package { ... }` | `schema Package:` | Tie |
| R2 — Custom vars | `hidden _deploy_aur: Boolean?` | `_deploy_aur?: bool = False` | **Pkl** — `hidden` excludes from JSON |
| R3 — Closed structs | Classes closed by default | `schema` open by default | **Pkl** — catches typos at eval time |
| R4 — Regex | `String(matches(Regex(#"^[a-z0-9@._+\-]+$"#)))` | `regex.match(pkgname, r"...")` in `check:` | Tie |
| R5 — Enum | `"x86_64"\|"aarch64"\|"any"` (union type) | `a in ["x86_64", "aarch64", "any"]` in `check:` | **Pkl** — inline, no separate block |
| R6 — Union type | `Number(this > 0)` (Number=Int\|Float) | `int \| float` | Tie |
| R7 — Optional/defaults | `_deploy_aur: Boolean? = false` | `_deploy_aur?: bool = False` | Tie |
| R8 — SourceEntry | `class SourceEntry { url: String; filename: String }` | `schema SourceEntry:` | Tie |
| R9 — OptDependsEntry | `class OptDependsEntry { name: String; desc: String }` | `schema OptDependsEntry:` | Tie |
| R10 — Raw functions | `prepare: String?` (multiline) | `prepare?: str` | Tie |
| R11 — JSON export | `pkl eval --format json` | `kcl run --format json` | Tie |
| R12 — Import script | Python subprocess (same approach) | Python subprocess | Tie |
| R13 — Metadata exclusion | `hidden` — auto-excluded from JSON | All vars exported; must filter post-hoc | **Pkl** |

**Score: Pkl 4, KCL 0, Tie 9** — Pkl wins on metadata hygiene, closed structs, enum style, and hidden properties.

### 1.3 Pkl's Differentiating Features

#### Late Binding

Pkl object properties are late-bound — changing a dependency re-evaluates dependents. This directly models how PKGBUILD variable references work:

```pkl
// schemas/arch_pkg.pkl
class Package {
  _pkgname: String?
  pkgname: String = if (_pkgname != null) "\(_pkgname)-git" else name
  name: String
  pkgver: String
}
```

```pkl
// packages/opencode-git/package.pkl
amends "schemas/arch_pkg.pkl"

_opencode = new Package {
  _pkgname = "opencode"
  name = "opencode"
  pkgver = "0.14.0"
}

opencodeGit = (_opencode) {
  // pkgname auto-computes to "opencode-git" via late binding
}
```

KCL has no late binding — variable references must be resolved statically by the import script. Pkl's late binding means you change `_pkgname` in one place and all derived fields update automatically, exactly like Bash `source` semantics.

#### Amends (Prototypical Inheritance)

Variant PKGBUILDs (e.g., `amass-bin` vs `amass`) share most fields and override a few. Pkl's `amends` mechanism is a natural fit:

```pkl
// packages/amass/package.pkl
amass: Package {
  pkgname = "amass"
  pkgver = "4.3.0"
  pkgdesc = "In-depth DNS Enumeration and Network Mapping"
  arch = "x86_64"|"aarch64"
  makedepends = new Listing<String> { "go" }
  ...
}
```

```pkl
// packages/amass-bin/package.pkl
import "packages/amass/package.pkl"

amassBin = (amass) { (1)
  pkgname = "amass-bin" (2)
  provides = new Listing<String> { "amass" }
  conflicts = new Listing<String> { "amass" }
  // All other fields inherited from amass
}
```

**1** Amends expression — creates `amassBin` from `amass`, overriding only specified fields.

**2** Overrides `pkgname`; late binding means any field referencing `pkgname` also updates.

KCL requires composition for variant packages — manually listing all shared fields. CUE uses unification, which is powerful but can produce confusing error messages when constraints conflict.

#### Hidden Properties

The 13 custom `_`-prefixed variables are build-system metadata, not PKGBUILD content. Pkl's `hidden` modifier automatically excludes them from rendered output and JSON export:

```pkl
class Package {
  // PKGBUILD content — exported
  pkgname: String
  pkgver: String
  ...

  // Build-system metadata — hidden from JSON
  hidden _deploy_aur: Boolean = false
  hidden _pkgname: String?
  hidden _githubname: String?
  hidden _upstream_aur_pkg: String?
  hidden _upstream_arch_repo: String?
  hidden _demote_upstream_maintainer: Boolean = false
  hidden _auto_merge_build: Boolean = false
  hidden _use_common_gemini_settings: Boolean = false
  hidden _repo_subarch: String?
  hidden _tag: String?
  hidden _npmscope: String?
  hidden _npmname: String?
  hidden _npmver: String?
}
```

When `pkl eval --format json` runs, hidden properties are absent from the output. This is exactly the right semantic: OPA/Conftest should never see internal build-system metadata. With KCL, all fields are exported and must be filtered post-hoc.

#### `package` Keyword Collision

Pkl reserves `package` as a keyword (module declaration). The PKGBUILD lifecycle function `package()` must use an alias:

```pkl
class Package {
  // ...
  packageFunc: String?  // NOT package: — reserved word
}
```

The import script maps `package()` → `packageFunc` and the renderer reverses the mapping. This is a minor impedance mismatch — documented, mechanical, and handled entirely by the import/render pipeline.

### 1.4 Import Script Strategy

Same approach as KCL: a Python script (`scripts/pkgbuild_to_pkl.py`) that:

1. Spawns a `bash` subprocess to source the PKGBUILD and dump resolved variables via `declare -p` and `declare -f`
2. Parses the declare output into a Python dict
3. Emits a Pkl module with a `Package` instance

The key difference from the KCL import: Pkl's late binding means the import script should store **both** resolved and raw values for source URLs. The Pkl class can then reconstruct variable references:

```pkl
class SourceEntry {
  url: String
  filename: String
  raw_url: String?  // Original unexpanded Bash string (for rendering fidelity)
}
```

This is identical to the `raw_url` field added in the KCL Phase 3 renderer design (§2.5).

---

## 2. Phase 2 — Policy Engine: Analysis

### 2.1 The Fundamental Constraint

Pkl is a configuration language with type validation, **not** a policy engine. It has no equivalent to OPA's Rego — no `deny`/`warn` rule semantics, no structured violation messages, no cross-package aggregation, no exception mechanism, and no content-scanning capabilities for lifecycle functions.

**Phase 2 still requires OPA/Conftest regardless of whether the schema language is KCL, CUE, or Pkl.**

### 2.2 Policy Rules: What Pkl Can Handle Natively

| Rule | Pkl Native? | Implementation | Notes |
|------|-------------|----------------|-------|
| 1. `enforce_https` | No | — | Requires URL protocol parsing + iteration over source array |
| 2. `privilege_escalation` | No | — | Requires regex scanning of function body strings |
| 3. `architecture_mismatch` | Partial | Type constraint on `arch` prevents invalid values; cross-field check (arch="any" + arch-specific deps) needs OPA | Pkl handles structural part; OPA for semantic |
| 4. `no_unprovided_conflicts` | No | — | Cross-field iteration: `conflicts[i] ∈ provides` |
| 5. `no_self_reference` | Partial | Could express as: `conflicts contains pkgname == false` via iteration, but OPA gives better error messages | Pkl feasible but OPA preferred |
| 6. `deploy_aur_subarch_mutex` | **Yes** | Type constraint: `_deploy_aur == true → _repo_subarch == null` | Pkl can express as a `fixed` derived check |
| 7. `pkgdesc_consistency` | No | — | Cross-package — requires external aggregation across all packages |
| 8. `valid_architectures` | **Yes** | Union type `"x86_64"\|"aarch64"\|"any"` | Already enforced |
| 9. `required_fields` | **Yes** | Non-optional fields on class | Already enforced |
| 10. `source_integrity` | Partial | Can enforce checksum array presence; length equality requires iteration | Partial Pkl; OPA for completeness |
| 11. `vcs_skip` | No | — | Requires URL protocol parsing |
| 12. `maintainer_present` | No | — | KCL schema doesn't model comments; same limitation for Pkl |

**Pkl covers 3 of 12 rules at the schema level** (rules 6, 8, 9), versus KCL's 2 (rules 8, 9). Rule 6 (`deploy_aur_subarch_mutex`) can be expressed as a Pkl type constraint because it's a simple cross-field conditional, whereas KCL expresses it in a `check:` block.

### 2.3 JSON Export Contract for OPA

Pkl exports the same JSON structure that OPA expects:

```bash
pkl eval --format json packages/*/package.pkl > manifest.json
conftest test manifest.json -p policies/
```

The JSON output of `pkl eval --format json` is identical in structure to `kcl run --format json` — an array of `Package` objects with the same field names and types. OPA/Conftest is agnostic to which tool produced the JSON.

**Hidden properties are automatically excluded** — Pkl's `hidden` modifier ensures build-system metadata never reaches OPA. This is correct behavior: OPA rules should audit PKGBUILD content, not internal variables like `_deploy_aur` or `_githubname`. (Exception: rule 6 needs `_deploy_aur` and `_repo_subarch` — these could be made non-hidden for OPA visibility or handled as a Pkl-native constraint.)

### 2.4 Exception Mechanism

The exception mechanism described in Phase 2 §4 relies on Conftest's built-in `exception` rule pattern. This works identically whether the JSON comes from KCL or Pkl — Conftest operates on the JSON manifest, not the source language.

Per-package `policy_exceptions.yaml` files remain unchanged. The validation wrapper (`validate-pkgbuilds.sh`) feeds them to Conftest via `--data` flags.

---

## 3. Phase 3 — Renderer + CI: Architectural Simplification

### 3.1 Pkl Eliminates the Python Renderer

The KCL architecture requires a Python renderer (`scripts/kcl_to_pkgbuild.py`, ~489 lines) that converts KCL JSON → valid PKGBUILD text. This script handles:

- Bash string quoting (single-quote with internal escape)
- Array rendering (`('elem1' 'elem2')` syntax)
- Source array rendering (`filename::url` syntax, VCS fragments)
- Optdepends rendering (`'name: desc'` syntax)
- Function body indentation
- Field ordering per PKGBUILD convention
- Boolean rendering (`true` vs omitted)
- Variable reference preservation in source URLs

Pkl's `output.text` property can compute the final PKGBUILD as a String directly in the schema module, eliminating the need for a separate renderer program:

```pkl
// schemas/arch_pkg.pkl (excerpt)
class Package {
  // ... all fields ...

  function renderPKGBUILD(): String =
    let (maintainer = "# Maintainer: pngdeity <pngdeity@tutanota.com>")
    let (fields = new Listing<String> {
      renderStringField("pkgname", pkgname)
      if (changelog != null) renderStringField("changelog", changelog!)
      renderStringField("pkgver", pkgver)
      renderNumberField("pkgrel", pkgrel)
      // ... all fields in order ...
    })
    let (funcs = new Listing<String> {
      if (pkgverFunc != null) renderFunction("pkgver", pkgverFunc!)
      if (prepare != null) renderFunction("prepare", prepare!)
      if (build != null) renderFunction("build", build!)
      if (check != null) renderFunction("check", check!)
      if (packageFunc != null) renderFunction("package", packageFunc!) (1)
    })
    in "\(maintainer)\n\n\(fields.join("\n"))\n\n\(funcs.join("\n\n"))\n"
}
```

**1** `packageFunc` is the alias for PKGBUILD's `package()` — see §1.3 keyword collision.

The `output.text` property wires this:

```pkl
output {
  text = (pkg).renderPKGBUILD()
}
```

**Eliminated**: `scripts/kcl_to_pkgbuild.py` (~489 lines of Python). **Replaced by**: ~80–100 lines of Pkl helper methods in `schemas/arch_pkg.pkl`.

### 3.2 Comparison: KCL Pipeline vs. Pkl Pipeline

**KCL pipeline (3 languages):**

```
PKGBUILD ──► [Python import] ──► package.k ──► [KCL compile] ──► manifest.json
                                                                       │
                                                                       ▼
PKGBUILD ◄── [Python renderer] ◄── validated ◄── [OPA/Conftest test]
```

**Pkl pipeline (2 languages):**

```
PKGBUILD ──► [Python import] ──► package.pkl ──► [Pkl eval --json] ──► manifest.json
                 (bootstrap only)        │                                      │
                                         │                                      ▼
                                         ├──► [Pkl output.text] ──► PKGBUILD ◄── [OPA/Conftest test]
                                         │    (built-in renderer)
                                         │
                                         └──► pkl eval validates schema constraints inline
```

The Python import script remains (bootstrap-only, deprecated in Phase 4), but the Python renderer is eliminated entirely.

### 3.3 Phase 4 (Deferred) — Pkl as Canonical Authoring Format

If Phase 4 proceeds (go/no-go after Phase 3), Pkl's advantages compound:

1. **Import script retired**: `package.pkl` files are manually authored — no Python subprocess needed.
2. **Two-language toolchain**: Only Pkl + OPA (no Python at all).
3. **Variant inheritance via amends**: `opencode-git` amends `opencode`, overriding only `pkgname`, `source`, and `pkgver_func`. No manual field duplication.
4. **Late binding drives version bumps**: Change `pkgver` in the base package, and `pkgname = "\(_pkgname)-git"` auto-updates in the variant.

### 3.4 CI Integration

CI integration is functionally identical to the KCL plan (Phase 3 §4):

```bash
# Install Pkl + Conftest (same pattern, different binary)
curl -sSL "https://github.com/apple/pkl/releases/download/v${PKL_VERSION}/pkl-linux-amd64" \
  -o /usr/local/bin/pkl
chmod +x /usr/local/bin/pkl

# Validate
pkl eval --format json schemas/arch_pkg.pkl packages/*/package.pkl > manifest.json
conftest test manifest.json -p policies/

# Render PKGBUILD (if Phase 4)
pkl eval schemas/arch_pkg.pkl -p packages/opendoas/ > packages/opendoas/PKGBUILD
```

The `build.yml` `validate` job, `discovery.yml` gate, `.pre-commit-config.yaml` hook, and `policy-tests.yml` workflow are all structurally identical. Only the binary URL and CLI invocation change.

### 3.5 Multi-File Output (Phase 3 Advanced)

Pkl supports writing output to multiple files via `output.files`:

```pkl
output {
  files {
    ["PKGBUILD"] {
      text = (pkg).renderPKGBUILD()
    }
    [".SRCINFO"] {
      // Could also generate .SRCINFO from the same model
      text = (pkg).renderSRCINFO()
    }
  }
}
```

This maps naturally to a single `package.pkl` producing both `PKGBUILD` and `.SRCINFO` as build artifacts. The KCL architecture would require two separate Python rendering passes or an extended renderer.

---

## 4. Risk Assessment

### 4.1 Risks Specific to Pkl

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| PR1 | **`package` keyword collision** — PKGBUILD lifecycle function `package()` conflicts with Pkl's reserved keyword | Low | Certain | Use `packageFunc` field name in the class; import script and renderer handle the mapping. Transparent to end users. |
| PR2 | **Binary size** — Pkl native binary (GraalVM native image) is ~40MB vs KCL's ~25MB | Low | Certain | Download once in CI; cached. Local install is one-time. Size is immaterial for CI runners. |
| PR3 | **Not in Arch repos** — requires binary download from GitHub releases | Medium | Certain | Same as KCL and Conftest. `scripts/install-validator-tools.sh` handles download with pinned versions. |
| PR4 | **JVM dependency** — Pkl is primarily a JVM language; native binaries via GraalVM | Low | Low | Linux amd64 native binary is first-class and performs well. No JVM needed for CI or local use. aarch64 native binary also available. |
| PR5 | **Community size** — Pkl (Apple, open source) has a smaller community than KCL (CNCF Sandbox) | Low | Medium | Documentation quality is high (Apple-backed). API stability is the primary concern; Pkl has been stable across 0.25 → 0.31. |
| PR6 | **VS Code / editor support** — developers need Pkl-aware editing | Low | Medium | Pkl has IntelliJ, VS Code, and Neovim plugins with LSP support. KCL has VS Code only. |
| PR7 | **`Number` type ambiguity** — `Number` = `Int|Float`. `pkgrel` accepting float means `pkgrel=1` renders as `1` (not `1.0`) | None | N/A | `Number` correctly preserves integer vs. float distinction. `pkgrel=1` renders as `1`; `pkgrel=1.1` renders as `1.1`. |

### 4.2 Risks Shared with KCL

| Risk | Description |
|------|-------------|
| R1–R6 from master plan §7 | Dynamic `${var}` interpolation, round-trip fidelity, binary download flakiness, team unfamiliarity, `sync-package.sh` compatibility, CI latency — all apply equally to Pkl |

### 4.3 Risks Mitigated by Pkl

| KCL Risk | How Pkl Mitigates |
|----------|-------------------|
| R1 — Dynamic interpolation (`${pkgname}` in source URLs) | Pkl's late binding naturally handles this. `url = "git+https://.../\(pkgname)"` auto-expands. No risk of stale resolved values. |
| R2 — Round-trip fidelity (PKGBUILD → KCL → PKGBUILD) | Pkl's late binding preserves variable references. The `SourceEntry.raw_url` field in the KCL plan is unnecessary — Pkl evaluates `${pkgname}` correctly in context. |
| R4 — Team unfamiliarity with KCL/Rego | Pkl's syntax is closer to mainstream languages (Swift-like). Lower learning curve than KCL's Python-like `check:` blocks. Rego is still required for policy regardless. |

---

## 5. Conceptual Mapping

| KCL Concept | Pkl Equivalent |
|-------------|---------------|
| `schema Package:` | `class Package { ... }` |
| `check:` block | Inline type constraints: `Int(this > 0)`, `String(matches(Regex(...)))` |
| `field in ["a", "b"]` (enum) | `field: "a"\|"b"` (string literal union type) |
| `regex.match(f, r"...")` | `String(matches(Regex(#"..."#)))` |
| `field?: str` (optional) | `field: String?` (nullable type) |
| `field?: bool = False` (optional+default) | `field: Boolean = false` |
| `int \| float` (union type) | `Number` (common supertype of Int and Float) |
| `kcl run --format json` | `pkl eval --format json` |
| Python renderer | `output.text` + Pkl helper methods |
| No inheritance | `amends "base.pkl"` (prototypical) |
| No late binding | Object properties are late-bound by default |
| All fields exported | `hidden` modifier excludes from JSON |

---

## 6. Architecture Reduction

```
KCL-based toolchain (3 languages):
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Python  │    │   KCL    │    │ OPA/Rego │
│ (import +│    │ (schema +│    │ (policy) │
│ render)  │    │ compile) │    │          │
└──────────┘    └──────────┘    └──────────┘
     2 files         1 file         1 file
   (~800 lines)   (~300 lines)   (~530 lines)

Pkl-based toolchain (2 languages):
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Python  │    │   Pkl    │    │ OPA/Rego │
│ (import  │    │ (schema +│    │ (policy) │
│  only)   │    │ render)  │    │          │
└──────────┘    └──────────┘    └──────────┘
     1 file         1 file         1 file
   (~300 lines)  (~400 lines)   (~530 lines)
```

The Python import script shrinks (no renderer). The Pkl schema grows slightly (absorbs renderer logic). Total line count and maintenance surface decrease.

---

## 7. Recommendation

### When to Prefer Pkl over KCL

| Condition | Rationale |
|-----------|-----------|
| **Variant packages are common** | `amends` inheritance is a first-class Pkl feature; KCL requires manual composition |
| **Late-bound variable references are used** | Pkl's late binding naturally models `${var}` expansion in PKGBUILDs; KCL requires `raw_url` workarounds |
| **Hidden metadata is valued** | Pkl's `hidden` property modifier automatically excludes build-system vars from JSON; KCL exports everything |
| **Fewer tools is a priority** | Pkl eliminates the Python renderer and consolidates schema + render into one language |
| **IDE support matters** | Pkl has IntelliJ + VS Code + Neovim plugins; KCL has VS Code only |
| **Team is comfortable with Swift/TypeScript-like syntax** | Pkl syntax is familiar to developers from those ecosystems |

### When to Prefer KCL over Pkl

| Condition | Rationale |
|-----------|-----------|
| **CNCF governance matters** | KCL is a CNCF Sandbox project; Pkl is Apple-backed open source. For projects that prioritize vendor-neutral governance, KCL is the safer bet. |
| **Smaller binary is critical** | KCL's Rust binary is ~25MB vs Pkl's ~40MB native image. |
| **Python-like constraint syntax is preferred** | KCL's `check:` blocks with function calls feel familiar to Python developers; Pkl's inline type constraints are a different paradigm. |
| **No variant packages exist** | If all packages are standalone (no inheritance needed), Pkl's `amends` advantage is irrelevant. |

### Neutral — Either Works

Both Pkl and KCL:
- Export JSON for OPA/Conftest consumption (identical contract)
- Require binary download from GitHub releases (not in Arch repos)
- Support native Linux amd64 and aarch64 binaries
- Have comparable evaluation speed (<1s per package)
- Require the same CI infrastructure (Ubuntu runner, cached download)

### Decision: Pkl

**Pkl is selected as the schema language for this repository.** The decision is based on three capabilities that are directly exercised by this project's package set and that KCL lacks:

1. **Amends for variant packages.** This repo has variant sets (opencode/opencode-git, amass/amass-bin, gemini-cli/gemini-cli-git/gemini-cli-preview). Pkl's `amends` inheritance models these without field duplication. KCL requires composing every shared field manually.

2. **Late binding for variable references.** PKGBUILDs use patterns like `pkgname="${_pkgname}-git"`, `source=("${pkgname}::git+...")`, and `depends=("${_pkgname}=${pkgver}")`. Pkl's late-bound object properties re-evaluate these references when dependencies change. KCL would require `raw_url` storage and Python-side re-resolution — a workaround, not a solution.

3. **Hidden properties for build-system metadata.** This repo carries 13 `_`-prefixed variables that are internal to `sync-package.sh`, `aur-deploy.sh`, and CI. Pkl's `hidden` modifier excludes them from JSON output automatically — OPA never sees them. KCL exports all fields and requires post-hoc filtering.

The CNCF governance advantage of KCL is acknowledged but does not produce functional value for this repo. For a packaging repository shipping to the AUR, technical fit outweighs governance alignment. The Pkl binary (~40MB) is installed once in CI and cached — size is immaterial.

**Impact on existing documents:** The `KCL-OPA-PHASE1-SCHEMA-DESIGN.md` (KCL schema) is superseded. The `KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md` becomes the canonical Phase 1 reference. The Phase 2 (OPA policy engine) and Phase 3 (renderer/CI) designs in the KCL documents remain valid — only the schema language changes; the OPA policy engine, exception mechanism, and CI topology are unchanged. The `KCL-OPA-PHASE3-RENDERER-CI.md` `kcl_to_pkgbuild.py` renderer is replaced by Pkl's `output.text` — all other Phase 3 content (pre-commit hook, CI workflows, round-trip tests) applies without modification.

---

## 8. Relationship to Existing Documents

| Document | Relationship |
|----------|-------------|
| `KCL-OPA-VALIDATION-IMPLEMENTATION-PLAN.md` | Parent — defines the architecture this evaluation measures against |
| `KCL-OPA-PHASE1-SCHEMA-DESIGN.md` | Sibling — KCL schema design (Phase 1 only) |
| `KCL-OPA-PHASE1-CUE-SCHEMA-DESIGN.md` | Sibling — CUE schema design (Phase 1 only) |
| `KCL-OPA-PHASE1-PKL-SCHEMA-DESIGN.md` | Sibling — Pkl schema design (Phase 1 only); this document extends the evaluation to Phases 2 and 3 |
| `KCL-OPA-PHASE2-POLICY-ENGINE.md` | Evaluated against — OPA policy rules remain required regardless of schema language |
| `KCL-OPA-PHASE3-RENDERER-CI.md` | Evaluated against — Pkl's `output.text` replaces the Python renderer |
