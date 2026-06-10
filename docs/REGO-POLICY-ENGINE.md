# Phase 2 — OPA/Rego Policy Engine

**Date:** 2026-05-11 **Status:** Active — implemented in `policies/repository.rego`
**Note:** Pkl selected as schema language per [`PKL-CROSS-PHASE-EVALUATION.md`](PKL-CROSS-PHASE-EVALUATION.md).
KCL references in this document are historical. The OPA/Rego policy rules and
engine architecture remain valid.
**Previous:** [`docs/PKL-SCHEMA-DESIGN.md`](PKL-SCHEMA-DESIGN.md)
**Next:** [`docs/PKGBUILD-RENDERER-CI.md`](PKGBUILD-RENDERER-CI.md)

---

## 1. Purpose & Scope

Phase 2 delivers an OPA/Rego policy ruleset that audits the KCL-generated JSON
manifest for violations before any build is attempted. The rules encode the
security requirements from the handoff, the structural invariants from
`AGENTS.md`, and the quality checks from `docs/TODO.md` §62.

**What this phase produces:**

| Artifact                | Path                                     | Purpose                                                   |
| ----------------------- | ---------------------------------------- | --------------------------------------------------------- |
| Policy ruleset          | `policies/repository.rego`               | 12 Rego rules enforcing repo standards                    |
| Exception file template | `packages/<name>/policy_exceptions.yaml` | Per-package opt-out mechanism                             |
| Updated wrapper         | `scripts/validate-pkgbuilds.sh`          | Phase 1 wrapper extended with `conftest test` invocation  |
| Tool installer          | `scripts/install-validator-tools.sh`     | Downloads pinned KCL + Conftest binaries for CI/local use |

**What this phase does NOT do:**

- Does not modify existing PKGBUILDs or `.SRCINFO` files.
- Does not replace `scripts/check-metadata.sh` or
  `scripts/check-pkgdesc-consistency.sh` (they remain active during Phase 2;
  retirement considered after policy rules prove stable).
