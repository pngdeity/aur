# pkl-lsp TODO

Implementation plan for deferred improvements to the `pkl-lsp` (build-from-source)
and `pkl-lsp-bin` (pre-built binary) packages.

---

## Phase 0 — Gate Completion

### 0.1 `pkgctl build` chroot validation

- [x] **Completed 2026-06-18**: Build succeeded in clean `extra-x86_64` chroot.
      Binary installed, LSP functional. Full output at `pkgctl-build-output.txt`.

### 0.2 Review `pkgctl-build-output.txt` concerns

The build produced several notifications that should be triaged:

- [ ] **`$srcdir` reference in binary** (line 268-269): `namcap` warns that
      `/usr/bin/pkl-lsp` contains a reference to `$srcdir`. GraalVM native-image
      embeds classpath and source file paths in some stack traces and exception
      messages. This is a packaging hygiene issue — Arch packages should not
      leak build paths into the binary. Investigate `-H:+RemoveSaturatedTypeFlows`
      and `-H:-PathInStackTrace` flags, or accept as cosmetic.
- [ ] **Resource scanning slowness** (line 207): native-image took ~2 minutes
      scanning ~46K entries across JARs, prompting `Resource scanning is taking
      a long time`. Caused by `-H:IncludeResources='.*'` — tightens along with
      Phase 2.2.
- [ ] **7 native-image warnings** (lines 177-185): Three experimental options
      (`IncludeResources`, `ForeignAPISupport`, `StripDebugInfo`) will require
      `-H:+UnlockExperimentalVMOptions` in future GraalVM releases. Two
      deprecated options (`--no-fallback`, `FallbackThreshold`) have no effect.
      Track GraalVM deprecation timeline; add unlock flag when required.
- [x] **`gdb-add-index: No debugging symbols`** (lines 263-265): Expected —
      `-H:+StripDebugInfo` strips debug info, so there's nothing for
      gdb-add-index to index. The debug package is empty (expected).
- [x] **`sudo: command not found`** (line 337): makechrootpkg cleanup uses
      sudo; this system uses doas. Not package-specific — ignore.
- [x] **checkpkg skipped** (lines 338-340): Not in any repo yet. Expected.
- [x] **aarch64 skipped** (line 8): Chroot only supports x86_64. Expected.

### 0.3 AUR deployment

Register `pkl-lsp` pkgbase on `aur.archlinux.org` and run
`scripts/aur-deploy.sh`. Deploy with the current dev-build GraalVM dependency;
switch to stable in Phase 4 when GraalVM 25.1.x stable ships.

- [ ] Register pkgbase on AUR
- [ ] Run `scripts/aur-deploy.sh pkl-lsp`

---

## Phase 1 — Structural Fixes

### 1.1 `-H:+FullRelro`

Add the flag to the `native-image` invocation. Fixes the only namcap warning:
`ELF file lacks FULL RELRO`.

```bash
native-image \
    ...
    -H:+FullRelro \
    ...
```

- [ ] Add flag to `build()` line ~95
- [ ] Rebuild, verify `namcap *.pkg.tar.zst` clean
- [ ] Confirmed in `pkgctl-build-output.txt` line 334: `pkl-lsp W: ELF file ('usr/bin/pkl-lsp') lacks FULL RELRO, check LDFLAGS.`
- File: `PKGBUILD`

### 1.2 Update `package.json` / `package.pkl`

Auto-generated metadata is stale after `makedepends` changed from `('python')`
to `('git' 'python')`.

- [ ] Regenerate from current PKGBUILD state
- Files: `package.json`, `package.pkl`

---

## Phase 2 — Reflection & Resource Accuracy

### 2.1 Verify `run-lsp-agent.py` reflection surfaces

The agent was originally written for `colelawrence/pkl-lsp`. Must verify all
5 surfaces exercise `apple/pkl-lsp` v0.7.1 classes:

| Surface | Expected target | Verification |
|---|---|---|
| kotlin-reflect | `org.pkl-lang.pkl-lsp.*` Kotlin classes | Full LSP session trace |
| Gson | LSP JSON message types | Initialize/completion/hover/diagnostics |
| lsp4j Proxy | LSP protocol interface methods | Method dispatch via Proxy |
| jtreesitter FFM | Panama downcalls to tree-sitter C | Document parsing |
| ServiceLoader SPI | Service provider discovery | `META-INF/services/` entries |

**Procedure**:
1. Run a full LSP session: initialize → textDocument/didOpen →
   textDocument/completion → textDocument/hover → textDocument/diagnostic
2. Collect reachability metadata from the traced session
3. Diff against agent-generated `META-INF/native-image/*.json`
4. If gaps found: update `run-lsp-agent.py`, regenerate, retry

