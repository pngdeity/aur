# Phase 3 — Renderer + CI/CD Integration

**Date:** 2026-05-11 **Status:** Proposed **Note:** Pkl selected as schema
language per [`PKL-CROSS-PHASE-EVALUATION.md`](PKL-CROSS-PHASE-EVALUATION.md).
KCL references in this document are historical. The Python renderer (§2) is
replaced by Pkl's `output.text`. The CI workflow topology (§4) and round-trip
testing strategy remain valid.
**Previous:** [`docs/REGO-POLICY-ENGINE.md`](REGO-POLICY-ENGINE.md)

---

## 1. Purpose & Scope

Phase 3 delivers three things:

1. A Python renderer that converts validated KCL JSON back into syntactically
   correct `PKGBUILD(5)` text.
2. A pre-commit hook that runs the full validation pipeline (import → KCL
   compile → OPA check).
3. CI workflow modifications that insert the validation job as an upstream gate
   in both `build.yml` and `discovery.yml`.

After this phase, the validation layer is fully operational: every commit and
every CI build passes through KCL schema validation and OPA policy enforcement
before `makepkg` is invoked.

**What this phase produces:**

| Artifact                   | Path                                 | Purpose                                                 |
| -------------------------- | ------------------------------------ | ------------------------------------------------------- |
| PKGBUILD renderer          | `scripts/kcl_to_pkgbuild.py`         | KCL manifest → valid `PKGBUILD(5)` text                 |
| Updated pre-commit hooks   | `.pre-commit-config.yaml`            | Add `kcl-validate` hook                                 |
| Updated build workflow     | `.github/workflows/build.yml`        | Add `validate` job before `execute`                     |
| Updated discovery workflow | `.github/workflows/discovery.yml`    | Add validation gate before `git push`                   |
| Policy test workflow       | `.github/workflows/policy-tests.yml` | Rego unit tests on PR (Phase 2 deliverable, wired here) |

**What this phase does NOT do:**

- Does not swap the source of truth from PKGBUILD to KCL (that's Phase 4,
  deferred).
- Does not modify `sync-package.sh`, `aur-deploy.sh`, or the Docker builder
  image.
- Does not change the `publish` or `deploy-aur` jobs in `release.yml`.

---

## 2. PKGBUILD Renderer (`scripts/kcl_to_pkgbuild.py`)

### 2.1 Design Goals

1. **Functional equivalence**: A PKGBUILD rendered from KCL must produce the
   same binary when built with `makepkg`. Byte-level identity with the original
   hand-authored PKGBUILD is not required — indentation, blank line count, and
   comment presence may differ.
2. **Deterministic output**: Given the same KCL manifest, the renderer produces
   the same PKGBUILD text every time. No timestamps, no random identifiers, no
   hostname injection.
3. **Valid Bash**: The output must be parseable by `bash` and
   `makepkg --printsrcinfo`. All quoting follows `PKGBUILD(5)` conventions.
4. **Round-trip acceptance**: `PKGBUILD → kcl → JSON → render → PKGBUILD2` must
   build correctly in the Docker container. The diff between original and
   rendered is informational only.

### 2.2 Input Contract

Input: A JSON file containing an array of `Package` objects conforming to
`schemas/arch_pkg.k`.

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
      {"filename": "rowhammer.patch", "url": "rowhammer.patch"},
      {"filename": "retry.patch", "url": "retry.patch"},
      {"filename": "arg-handling.patch", "url": "arg-handling.patch"},
      {"filename": "post-release-v6.8.2.patch", "url": "post-release-v6.8.2.patch"}
    ],
    "backup": ["etc/pam.d/doas"],
    "sha256sums": ["43b4c2de...", "d1784db1...", "80c9ebdb...", "cae34e45...", "3e86c260...", "dab65313..."],
    "prepare": "cd \"$pkgname\"\n\npatch -Np1 -i ../change-PATH.patch\npatch -Np1 -i ../rowhammer.patch\npatch -Np1 -i ../retry.patch\npatch -Np1 -i ../arg-handling.patch\npatch -Np1 -i ../post-release-v6.8.2.patch",
    "build": "cd \"$pkgname\"\n./configure --prefix=/usr --with-timestamp\nmake",
    "package": "cd \"$pkgname\"\nmake DESTDIR=\"$pkgdir\" install\ninstall -Dm644 LICENSE -t \"$pkgdir/usr/share/licenses/$pkgname\"",
    "pkgver_func": "cd \"$pkgname\"\ngit describe --long --tags | sed 's,^v,,; s|-\\(.*\\)-g|.r\\1.g|'",
    ...
  }
]
```

**Multi-package input**: The renderer accepts a JSON array. For the
validation-only mode (Phase 1–3), it renders each package to a separate output
file. For Phase 4 (deferred), a single package is rendered.

### 2.3 Output Contract

Output: Valid `PKGBUILD(5)` text written to stdout or a specified file.

```
# Maintainer: pngdeity <pngdeity@tutanota.com>