- Does not introduce the renderer (that's Phase 3).

---

## 2. Rego Architecture

### 2.1 Design Principles

1. **Fail-closed**: Unknown conditions result in a WARN at minimum. No silent
   acceptance.
2. **Package as unit of evaluation**: Each `Package` object from the KCL
   manifest is evaluated independently. Cross-package rules (pkgdesc
   consistency, rule 7) aggregate across all packages.
3. **Exceptions before deny**: The exception mechanism is evaluated before any
   rule — if a package has a registered exception for a rule, the rule is
   skipped, not evaluated-then-suppressed.
4. **Descriptive messages**: Every violation message includes the package name,
   the offending value, and a pointer to the relevant `PKGBUILD(5)` section or
   repo documentation.

### 2.2 Input Data Model

The Rego rules operate on the JSON output of the KCL schema. Input structure
(simplified):

```json
[
  {
    "pkgname": "opendoas",
    "pkgver": "6.8.2",
    "pkgrel": 1,
    "pkgdesc": "Run commands as super user or another user (patched version)",
    "arch": ["x86_64"],
    "url": "https://github.com/Duncaen/OpenDoas",
    "license": ["custom:ISC"],
    "depends": ["pam"],
    "makedepends": ["git"],
    "provides": ["doas"],
    "conflicts": ["doas"],
    "replaces": ["doas"],
    "install": "opendoas.install",
    "source": [
      {"filename": "opendoas", "url": "git+https://github.com/Duncaen/OpenDoas.git#tag=v6.8.2"},
      {"filename": "change-PATH.patch", "url": "change-PATH.patch"},
      ...
    ],
    "sha256sums": ["43b4c2d...", "d1784db...", ...],
    "backup": ["etc/pam.d/doas"],
    "validpgpkeys": [],
    "pkgver_func": "cd \"$pkgname\"\ngit describe --long --tags | sed 's,^v,,; s|-\\(.*\\)-g|.r\\1.g|'",
    "prepare": "cd \"$pkgname\"\n\n# Alpine PATH patch\npatch -Np1 -i ../change-PATH.patch\n...",
    "build": "cd \"$pkgname\"\n./configure --prefix=/usr --with-timestamp\nmake",
    "package": "cd \"$pkgname\"\nmake DESTDIR=\"$pkgdir\" install\ninstall -Dm644 LICENSE -t \"$pkgdir/usr/share/licenses/$pkgname\"",
    "_deploy_aur": false,
    "_pkgname": null,
    ...
  },
  ...
]
```

**Notes on the model**:

- All `_`-prefixed custom variables are present; `null` when the package doesn't
  set them.
- Lifecycle functions are raw strings — `prepare`, `build`, `check`, `package`,
  `pkgver_func`.
- `source` is an array of `{filename, url}` objects.
- `optdepends` is an array of `{name, desc}` objects.

### 2.3 Exception Mechanism

Each package may have a `packages/<name>/policy_exceptions.yaml` file:

```yaml
exceptions:
  - rule: enforce_https
    reason: "Upstream does not publish tarballs over HTTPS. Binary pinned by sha256sum."
  - rule: vcs_skip
    reason: "Binary release package — no VCS sources to checksum."
```

The validation wrapper (`validate-pkgbuilds.sh`) reads this file for each
package, converts it to a JSON input flag for `conftest`:

```bash
if [ -f "$pkg_dir/policy_exceptions.yaml" ]; then
    exceptions_json=$(python3 -c "import yaml,json; print(json.dumps(yaml.safe_load(open('$pkg_dir/policy_exceptions.yaml'))))")
    conftest test "$MANIFEST" -p policies/ -d <(echo "$exceptions_json")
else
    conftest test "$MANIFEST" -p policies/
fi
```

The Rego rules use `data.exceptions` to skip evaluation for packages with
registered exceptions.

---

## 3. Rule Specifications

### 3.1 Rule 1: `enforce_https`

**Severity**: ERROR (rule name: `deny_enforce_https`) **Source**: Handoff
`manifest-refactor-review-response.md` §3.B **Scope**: Per-package

```
Rule: All source URL protocols must be https:// or git+https://
Trigger: Any source[].url where protocol is http:// (not https://, git+https://, ftp://)
         or any url field on the Package itself starting with http://
```

**Rego implementation** (note: Conftest uses `deny_<id> contains msg if { ... }`
syntax):

```rego
deny_enforce_https contains msg if {
    pkg := input.packages[_]
    src := pkg.source[_]
    not startswith(src.url, "https://")
    not startswith(src.url, "git+https://")
    not startswith(src.url, "ftp://")        # FTP sources are valid per PKGBUILD(5)

    msg := sprintf("%s: source URL '%s' must use HTTPS (enforce_https rule)",
                   [pkg.pkgname, src.url])
}

deny_enforce_https contains msg if {
    pkg := input.packages[_]
    startswith(pkg.url, "http://")

    msg := sprintf("%s: url field '%s' must use HTTPS (enforce_https rule)",
                   [pkg.pkgname, pkg.url])
}
```

Exception exemptions are handled by the `exception` rule (see §4.1) — deny rules
remain clean.

**Testing notes**:

- `git+https://github.com/foo/bar.git` → pass
- `http://example.com/pkg.tar.gz` → fail
- `ftp://ftp.gnu.org/gnu/pkg.tar.gz` → pass (FTP is valid)
- `https://example.com/pkg.tar.gz` → pass
- `change-PATH.patch` (local file, no protocol) → pass
- `git+http://...` → fail (VCS sources must use git+https)

### 3.2 Rule 2: `privilege_escalation`

**Severity**: WARN (rule name: `warn_privilege_escalation`) **Source**: Handoff
§3.B **Scope**: Per-package

```
Rule: No use of `sudo` in lifecycle functions or .install scriptlets.
      `doas` is the approved privilege escalation mechanism.
Trigger: String "sudo" (word boundary) appears in any of:
         prepare, build, check, package, pkgver_func, or the .install scriptlet file
```

**Rego implementation**:

```rego
warn_privilege_escalation contains msg if {
    pkg := input.packages[_]

    func_fields := [pkg.prepare, pkg.build, pkg.check, pkg.packageFunc, pkg.pkgverFunc]
    field_names := ["prepare", "build", "check", "package", "pkgver_func"]

    func := func_fields[i]
    func != null
    regex.match(`\bsudo\b`, func)

    msg := sprintf("%s: '%s' string found in %s() — use doas instead (privilege_escalation rule)",
                   [pkg.pkgname, "sudo", field_names[i]])
}
```

**Testing notes**:

- `sudo make install` → fail
- `make install DESTDIR=...` → pass
- `# Comment about sudo` (in comment) → pass (comments are stripped by KCL
  import)
- `pseudo` → pass (partial word match excluded by `\b` boundary)
- `SUDO` → pass (case-sensitive match — `\bsudo\b`)

**Limitation**: If the `.install` file contains `sudo` and is referenced by the
`install` field, the Rego rule cannot scan the file content (only the filename).
Mitigation: a separate Bash check in `validate-pkgbuilds.sh` that optionally
scans `pkg.install` files for `sudo` when they exist. The Rego rule flags the
presence of an `install` field as a WARN:

```rego
warn_install_present contains msg if {
    pkg := input.packages[_]
    pkg.install != null
    msg := sprintf("%s: has .install scriptlet '%s' — manually verify no sudo usage",
                   [pkg.pkgname, pkg.install])
}
```

### 3.3 Rule 3: `architecture_mismatch`

**Severity**: WARN **Source**: Adapted from handoff §3.C "headless" rule
**Scope**: Per-package

```
Rule: If arch is ["any"], the package should not declare architecture-specific
      dependencies or build flags.
Trigger: arch=["any"] AND (depends contains arch-specific packages like
         glibc, or prepare/build functions contain CARCH references)
```

**Rego implementation**:

```rego
warn_architecture_mismatch contains msg if {
    pkg := input.packages[_]
    pkg.arch == ["any"]

    # Check for arch-specific dependency patterns
    arch_specific_deps := {"glibc", "lib32-glibc", "gcc-libs"}
    dep := pkg.depends[_] | pkg.makedepends[_] | pkg.checkdepends[_]
    arch_specific_deps[dep]

    msg := sprintf("%s: arch='any' but depends on arch-specific package '%s' (architecture_mismatch rule)",
                   [pkg.pkgname, dep])
}

warn_architecture_mismatch contains msg if {
    pkg := input.packages[_]
    pkg.arch == ["any"]

    funcs := [pkg.prepare, pkg.build, pkg.check, pkg.package]
    func_names := ["prepare", "build", "check", "package"]
    func := funcs[i]
    func != null
    contains(func, "CARCH")

    msg := sprintf("%s: arch='any' but %s() references CARCH (architecture_mismatch rule)",
                   [pkg.pkgname, func_names[i]])
}
```

**Testing notes**:

- `jules-tools` with `arch=["any"]` and `depends=["nodejs", "npm"]` → pass
  (nodejs/npm are not arch-specific)
- A hypothetical package with `arch=["any"]` and `depends=["glibc"]` → WARN
- `opencode-git` with `arch=["aarch64", "x86_64"]` and `depends=["glibc"]` →
  pass (not `any`)

### 3.4 Rule 4: `no_unprovided_conflicts`

**Severity**: ERROR **Source**: `AGENTS.md` variant builds convention **Scope**:
Per-package

```
Rule: Every entry in conflicts and replaces must have a matching entry in provides.
Trigger: conflicts[i] or replaces[i] not present in provides[]
```

**Rego implementation**:

```rego
deny_no_unprovided_conflicts contains msg if {
    pkg := input.packages[_]
    conflict := pkg.conflicts[_]
    not conflict_in_provides(pkg, conflict)

    msg := sprintf("%s: conflicts '%s' has no matching entry in provides (no_unprovided_conflicts rule)",
                   [pkg.pkgname, conflict])
}

deny_no_unprovided_conflicts contains msg if {
    pkg := input.packages[_]
    replace := pkg.replaces[_]
    not conflict_in_provides(pkg, replace)

    msg := sprintf("%s: replaces '%s' has no matching entry in provides (no_unprovided_conflicts rule)",
                   [pkg.pkgname, replace])
}

conflict_in_provides(pkg, target) {
    pkg.provides[_] == target
}
```

**Testing notes**:

- `opendoas`: `provides=["doas"]`, `conflicts=["doas"]`, `replaces=["doas"]` →
  pass for all three
- `opencode-git`: `provides=["opencode"]`, `conflicts=["opencode"]` → pass
- Hypothetical: `conflicts=["foo"]`, `provides=[]` → fail
- Hypothetical: `replaces=["foo"]`, `provides=["bar"]` → fail (mismatch)

### 3.5 Rule 5: `no_self_reference`

**Severity**: ERROR **Source**: `AGENTS.md` variant builds convention **Scope**:
Per-package

```
Rule: A package must not list its own pkgname in provides or conflicts.
Trigger: pkgname appears in provides[] or conflicts[]
```

**Rego implementation**:

```rego
deny_no_self_reference contains msg if {
    pkg := input.packages[_]
    pkg.provides[_] == pkg.pkgname
    msg := sprintf("%s: self-reference — provides contains own pkgname '%s' (no_self_reference rule)",
                   [pkg.pkgname, pkg.pkgname])
}

deny_no_self_reference contains msg if {
    pkg := input.packages[_]
    pkg.conflicts[_] == pkg.pkgname
    msg := sprintf("%s: self-reference — conflicts contains own pkgname '%s' (no_self_reference rule)",
                   [pkg.pkgname, pkg.pkgname])
}
```

**Testing notes**:

- `opencode-git`: pkgname=`opencode-git`, provides=`["opencode"]`,
  conflicts=`["opencode"]` → pass (no self-reference)
- `jules-tools`: pkgname=`jules-tools`, no provides/conflicts → pass
- Hypothetical: pkgname=`foo`, provides=`["foo"]` → fail

### 3.6 Rule 6: `deploy_aur_subarch_mutex`

**Severity**: ERROR **Source**: `AGENTS.md` AUR Deployment Gate **Scope**:
Per-package

```
Rule: _deploy_aur=true and _repo_subarch set are mutually exclusive.
Trigger: _deploy_aur == true AND _repo_subarch != null
```

**Rego implementation**:

```rego
deny_deploy_aur_subarch_mutex contains msg if {
    pkg := input.packages[_]
    pkg._deploy_aur == true
    pkg._repo_subarch != null

    msg := sprintf("%s: _deploy_aur=true is mutually exclusive with _repo_subarch='%s' — AUR packages cannot be sub-architecture variants (deploy_aur_subarch_mutex rule)",
                   [pkg.pkgname, pkg._repo_subarch])
}
```

**Testing notes**:

- `opencode-git`: `_deploy_aur=true`, `_repo_subarch=null` → pass
- Hypothetical: `_deploy_aur=true`, `_repo_subarch="x86_64_v3"` → fail

### 3.7 Rule 7: `pkgdesc_consistency`

**Severity**: ERROR **Source**: `AGENTS.md` variant builds convention **Scope**:
Cross-package

```
Rule: All packages sharing the same _pkgname must have identical pkgdesc.
Trigger: Two or more packages have identical _pkgname but differing pkgdesc values.
```

**Rego implementation**:

```rego
deny_pkgdesc_consistency contains msg if {
    # Group packages by _pkgname
    pkg1 := input[i]
    pkg2 := input[j]
    i < j
    pkg1._pkgname == pkg2._pkgname
    pkg1._pkgname != null
    pkg1.pkgdesc != pkg2.pkgdesc

    msg := sprintf("_pkgname '%s': pkgdesc mismatch — '%s' (%s) vs '%s' (%s) (pkgdesc_consistency rule)",
                   [pkg1._pkgname, pkg1.pkgdesc, pkg1.pkgname, pkg2.pkgdesc, pkg2.pkgname])
}
```

**Testing notes**:

- `opencode-git` and a hypothetical `opencode-nightly` with identical
  `_pkgname="opencode"` and identical `pkgdesc` → pass
- Same scenario but different `pkgdesc` → fail
- `opendoas` with `_pkgname=null` and `ranger-doas` with `_pkgname=null` → pass
  (no shared `_pkgname` to compare)
- Single package with `_pkgname` set → pass (no peer to compare against)

### 3.8 Rule 8: `valid_architectures`

**Severity**: ERROR **Source**: `PKGBUILD(5)` §7.7 **Scope**: Per-package

```
Rule: arch array values must be from the known set: x86_64, aarch64, any
Trigger: Any value in arch[] not in the known set.
```

Note: This duplicates the KCL schema `check` block. It's included in OPA for
cases where the schema is bypassed and raw JSON is fed directly to Conftest. The
KCL check is the primary enforcement; the OPA rule is a defense-in-depth
duplicate.

**Rego implementation**:

```rego
deny_valid_architectures contains msg if {
    pkg := input.packages[_]
    valid_arches := {"x86_64", "aarch64", "any"}

    arch := pkg.arch[_]
    not valid_arches[arch]

    msg := sprintf("%s: unknown architecture '%s' — must be one of: x86_64, aarch64, any (valid_architectures rule)",
                   [pkg.pkgname, arch])
}
```

### 3.9 Rule 9: `required_fields`

**Severity**: ERROR **Source**: `PKGBUILD(5)` §7 **Scope**: Per-package

```
Rule: The following fields must be present and non-empty:
      pkgname, pkgver, pkgrel, pkgdesc, arch, url, license
Trigger: Any required field is null, empty string, zero, or empty array.
```

**Rego implementation**:

```rego
deny_required_fields contains msg if {
    pkg := input.packages[_]
    required := [
        {"name": "pkgname", "value": pkg.pkgname},
        {"name": "pkgver",  "value": pkg.pkgver},
        {"name": "pkgrel",  "value": pkg.pkgrel},
        {"name": "pkgdesc", "value": pkg.pkgdesc},
        {"name": "arch",    "value": pkg.arch},
        {"name": "url",     "value": pkg.url},
        {"name": "license", "value": pkg.license},
    ]

    field := required[i]
    is_empty_or_null(field.value)

    msg := sprintf("%s: required field '%s' is missing or empty (required_fields rule)",
                   [pkg.pkgname, field.name])
}

is_empty_or_null(v) {
    v == null
}

is_empty_or_null(v) {
    v == ""
}

is_empty_or_null(v) {
    v == 0
}

is_empty_or_null(v) {
    count(v) == 0
}
```

### 3.10 Rule 10: `source_integrity`

**Severity**: ERROR **Source**: `PKGBUILD(5)` §7.10 **Scope**: Per-package

```
Rule: If source[] is present, exactly one checksum array must be present and
      its length must match source[] length (excluding SKIP entries for VCS sources).
Trigger: (source is non-empty) AND (no checksum array present OR
         checksum array length != count of non-SKIP source entries)
```

**Rego implementation**:

```rego
deny_source_integrity contains msg if {
    pkg := input.packages[_]
    count(pkg.source) > 0
    pkg.sha256sums == null
    pkg.sha512sums == null
    pkg.sha224sums == null
    pkg.sha384sums == null
    pkg.b2sums == null

    msg := sprintf("%s: source[] has %d entries but no checksum array present (source_integrity rule)",
                   [pkg.pkgname, count(pkg.source)])
}

deny_source_integrity contains msg if {
    pkg := input.packages[_]
    checksums := coalesce_checksums(pkg)
    count(pkg.source) != count(checksums)

    msg := sprintf("%s: source[] has %d entries but checksums has %d entries (source_integrity rule)",
                   [pkg.pkgname, count(pkg.source), count(checksums)])
}

coalesce_checksums(pkg) = c {
    pkg.sha256sums != null
    c = pkg.sha256sums
} else = c {
    pkg.sha512sums != null
    c = pkg.sha512sums
} else = c {
    pkg.sha224sums != null
    c = pkg.sha224sums
} else = c {
    pkg.sha384sums != null
    c = pkg.sha384sums
} else = c {
    pkg.b2sums != null
    c = pkg.b2sums
} else = [] {
    c = []
}
```

**Note**: VCS sources (git+, svn+, etc.) use `SKIP` as their checksum value. The
schema stores these as literal `"SKIP"` strings. The length check includes SKIP
entries — both source[] and checksum[] arrays must be the same length.

### 3.11 Rule 11: `vcs_skip`

**Severity**: WARN **Source**: Arch Wiki
[VCS package guidelines](https://wiki.archlinux.org/title/VCS_package_guidelines)
**Scope**: Per-package

```
Rule: Non-VCS source entries (tarballs, local files) should not have SKIP checksums.
Trigger: A source[i].url that is NOT a VCS URL (no git+, svn+, hg+, bzr+ prefix)
         has a corresponding checksum[i] == "SKIP"
```

**Rego implementation**:

```rego
warn_vcs_skip contains msg if {
    pkg := input.packages[_]
    checksums := coalesce_checksums(pkg)
    src := pkg.source[i]
    checksums[i] == "SKIP"
    not is_vcs_url(src.url)

    msg := sprintf("%s: non-VCS source '%s' has SKIP checksum — should have integrity hash (vcs_skip rule)",
                   [pkg.pkgname, src.filename])
}

is_vcs_url(url) {
    startswith(url, "git+")
}
is_vcs_url(url) {
    startswith(url, "svn+")
}
is_vcs_url(url) {
    startswith(url, "hg+")
}
is_vcs_url(url) {
    startswith(url, "bzr+")
}
```

**Testing notes**:

- `opencode-git`: VCS git+https URL with SKIP checksum → pass
- `opendoas`: VCS git+https URL with SKIP checksum (if present) → pass; local
  patches with real hashes → pass
- Hypothetical: `https://example.com/pkg.tar.gz` with SKIP checksum → WARN

### 3.12 Rule 12: `deny_missing_maintainer`

**Severity**: FAIL **Source**: Repo convention (`AGENTS.md` §2 Identity &
Security) **Scope**: Per-package

Every package must declare a maintainer in "Name <email>" format. The Pkl schema
enforces the format; this rule catches cases where the field is absent entirely.

**Rego implementation**:

```rego
deny_missing_maintainer contains msg if {
    pkg := input.packages[_]
    not has_exception(pkg, "missing_maintainer")
    object.get(pkg, "maintainer", null) == null
    msg := sprintf(
        "%s: maintainer is missing (must be 'Name <email>')",
        [pkg.pkgname],
    )
}
```

---

## 4. Exception Mechanism

Conftest provides a built-in `exception` rule pattern: when an
`exception contains rules if { ... }` rule body evaluates for a given input, the
returned `rules` list specifies which `deny_<id>` rules are skipped. The `<id>`
suffix matches the rule name after `deny_` or `violation_`.

### 4.1 Exception Data

Exception declarations live in `packages/<name>/policy_exceptions.yaml`:

```yaml
exceptions:
  - rule: enforce_https
    reason: "Upstream does not publish tarballs over HTTPS. Binary pinned by sha256sum."
  - rule: vcs_skip
    reason: "Binary release package — no VCS sources to checksum."
```

These are loaded into Conftest via the `--data` flag (see §4.3) and become
available as `data.exceptions`.

### 4.2 Rego Exception Rule

The exception rule in `policies/repository.rego` matches exemption data against
packages in the input manifest:

```rego
exception contains rules if {
    pkg := input.packages[_]
    exc := data.exceptions.exceptions[_]
    exc.pkgname == pkg.pkgname
    rules := [exc.rule]
}
```

When `exception` produces a non-empty `rules` list for an input, the
corresponding `deny_<id>` rules are automatically skipped by Conftest. For
example, if `rules := ["enforce_https"]`, the `deny_enforce_https` rule does not
evaluate for that package. The matching is by rule ID suffix only — the
`exception` rule does not need to import or reference the deny rules directly.

**Important constraint**: The `exception` rule pattern only works with
`deny_<id>` and `violation_<id>` rule names — it does NOT skip `warn_<id>`
rules. Warning rules that need exceptions must either handle them within their
own rule bodies or the exception mechanism must be extended (not implemented in
Phase 2).

### 4.3 Validation Wrapper Integration

The wrapper script converts `policy_exceptions.yaml` files into JSON for the
`--data` flag:

```bash
build_exceptions_json() {
    local exceptions_json='{"exceptions":['
    local first=true
    shopt -s nullglob
    for exceptions_file in packages/*/policy_exceptions.yaml; do
        if [ -s "$exceptions_file" ]; then
            local pkg_dir
            pkg_dir=$(dirname "$exceptions_file")
            local pkg_name
            pkg_name=$(basename "$pkg_dir")
            python3 -c "
import yaml, json, sys
data = yaml.safe_load(open('$exceptions_file'))
for exc in data.get('exceptions', []):
    exc['pkgname'] = '$pkg_name'
    print(json.dumps(exc))
" | while read -r entry; do
                if [ "$first" = true ]; then first=false; else exceptions_json+=','; fi
                exceptions_json+="$entry"
            done
        fi
    done
    exceptions_json+=']}'
    echo "$exceptions_json"
}
```

The resulting JSON is written to a directory and passed to Conftest, which
recursively loads all JSON/YAML files found under `--data` paths:

```bash
# In validate-pkgbuilds.sh
exceptions_json=$(build_exceptions_json)
exceptions_dir="$TMPDIR/conftest-data"
mkdir -p "$exceptions_dir"
echo "$exceptions_json" > "$exceptions_dir/exceptions.json"
conftest test "$MANIFEST" -p policies/ -d "$exceptions_dir/"
```

---

## 5. Tool Installer (`scripts/install-validator-tools.sh`)

Pinned-version KCL and Conftest downloader for CI and local use:

```bash
#!/bin/bash
set -euo pipefail

KCL_VERSION="${KCL_VERSION:-0.12.0}"
CONFTEST_VERSION="${CONFTEST_VERSION:-0.59.0}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

install_kcl() {
    if command -v kcl &>/dev/null; then return 0; fi
    local url="https://github.com/kcl-lang/kcl/releases/download/v${KCL_VERSION}/kcl-v${KCL_VERSION}-linux-amd64.tar.gz"
    curl -sSL "$url" | tar xz -C /tmp
    mv "/tmp/kcl" "$INSTALL_DIR/kcl"
    echo "Installed KCL ${KCL_VERSION}"
}

install_conftest() {
    if command -v conftest &>/dev/null; then return 0; fi
    local url="https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz"
    curl -sSL "$url" | tar xz -C /tmp
    mv "/tmp/conftest" "$INSTALL_DIR/conftest"
    echo "Installed Conftest ${CONFTEST_VERSION}"
}

install_kcl
install_conftest
```

CI usage in `build.yml` validate job:

```yaml
- name: Install KCL + Conftest
  run: |
    KCL_VERSION=0.12.0 CONFTEST_VERSION=0.59.0 bash scripts/install-validator-tools.sh
    echo "$HOME/.local/bin" >> $GITHUB_PATH
```

---

## 6. Updated `validate-pkgbuilds.sh` (Phase 2 Additions)

Extending the Phase 1 wrapper:

```bash
#!/bin/bash
set -euo pipefail

KCL_BIN="${KCL_BIN:-kcl}"
CONFTEST_BIN="${CONFTEST_BIN:-conftest}"
SKIP_OPA="${SKIP_OPA:-}"
TMPDIR="${TMPDIR:-/tmp}/kcl-validate-$$"
PACKAGES_DIR="packages"
SCHEMA_FILE="schemas/arch_pkg.pkl"
POLICIES_DIR="policies"
FAILED=0

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

mkdir -p "$TMPDIR"

# Phase 1: Import + compile (unchanged from Phase 1 design)
# ...

# Phase 2: Policy check
if [ "${SKIP_OPA:-}" != "1" ]; then
    if [ ! -d "$POLICIES_DIR" ]; then
        echo "WARNING: policies/ directory not found. Skipping OPA check."
        echo "This is normal during Phase 1. Phase 2 populates policies/."
    elif ! command -v "$CONFTEST_BIN" &>/dev/null; then
        echo "WARNING: conftest not found. Install with: scripts/install-validator-tools.sh"
        exit 2
    else
        # Build exceptions JSON from all policy_exceptions.yaml files
        exceptions_json=$(build_exceptions_json)
        exceptions_file="$TMPDIR/exceptions.json"
        echo "$exceptions_json" > "$exceptions_file"

        if ! "$CONFTEST_BIN" test "$MANIFEST" -p "$POLICIES_DIR" -d "$exceptions_file" 2>&1; then
            echo "FAIL: OPA policy violations detected"
            FAILED=1
        fi
    fi
fi

exit $FAILED
```

---

## 7. Testing Strategy

### 7.1 Unit Tests (Rego)

Test each rule in isolation using `conftest verify`:

```
policies/
├── repository.rego
├── repository_test.rego       # Test fixtures and assertions
└── test_fixtures/
    ├── valid_package.json      # Should pass all rules
    ├── http_source.json        # Should trigger enforce_https
    ├── sudo_in_build.json      # Should trigger privilege_escalation
    ├── arch_mismatch.json      # Should trigger architecture_mismatch
    ├── unprovided_conflict.json # Should trigger no_unprovided_conflicts
    ├── self_reference.json     # Should trigger no_self_reference
    ├── aur_subarch_mutex.json  # Should trigger deploy_aur_subarch_mutex
    ├── pkgdesc_mismatch.json   # Should trigger pkgdesc_consistency
    ├── invalid_arch.json       # Should trigger valid_architectures
    ├── missing_fields.json     # Should trigger required_fields
    ├── source_mismatch.json    # Should trigger source_integrity
    └── vcs_skip_warn.json      # Should trigger vcs_skip
```

### 7.2 Integration Tests

Run validation against all 6 existing PKGBUILDs:

1. Import to KCL → compile → `conftest test`.
2. For each policy violation found: determine whether it's a legitimate finding
   (fix the PKGBUILD) or a false positive (add a `policy_exceptions.yaml`).
3. Iterate until all 6 packages pass cleanly (or have documented exceptions for
   legitimate cases).

### 7.3 Regression Tests

After Phase 2, add a GitHub Actions test workflow that runs on every PR:

```yaml
name: Policy Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Install tools
        run: bash scripts/install-validator-tools.sh
      - name: Run Rego unit tests
        run: conftest verify -p policies/
      - name: Validate all packages
        run: bash scripts/validate-pkgbuilds.sh
```

---

## 8. Phase 2 Acceptance Criteria

- [ ] `policies/repository.rego` exists with all 12 rules implemented.
- [ ] All 12 rules have corresponding test fixtures in
      `policies/test_fixtures/`.
- [ ] `conftest verify -p policies/` passes (all unit tests green).
- [ ] `scripts/install-validator-tools.sh` downloads and verifies KCL + Conftest
      on a clean system.
- [ ] `scripts/validate-pkgbuilds.sh` runs the full import → compile → policy
      check loop without errors.
- [ ] All 6 existing packages pass validation or have documented
      `policy_exceptions.yaml` files.
- [ ] No false positives remain — every violation is either a real issue or has
      a justified exception.