- [ ] Full LSP session trace against built binary
- [ ] Diff trace metadata vs. agent output
- [ ] Update agent if gaps found
- Files: `run-lsp-agent.py` (if gaps found)

### 2.2 Tighten `-H:IncludeResources`

Current: `-H:IncludeResources='.*'` embeds everything in the JAR → ~328 MiB
binary. Most of this is class files that don't need resource embedding.

**Procedure**:
1. Enumerate actual resources:
   ```bash
   jar tf build/libs/pkl-lsp-0.7.1-SNAPSHOT.jar \
     | grep -v '\.class$' \
     | grep -v '^META-INF/native-image/'
   ```
2. Identify required patterns:
   - `META-INF/native-image/.*` — reachability metadata
   - `META-INF/services/.*` — ServiceLoader SPI
   - `.pkl` — Pkl stdlib files
   - Any additional classpath resources discovered in 2.1
3. Replace `'.*'` with specific globs
4. Rebuild, compare binary size, run LSP functional test

- [ ] Enumerate resources in shadow JAR
- [ ] Determine minimal IncludeResources patterns
- [ ] Update `native-image` invocation in `build()`
- [ ] Rebuild, validate LSP still functional
- File: `PKGBUILD`

### 2.3 `--exact-reachability-metadata` verification

One-off diagnostic: add `--exact-reachability-metadata` to `native-image`
invocation. This fails if any reflection, JNI, or resource usage is not
covered by the provided metadata.

- If passes: metadata is complete — remove flag (diagnostic-only)
- If fails: inspect missing registrations, update `run-lsp-agent.py`,
  regenerate metadata, retry

- [ ] Add `--exact-reachability-metadata` to `native-image`
- [ ] Build → triage result
- [ ] If gaps: update agent, regenerate metadata, retry → remove flag
- File: `PKGBUILD` (temporary), `run-lsp-agent.py` (if gaps found)

---

## Phase 3 — Completeness

### 3.1 `check()` function

Upstream has `./gradlew test`.

**Approach**: Start with a smoke test (Option B). If upstream tests are fast
and meaningful, upgrade to full Gradle test suite (Option A).

```bash
check() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    "${srcdir}/${pkgname}" --version || true   # smoke test
}
```

- [ ] Add `check()` function to PKGBUILD
- File: `PKGBUILD`

### 3.2 aarch64 build validation

Both GraalVM aarch64 tarball and `sha512sums_aarch64` are in the PKGBUILD,
but only x86_64 has been tested. Requires aarch64 hardware (GraalVM
native-image cannot cross-compile).

- [ ] Build on aarch64 host with `makepkg`
- [ ] Verify LSP binary responds to `initialize` with valid JSON-RPC
- File: no changes expected (build logic is arch-agnostic)

---

## Phase 4 — GraalVM Stable Migration

### 4.1 Switch from dev to stable GraalVM

**Current state**: `_graalvm_ver=25.1.3-dev-20260619_0111` (dev build from
`graalvm/graalvm-ce-dev-builds`). Required because GraalVM CE 25.0.2 has a
`linkToNative` bug in `PolymorphicSignatureWrapperMethod.buildGraph()` that
crashes native-image for jtreesitter FFM downcalls.

**Trigger**: GraalVM CE 25.1.x stable release on `graalvm/graalvm-ce-builds`.

**Procedure**:
1. Set `_graalvm_ver=<stable_version>` (e.g. `25.1.0`)
2. Update source URLs:
   - Stable: `https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-${_graalvm_ver}/graalvm-community-jdk-${_graalvm_ver}_linux-x64_bin.tar.gz`
   - Dev: `https://github.com/graalvm/graalvm-ce-dev-builds/releases/download/${_graalvm_ver}/graalvm-community-dev-linux-amd64.tar.gz`
   - Verify exact URL against the release page — stable and dev builds use different path/file conventions
3. Run `updpkgsums` to regenerate checksums
4. `pkgctl build` clean chroot validation
5. Commit and push update

- [ ] Monitor GraalVM releases at `graalvm/graalvm-ce-builds`
- [ ] When 25.1.x stable ships: bump `_graalvm_ver`
- [ ] Update `source_x86_64` and `source_aarch64` URL patterns
- [ ] `updpkgsums`, rebuild, validate
- File: `PKGBUILD` (lines 16, 22-27, 31-32)

---

## Phase 5 — Optimization

### 5.1 Binary size reduction

Current: 328 MiB unstripped / 106.8 MiB compressed.

**Primary lever**: Phase 2.2 (tighten `IncludeResources`). If that's
insufficient:

- [ ] Verify `-H:+RemoveUnusedSymbols` is active (default in GraalVM 25)
- [ ] Remove `-H:+ReportExceptionStackTraces` in production? (keeps debug
      info in the image — tradeoff: smaller binary vs. debuggability)
- [ ] Profile with `--verbose` to identify large embedded sections
- File: `PKGBUILD`

---

## `pkl-lsp-bin` Package Rewrite

**Blocked**: Apple does not currently publish native binaries for `pkl-lsp`.
This plan assumes they will, following the same naming conventions as
`apple/pkl` (bare binaries, no tarball, tag without `v` prefix). See
[issue #60](https://github.com/apple/pkl-lsp/issues/60) for tracking.

### Guessed format

Based on `apple/pkl` convention:

| Release asset | Platform | Example URL |
|---|---|---|
| `pkl-lsp-linux-amd64` | x86_64 | `${url}/releases/download/${pkgver}/pkl-lsp-linux-amd64` |
| `pkl-lsp-linux-aarch64` | aarch64 | `${url}/releases/download/${pkgver}/pkl-lsp-linux-aarch64` |
| `pkl-lsp-macos-aarch64` | (not packaged) | — |
| `pkl-lsp-macos-amd64` | (not packaged) | — |

Key assumptions:
- **Bare binary**, not a tarball (matches how `apple/pkl` publishes all native
  executables: `pkl-linux-amd64`, `pkl-macos-aarch64`, etc.)
- **No `v` prefix** on tag (matches `apple/pkl`: `releases/download/0.31.1/...`)
- **Same naming for lsp**: prefix `pkl-lsp-` + platform triple

### PKGBUILD structure

```bash
# Maintainer: pngdeity <pngdeity@tutanota.com>
_githubname="apple/pkl-lsp"
_pkgname=pkl-lsp
_deploy_aur=true

pkgname=pkl-lsp-bin
pkgver=<first Apple release with native binaries>
pkgrel=1
pkgdesc="Language Server Protocol implementation for Pkl (pre-built native binary)"
arch=('x86_64' 'aarch64')
url="https://github.com/apple/pkl-lsp"
license=('Apache-2.0')
depends=('glibc' 'zlib')
provides=("$_pkgname")
conflicts=("$_pkgname")
options=('!strip')

source=(
  "LICENSE::${url}/raw/v${pkgver}/LICENSE.txt"
)
source_x86_64=("${url}/releases/download/${pkgver}/pkl-lsp-linux-amd64")
source_aarch64=("${url}/releases/download/${pkgver}/pkl-lsp-linux-aarch64")
sha512sums=('SKIP')
sha512sums_x86_64=('SKIP')
sha512sums_aarch64=('SKIP')

package() {
    install -Dm755 "${srcdir}/pkl-lsp-linux-${CARCH#x86_64/amd64}" \
        "${pkgdir}/usr/bin/pkl-lsp"
    install -Dm644 "${srcdir}/LICENSE" \
        "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
```

Key design decisions:
- **`options=('!strip')`**: makepkg's default `strip` can corrupt GraalVM
  native images. Same pattern as `apm-bin`.
- **`CARCH` dispatch in `package()`**: `pkl-lsp-linux-${CARCH#x86_64/amd64}`
  maps `x86_64` → `amd64`, `aarch64` stays `aarch64`. This avoids an `if/else`.
- **`depends=('glibc' 'zlib')`**: Same runtime deps as `pkl-lsp` (GraalVM
  native images link against glibc and zlib on Linux).
- **`provides/conflicts`**: Standard variant pattern — provides the base
  `pkl-lsp` and conflicts with it so only one can be installed.

### Bootstrap steps (when Apple publishes native binaries)

- [ ] Monitor [issue #60](https://github.com/apple/pkl-lsp/issues/60)
- [ ] When native binaries appear: determine exact asset filenames and first
      release version
- [ ] Set `pkgver` to that version, update `_graalvm_ver` (if applicable)
- [ ] Set up `.nvchecker.toml`:
      ```toml
      [pkl-lsp-bin]
      source = "github"
      github = "apple/pkl-lsp"
      use_latest_release = true```
- [ ] Run `pkgctl build` clean chroot validation
- [ ] Register `pkl-lsp-bin` pkgbase on AUR, run `scripts/aur-deploy.sh pkl-lsp-bin`
- [ ] Update `package.json` / `package.pkl`

### Files (all in `packages/pkl-lsp-bin/`)

| File | Action |
|---|---|
| `PKGBUILD` | Rewrite |
| `.nvchecker.toml` | Rewrite (track `apple/pkl-lsp` instead of `colelawrence/pkl-lsp`) |
| `package.json` | Regenerate |
| `package.pkl` | Regenerate |