pkgname=opendoas
pkgver=6.8.2
pkgrel=1
pkgdesc='Run commands as super user or another user (patched version)'
arch=('x86_64')
url='https://github.com/Duncaen/OpenDoas'
license=('custom:ISC')
depends=('pam')
makedepends=('git')
provides=('doas')
conflicts=('doas')
replaces=('doas')
install=opendoas.install
backup=('etc/pam.d/doas')
source=(
    "${pkgname}::git+https://github.com/Duncaen/OpenDoas.git#tag=v${pkgver}"
    "change-PATH.patch"
    "rowhammer.patch"
    "retry.patch"
    "arg-handling.patch"
    "post-release-v6.8.2.patch"
)
sha256sums=('43b4c2de...'
            'd1784db1...'
            ...)

pkgver() {
  cd "$pkgname"
  git describe --long --tags | sed 's,^v,,; s|-\(.*\)-g|.r\1.g|'
}

prepare() {
  cd "$pkgname"

  patch -Np1 -i ../change-PATH.patch
  patch -Np1 -i ../rowhammer.patch
  ...
}

build() {
  cd "$pkgname"
  ./configure --prefix=/usr --with-timestamp
  make
}

package() {
  cd "$pkgname"
  make DESTDIR="$pkgdir" install
  install -Dm644 LICENSE -t "$pkgdir/usr/share/licenses/$pkgname"
}
```

### 2.4 Field Ordering

Fields are rendered in this order, matching common PKGBUILD conventions (not
`PKGBUILD(5)` mandated, but community standard):

| Section            | Fields                                                                                                                                                                                                                               | Notes                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Custom variables   | `_deploy_aur`, `_pkgname`, `_githubname`, `_upstream_aur_pkg`, `_upstream_arch_repo`, `_demote_upstream_maintainer`, `_auto_merge_build`, `_use_common_gemini_settings`, `_repo_subarch`, `_tag`, `_npmscope`, `_npmname`, `_npmver` | Rendered if present (not null/empty/false-for-booleans-at-default). Order: as enumerated here. |
| Identity           | `pkgname`, `changelog`                                                                                                                                                                                                               |                                                                                                |
| Version            | `pkgver`, `pkgrel`, `epoch`                                                                                                                                                                                                          | `epoch` only if present                                                                        |
| Metadata           | `pkgdesc`, `arch`, `url`, `license`, `groups`                                                                                                                                                                                        |                                                                                                |
| Depends            | `depends`, `makedepends`, `checkdepends`                                                                                                                                                                                             |                                                                                                |
| OptDepends         | `optdepends`                                                                                                                                                                                                                         | Rendered as `'name: desc'` strings                                                             |
| Provides/Conflicts | `provides`, `conflicts`, `replaces`                                                                                                                                                                                                  |                                                                                                |
| Config             | `backup`, `install`                                                                                                                                                                                                                  |                                                                                                |
| Source             | `source`                                                                                                                                                                                                                             | Filename::url syntax; VCS fragments preserved                                                  |
| Integrity          | `sha256sums` (or `sha512sums`, etc.), `validpgpkeys`                                                                                                                                                                                 | `b2sums` last if present; order: sha256, sha512, sha224, sha384, b2                            |
| Extract            | `noextract`                                                                                                                                                                                                                          |                                                                                                |
| Options            | `options`                                                                                                                                                                                                                            |                                                                                                |
| Functions          | `pkgver_func`, `prepare`, `build`, `check`, `package`                                                                                                                                                                                | In lifecycle order                                                                             |

### 2.5 Rendering Rules

#### String quoting

- Single-word values (no spaces, no special chars): unquoted. Example:
  `install=opendoas.install`
- Multi-word or special-char values: single-quoted with internal single quotes
  escaped. Example:
  `pkgdesc='Run commands as super user or another user (patched version)'`
- Empty strings: `''`

#### Array rendering

- Arrays use `('element1' 'element2')` syntax. One element per line if `len > 3`
  for readability:
  ```
  depends=('pam')
  ```
  vs.
  ```
  optdepends=(
      'atool: for previews of archives'
      'elinks: for previews of html pages'
      ...
  )
  ```
- Empty arrays: omitted entirely (optional field, not rendered).
- Checksum arrays: each element on its own indented line for readability,
  matching existing PKGBUILD style.

#### Source array rendering

- Each `SourceEntry` is rendered as:
  - If `filename != url`: `"${filename}::${url}"` (with `${pkgname}` references
    preserved if detected as variable)
  - If `filename == url`: `"${filename}"` (local file or simple URL)
- VCS fragments (`#tag=`, `#commit=`, `#branch=`) preserved verbatim in the URL
  portion.
- SKIP hashes rendered as literal `'SKIP'`.

#### Function rendering

- Function name line: `funcname() {`
- Body: rendered verbatim (the KCL model stores the raw text).
- Closing: `}`
- Functions are separated by exactly one blank line.

#### Boolean rendering

- `true` → rendered as `true` (lowercase, no quotes)
- `false` → field omitted (not rendered at all)

#### Null/absent handling

- Optional fields that are `null` or absent → not rendered.
- Required fields → always rendered (validation ensures they're present).

#### Variable references in source URLs

- If a source URL contains `${pkgname}`, `${pkgver}`, or `${_pkgname}`, the
  renderer preserves the variable reference. The import script (Phase 1)
  resolves variables via `declare -p`, which expands them. To preserve variable
  references, the import script must detect the pattern `${VAR}` in the original
  PKGBUILD source array and store it as-is in the KCL model rather than
  expanding it. This requires a modification to the import script's source
  parsing logic.

  **Resolution**: The import script reads the original `PKGBUILD` source array
  text before Bash expansion. It stores the raw (unexpanded) source entries
  alongside the resolved ones in the KCL model. Add a `raw_url` field to
  `SourceEntry`:

  ```kcl
  schema SourceEntry:
      url: str       # Resolved URL (for validation)
      filename: str  # Local filename
      raw_url?: str  # Raw unexpanded text from PKGBUILD (for rendering fidelity)
  ```

  When `raw_url` is present, the renderer uses it instead of `url`. When absent
  (manually authored `package.k`), the renderer uses `url` directly.

### 2.6 Implementation Structure

```python
#!/usr/bin/env python3
"""
scripts/kcl_to_pkgbuild.py — Render KCL manifest JSON to PKGBUILD(5) text.

Usage:
    python scripts/kcl_to_pkgbuild.py manifest.json [--output-dir /path/to/output/]

Reads a JSON array of Package objects (KCL manifest output).
Writes one PKGBUILD per package to the output directory.
If --output-dir is not specified, prints all PKGBUILDs to stdout separated by
a "### <pkgname>" marker.

Exit codes:
    0 — All packages rendered successfully.
    1 — Input file missing, invalid JSON, or schema violation in input.
"""

import json
import sys
import os
import argparse
from typing import Any

# ── Constants ──

MAINTAINER_LINE = "# Maintainer: pngdeity <pngdeity@tutanota.com>"

# Field ordering (list of tuples: (field_name, section_label))
FIELD_ORDER = [
    # Custom variables
    ("_deploy_aur", None),
    ("_pkgname", None),
    ("_githubname", None),
    ("_upstream_aur_pkg", None),
    ("_upstream_arch_repo", None),
    ("_demote_upstream_maintainer", None),
    ("_auto_merge_build", None),
    ("_use_common_gemini_settings", None),
    ("_repo_subarch", None),
    ("_tag", None),
    ("_npmscope", None),
    ("_npmname", None),
    ("_npmver", None),
    # Identity
    ("pkgname", None),
    ("changelog", None),
    # Version
    ("pkgver", None),
    ("pkgrel", None),
    ("epoch", None),
    # Metadata
    ("pkgdesc", None),
    ("arch", None),
    ("url", None),
    ("license", None),
    ("groups", None),
    # Dependencies
    ("depends", None),
    ("makedepends", None),
    ("checkdepends", None),
    ("optdepends", None),
    # Relationships
    ("provides", None),
    ("conflicts", None),
    ("replaces", None),
    # Config
    ("backup", None),
    ("install", None),
    # Source
    ("source", None),
    ("sha256sums", None),
    ("sha512sums", None),
    ("sha224sums", None),
    ("sha384sums", None),
    ("b2sums", None),
    ("validpgpkeys", None),
    # Misc
    ("noextract", None),
    ("options", None),
]

FUNCTION_ORDER = ["pkgver_func", "prepare", "build", "check", "package"]
FUNCTION_NAMES = {"pkgver_func": "pkgver", "prepare": "prepare",
                  "build": "build", "check": "check", "package": "package"}


def quote_string(value: str) -> str:
    """Single-quote a Bash string, escaping internal single quotes."""
    if " " not in value and not any(c in value for c in "'\"$*?[]{}()<>|;&#~"):
        return value
    escaped = value.replace("'", "'\\''")
    return f"'{escaped}'"


def render_array(items: list, indent: int = 0) -> str:
    """Render a Bash array: ('item1' 'item2') or multi-line if > 3 items."""
    if not items:
        return ""
    prefix = " " * indent
    if len(items) <= 3:
        elements = " ".join(quote_string(str(i)) for i in items)
        return f"({elements})"

    lines = ["("]
    for item in items:
        lines.append(f"{prefix}    {quote_string(str(item))}")
    lines.append(f"{prefix})")
    return "\n".join(lines)


def render_source_entry(entry: dict) -> str:
    """Render a single SourceEntry to PKGBUILD source array element text."""
    raw = entry.get("raw_url")
    url = entry.get("url", "")
    filename = entry.get("filename", "")

    if raw:
        return quote_string(raw)

    if filename and filename != url:
        # Extract basename without path for the :: prefix
        display_name = filename
        return quote_string(f"{display_name}::{url}")

    return quote_string(url)


def render_optdepends(items: list) -> list:
    """Render optdepends entries as 'name: desc' strings."""
    result = []
    for entry in items:
        name = entry.get("name", "")
        desc = entry.get("desc", "")
        if desc:
            result.append(f"{name}: {desc}")
        else:
            result.append(name)
    return result


def render_pkgbuild(pkg: dict) -> str:
    """Render a single Package object to PKGBUILD text."""
    lines = [MAINTAINER_LINE, ""]

    # Render regular fields in order
    for field_name, _ in FIELD_ORDER:
        value = pkg.get(field_name)
        if value is None:
            continue
        if value == "" or value == 0 or value == [] or value is False:
            continue

        if field_name == "arch":
            lines.append(f"arch={render_array(value)}")
        elif field_name == "license":
            lines.append(f"license={render_array(value)}")
        elif field_name == "optdepends":
            rendered = render_optdepends(value)
            lines.append(f"optdepends={render_array(rendered)}")
        elif field_name == "source":
            elements = [render_source_entry(e) for e in value]
            lines.append(f"source=(")
            for elem in elements:
                lines.append(f"    {elem}")
            lines.append(")")
        elif field_name in ("sha256sums", "sha512sums", "sha224sums",
                            "sha384sums", "b2sums"):
            lines.append(f"{field_name}=(")
            for checksum in value:
                lines.append(f"            '{checksum}'")
            lines.append("            )")
        elif field_name == "validpgpkeys":
            lines.append(f"validpgpkeys={render_array(value)}")
        elif field_name == "noextract":
            lines.append(f"noextract={render_array(value)}")
        elif field_name == "options":
            lines.append(f"options={render_array(value)}")
        elif field_name == "depends":
            lines.append(f"depends={render_array(value)}")
        elif field_name == "makedepends":
            lines.append(f"makedepends={render_array(value)}")
        elif field_name == "checkdepends":
            lines.append(f"checkdepends={render_array(value)}")
        elif field_name == "provides":
            lines.append(f"provides={render_array(value)}")
        elif field_name == "conflicts":
            lines.append(f"conflicts={render_array(value)}")
        elif field_name == "replaces":
            lines.append(f"replaces={render_array(value)}")
        elif field_name == "backup":
            lines.append(f"backup={render_array(value)}")
        elif field_name == "groups":
            lines.append(f"groups={render_array(value)}")
        elif field_name in ("_deploy_aur", "_demote_upstream_maintainer",
                            "_auto_merge_build", "_use_common_gemini_settings"):
            # Booleans
            if value is True:
                lines.append(f"{field_name}=true")
        elif isinstance(value, bool):
            continue  # False booleans omitted
        elif isinstance(value, (int, float)):
            lines.append(f"{field_name}={value}")
        elif isinstance(value, str) and "\n" not in value:
            lines.append(f"{field_name}={quote_string(value)}")
        elif isinstance(value, str):
            pass  # Multi-line strings are functions, handled below

    # Render lifecycle functions
    for func_field in FUNCTION_ORDER:
        func_body = pkg.get(func_field)
        if not func_body or not isinstance(func_body, str):
            continue
        func_name = FUNCTION_NAMES[func_field]
        lines.append("")
        lines.append(f"{func_name}() {{")
        # Indent function body
        for body_line in func_body.strip().split("\n"):
            if body_line.strip():
                lines.append(f"  {body_line}")
            else:
                lines.append("")
        lines.append("}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Render KCL manifest JSON to PKGBUILD text")
    parser.add_argument("manifest", help="Path to KCL manifest JSON")
    parser.add_argument("--output-dir", "-o",
                        help="Output directory for PKGBUILD files")
    parser.add_argument("--package", "-p",
                        help="Render only a specific package by pkgname")
    args = parser.parse_args()

    with open(args.manifest) as f:
        packages = json.load(f)

    if not isinstance(packages, list):
        packages = [packages]

    for pkg in packages:
        pkgname = pkg.get("pkgname", "unknown")
        if args.package and pkgname != args.package:
            continue

        rendered = render_pkgbuild(pkg)

        if args.output_dir:
            os.makedirs(args.output_dir, exist_ok=True)
            outpath = os.path.join(args.output_dir, "PKGBUILD")
            with open(outpath, "w") as f:
                f.write(rendered)
            print(f"Rendered: {outpath}")
        else:
            print(f"### {pkgname}")
            print(rendered)


if __name__ == "__main__":
    main()
```

### 2.7 Round-Trip Verification

The acceptance test for the renderer:

```bash
#!/bin/bash
# scripts/test-roundtrip.sh — Verify PKGBUILD → KCL → PKGBUILD round-trip

set -euo pipefail

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

for pkgbuild in packages/*/PKGBUILD; do
    pkg_dir=$(dirname "$pkgbuild")
    pkg_name=$(basename "$pkg_dir")

    echo "=== Testing $pkg_name ==="

    # Step 1: PKGBUILD → KCL
    python3 scripts/pkgbuild_to_kcl.py "$pkgbuild" > "$TMPDIR/${pkg_name}.k"

    # Step 2: KCL → JSON
    kcl run "$TMPDIR/${pkg_name}.k" -o "$TMPDIR/${pkg_name}.json" --format json

    # Step 3: JSON → PKGBUILD
    python3 scripts/kcl_to_pkgbuild.py "$TMPDIR/${pkg_name}.json" \
        -o "$TMPDIR/${pkg_name}/"

    # Step 4: diff original vs rendered
    echo "  Diff (informational — functional equivalence is the goal):"
    diff "$pkgbuild" "$TMPDIR/${pkg_name}/PKGBUILD" || true

    # Step 5: Verify rendered PKGBUILD is valid
    pushd "$TMPDIR/${pkg_name}" > /dev/null
    if ! bash -n PKGBUILD 2>&1; then
        echo "FAIL: $pkg_name — rendered PKGBUILD is not valid Bash"
        exit 1
    fi
    popd > /dev/null

    echo "PASS: $pkg_name"
done

echo "All packages round-trip OK"
```

The diff is informational — not a gate. The gate is: "does the rendered PKGBUILD
build correctly?" Byte-level identity is not required because the renderer
doesn't preserve comments, and blank line counts may differ.

---

## 3. Pre-Commit Hook Integration

### 3.1 Design

Add a `kcl-validate` hook to `.pre-commit-config.yaml` alongside the existing
`check-pkgdesc-consistency` hook.

The hook runs the validation wrapper which:

1. Imports all PKGBUILDs to KCL (via `pkgbuild_to_kcl.py`)
2. Compiles KCL → JSON (via `kcl run`)
3. Runs OPA policy check (via `conftest test`)

### 3.2 Implementation

```yaml
repos:
  - repo: local
    hooks:
      - id: check-pkgdesc-consistency
        name: Validate pkgdesc consistency across variants
        entry: bash scripts/check-pkgdesc-consistency.sh
        language: system
        files: ^packages/.*/PKGBUILD$
        pass_filenames: false
        always_run: false

      - id: kcl-validate
        name: KCL Schema + OPA Policy Validation
        entry: bash scripts/validate-pkgbuilds.sh
        language: system
        files: ^packages/.*/(PKGBUILD|package\.k)$
        pass_filenames: false
        require_serial: true
```

**Design decisions**:

- `pass_filenames: false` — the validator discovers all PKGBUILDs itself (needs
  all packages for cross-package rules like pkgdesc consistency).
- `require_serial: true` — ensures this hook runs alone (not in parallel with
  other hooks). The KCL compile step creates temp files that shouldn't race with
  other processes.
- `files` pattern matches both `PKGBUILD` and `package.k` — future-proofing for
  Phase 4.
- Hook runs under `language: system` — requires KCL and Conftest installed on
  the developer's machine. The `scripts/install-validator-tools.sh` script
  handles this.

### 3.3 Developer Experience

When a developer without KCL/Conftest installed makes a PKGBUILD change:

```
$ git commit -m "fix: update deps"
KCL Schema + OPA Policy Validation.......................................Failed
- hook id: kcl-validate
- exit code: 2

ERROR: kcl not found. Install with: bash scripts/install-validator-tools.sh
```

The exit code 2 (prerequisites missing) is distinct from exit code 1 (validation
failure). The commit is blocked. After installing tools, the hook passes.

**Mitigation for CI-only validation**: If developers prefer to skip local
validation, they can use `SKIP=kcl-validate git commit ...`. The CI gate catches
violations before they reach `main`. This is not recommended but is a supported
escape hatch.

---

## 4. CI Workflow Integration

### 4.1 `build.yml` — New `validate` Job

A `validate` job runs **before** the existing `execute` job, in `ubuntu-latest`
(not the builder container). This avoids polluting the builder image with KCL +
Conftest.

```yaml
name: Build
on:
  workflow_call:
    inputs:
      version:
        required: true
        type: string
      package_list:
        required: true
        type: string # JSON array of package dirs
      chunk_index:
        required: true
        type: string

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Install KCL + Conftest
        run: |
          KCL_VERSION="${KCL_VERSION:-0.12.0}"
          CONFTEST_VERSION="${CONFTEST_VERSION:-0.59.0}"
          bash scripts/install-validator-tools.sh
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"

      - name: Run KCL + OPA Validation
        run: |
          bash scripts/validate-pkgbuilds.sh

  execute:
    needs: validate
    runs-on: ubuntu-latest
    container: ghcr.io/${{ github.repository }}/arch-builder:latest
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    steps:
# ... existing steps unchanged ...
```

**Key details**:

- The `needs: validate` gate means `execute` waits for validation to pass before
  starting.
- If `validate` fails, `execute` is skipped entirely — no build artifacts are
  produced.
- The `validate` job uses the GitHub-hosted runner, not the builder container.
  This keeps the builder image lean.
- KCL and Conftest are installed fresh each CI run. With GitHub's cache,
  binaries download in <5s.

#### Fallback: Inline Validation (Alternative Design)

If the repository prefers not to add a separate job, validation can be inlined
as a step in the `execute` job's `ubuntu-latest` preamble, before the container
step. However, this pattern is discouraged because it couples the validation
toolchain to the build job's lifecycle.

### 4.2 `discovery.yml` — Pre-Push Validation Gate

Inserted after the pkgdesc consistency check and before the
`git commit`/`git push` block.

```yaml
- name: Checkout
  uses: actions/checkout@v6
  with:
    fetch-depth: 0

- id: get-updates
  name: Consolidate, Run nvchecker, and Sync
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    # ... existing nvchecker + sync-package.sh logic ...

    # Validate pkgdesc consistency before committing
    if ! bash scripts/check-pkgdesc-consistency.sh --ci; then
      echo "::error::Aborting discovery pipeline — pkgdesc consistency violations found."
      exit 1
    fi

    # ── NEW: KCL + OPA validation gate ──
    # Install tools if not already present (discovery runs on archlinux:latest)
    if ! command -v kcl &>/dev/null; then
      bash scripts/install-validator-tools.sh
      export PATH="$HOME/.local/bin:$PATH"
    fi
    if ! bash scripts/validate-pkgbuilds.sh; then
      echo "::error::Aborting discovery pipeline — KCL/OPA validation failures after sync."
      exit 1
    fi
    # ── End new gate ──

    # ... existing PREREVIEW filter + commit + push logic ...
```

**Design decision**: The discovery workflow runs in `archlinux:latest`, not
`ubuntu-latest`. KCL and Conftest are not in Arch repos. The
`install-validator-tools.sh` script downloads static binaries — this works on
Arch too since it's downloading Linux-amd64 binaries. The PATH export ensures
they're available.

### 4.3 `policy-tests.yml` — New Workflow (Phase 2 deliverable)

A standalone workflow for Rego unit tests, triggered on PR:

```yaml
name: Policy Tests
on:
  push:
    paths:
      - "policies/**"
      - "schemas/**"
      - "scripts/validate-pkgbuilds.sh"
      - "scripts/kcl_to_pkgbuild.py"
      - "scripts/pkgbuild_to_kcl.py"
  pull_request:
    paths:
      - "policies/**"
      - "schemas/**"
      - "scripts/validate-pkgbuilds.sh"
      - "scripts/kcl_to_pkgbuild.py"
      - "scripts/pkgbuild_to_kcl.py"

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Install Conftest
        run: |
          CONFTEST_VERSION=0.59.0
          bash scripts/install-validator-tools.sh
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"

      - name: Run Rego Unit Tests
        run: conftest verify --policy policies/

  integration:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Install KCL + Conftest
        run: |
          bash scripts/install-validator-tools.sh
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"

      - name: Validate All Packages
        run: bash scripts/validate-pkgbuilds.sh
```

---

## 5. Wiring the Full Pipeline

After Phase 3, the validation flow across all insertion points:

```
┌──────────────────────────────────────────────────────────────┐
│  Developer Workstation (pre-commit)                          │
│                                                              │
│  git commit                                                  │
│    └─▶ check-pkgdesc-consistency                             │
│    └─▶ kcl-validate                                          │
│         ├─ pkgbuild_to_kcl.py (import all PKGBUILDs)        │
│         ├─ kcl run (compile → manifest.json)                 │
│         └─ conftest test (policy enforcement)                │
│              ├─ deny_enforce_https                           │
│              ├─ deny_privilege_escalation                    │
│              ├─ ... (all 12 rules)                           │
│              └─ exception (per-package rule exemptions)      │
│                                                              │
│  ✓ validation passed → commit accepted                       │
│  ✗ validation failed → commit blocked                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  CI: discovery.yml                                           │
│                                                              │
│  nvchecker → sync-package.sh → check-pkgdesc → VALIDATE      │
│                                              │               │
│                                              ├─ PASS → git commit → git push
│                                              │                    │
│                                              │                    ▼
│                                              │             release.yml
│                                              │                    │
│                                              └─ FAIL → pipeline aborted
│                                                        (error message)
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  CI: build.yml (triggered by release.yml)                    │
│                                                              │
│  validate (ubuntu-latest)                                    │
│    ├─ install-validator-tools.sh                             │
│    └─ validate-pkgbuilds.sh                                  │
│         │                                                    │
│         ├─ PASS                                              │
│         │  └─▶ execute (arch-builder container)              │
│         │       ├─ Validate Metadata                         │
│         │       ├─ Check pkgdesc Consistency                 │
│         │       ├─ Check PREREVIEW Markers                   │
│         │       └─ Build Batch (makepkg)                     │
│         │                                                    │
│         └─ FAIL → execute skipped, build aborted             │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Testing Strategy

### 6.1 Renderer Unit Tests

Test fixture: `tests/fixtures/` containing known KCL JSON manifests and expected
PKGBUILD output.

| Test Case                              | Input JSON                                             | Expected Output                           |
| -------------------------------------- | ------------------------------------------------------ | ----------------------------------------- |
| Minimal package (required fields only) | `pkgname, pkgver, pkgrel, pkgdesc, arch, url, license` | Valid PKGBUILD with just those fields     |
| Package with all standard fields       | Complete `opendoas`-like manifest                      | Matches `opendoas/PKGBUILD` structurally  |
| Package with VCS source                | Source with `git+https://...#tag=`                     | Preserved in rendered PKGBUILD            |
| Package with multi-line functions      | `prepare`, `build`, `package` with line breaks         | Correct indentation, brace placement      |
| Package with optdepends                | Array of `{name, desc}` objects                        | Rendered as `'name: desc'` strings        |
| Package with boolean custom vars       | `_deploy_aur: true`                                    | Rendered as `_deploy_aur=true`            |
| Boolean false omitted                  | `_deploy_aur: false`                                   | Not present in output                     |
| Checksum array with SKIP entries       | Mixed VCS and regular source                           | `'SKIP'` entries preserved                |
| Source with `filename::url` syntax     | `{filename: "opendoas", url: "git+https://..."}`       | Rendered as `"opendoas::git+https://..."` |
| Empty optional arrays                  | `optdepends: []`                                       | Omitted from output                       |

### 6.2 Round-Trip Acceptance Test

Run `scripts/test-roundtrip.sh` against all 6 existing PKGBUILDs. Acceptance:
all 6 packages pass (rendered PKGBUILD is valid Bash, diff shows no functional
differences). Byte-level differences documented in a `roundtrip-report.md`.

### 6.3 CI Pipeline Dry Run

Before merging to `main`:

1. Push Phase 1–3 changes to a branch.
2. Observe `policy-tests.yml` passing on PR.
3. Observe `build.yml` validate job passing.
4. Manually trigger `discovery.yml` and verify the validation gate fires.

---

## 7. Phase 3 Acceptance Criteria

- [ ] `scripts/kcl_to_pkgbuild.py` renders all 6 existing packages to valid
      PKGBUILD text.
- [ ] `scripts/test-roundtrip.sh` passes: all packages round-trip through
      PKGBUILD → KCL → JSON → PKGBUILD.
- [ ] Diff report shows no functional differences between original and rendered
      PKGBUILDs.
- [ ] `.pre-commit-config.yaml` includes `kcl-validate` hook.
- [ ] Pre-commit hook blocks commits on validation failure (tested with a
      deliberately invalid PKGBUILD).
- [ ] `.github/workflows/build.yml` includes `validate` job with
      `needs: validate` gate on `execute`.
- [ ] `.github/workflows/discovery.yml` includes pre-push validation gate.
- [ ] `.github/workflows/policy-tests.yml` exists and runs `conftest verify`.
- [ ] `scripts/install-validator-tools.sh` successfully installs KCL + Conftest
      on a clean Ubuntu runner.
- [ ] All existing scripts (`sync-package.sh`, `aur-deploy.sh`,
      `arch-builder.sh`) function identically — no regressions.
