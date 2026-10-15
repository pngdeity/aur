# CI/CD Maintenance & Improvement Tasks

Actionable items identified during the 2026-06-18 CI/CD audit. Ordered by impact /
effort ratio.

## 1. Extract Duplicated Configuration

**Problem:** Five identical `find packages -mindepth 2 -maxdepth 2 -name PKGBUILD
-exec dirname {} \; | sort` invocations across `build.yml` (x1), `release.yml`
(x2), and `aur-deploy.sh` (called by release.yml). A directory restructure
breaks three workflows simultaneously.

**Proposed fix:** Create `scripts/discover-packages.sh` that outputs the package
list. Invoke from all four locations. Single point of change for directory
structure assumptions.

**Files:** `scripts/discover-packages.sh` (new), `build.yml`, `release.yml`,
`scripts/aur-deploy.sh` (caller in `release.yml:150`).

---

## 2. Centralize Version Pins

**Problem:** Seven version pins spread across 3 files, with 3 of them duplicated
in 2 locations. `archlinux:base-devel@sha256:6d08...` appears in both
`release.yml:12` and `Dockerfile:1` — updating one but not the other causes
silent divergence. `SOURCE_DATE_EPOCH` duplicated in `build.yml` and
`release.yml`.

**Proposed fix:** Create `.github/ci-config.json` or a YAML anchor file with all
pins (`digest`, `epoch`, `pkl_version`, `conftest_version`, etc.). Source from
all workflows. For the Dockerfile, pass the digest as a build arg.

**Files:** `.github/ci-config.json` (new), `release.yml`, `build.yml`,
`Dockerfile`, `builder-image.yml`.

---

## 3. Add Unknown-Change Guard to Concern Classifier

**Problem:** `sync-package.sh:79-111` classifies upstream PKGBUILD changes into
10 categories. Any change to a line that doesn't match a known variable (e.g., a
future `confdepends=` spec addition) is silently classified as "no change" and
merged without review.

**Proposed fix:** After the 10 classification `grep` calls, add a fallthrough
that checks if any changed line remains unmatched, and flags it as `"UNKNOWN"`
to force manual review.

**Files:** `scripts/sync-package.sh`.

---

## 4. Survive Silent Builder Image Failure

**Problem:** The `arch-builder:latest` image is rebuilt weekly by
`builder-image.yml` (Sunday). Consumers (Discovery on Monday, Build/Release on
push) pull `:latest` with no verification that the image is recent. If the
Sunday build silently fails, consumers use a stale image for a full week.

**Proposed fix:** Consumer workflows should compare the pulled image's creation
timestamp against the last `builder-image.yml` run timestamp (available via
`gh run list` or GHCR API `created_at` on the manifest). Warn if gap exceeds the
rebuild interval.

**Files:** `discovery.yml`, `build.yml`, `release.yml`.

---

## 5. Notify on Upstream Merge Conflicts

**Problem:** When `sync-package.sh` encounters a three-way merge conflict (line
203), it prints a message to stderr and exits. There is no notification — the
maintainer discovers it only by checking Discovery workflow logs.

**Proposed fix:** After a merge conflict, create a GitHub Issue (via `gh issue
create`) with the conflicting diff and the package name, so the maintainer
receives a notification.

**Files:** `scripts/sync-package.sh`.

---

## 6. Validate Secrets Before Production Runs

**Problem:** Four of five CI secrets fail silently if missing — the jobs print a
`::warning::` and exit 0. In production, a missing `REPO_GPG_KEY` or
`AUR_SSH_PRIVATE_KEY` is indistinguishable from "nothing to publish."

**Proposed fix:** Add a `PRODUCTION` workflow variable. When `PRODUCTION=true`,
missing secrets should be a hard failure. Alternatively, check for a tag pattern
(`v*` = production, `workflow_dispatch` = optional).

**Files:** `release.yml`.

---

## 7. Decouple Conftest Checksum from Version

**Problem:** `build.yml:41` hardcodes a sha256sum for the conftest binary. When
`CONFTEST_VERSION` is bumped (line 30), the sum must be manually recomputed.
GitHub publishes `.sha256` files alongside releases.

**Proposed fix:** Download the checksum from the release page:
`curl -fsSL "${URL}.sha256"`. Compare against the downloaded binary.

**Files:** `build.yml`.

---

## 8. Hard-Fail on Missing Build Artifacts

**Problem:** `release.yml:31` suppresses errors when `cp *.pkg.tar.zst dist/`
fails (post-fix, `2>/dev/null` remains). If `makepkg` succeeds but produces zero
artifacts (e.g., wrong architecture), the job continues and later fails with a
confusing "no packages in repo-root" error.

**Proposed fix:** After `makepkg`, check that at least one `.pkg.tar.zst` was
produced in `$PKGDEST` before copying. Fail hard if zero files exist.

**Files:** `release.yml`, `scripts/arch-builder.sh`.

---

## 9. Add GPG Key Expiry Check

**Problem:** `release.yml:81` imports the GPG key with `gpg --import` but never
checks if the key is expired. An expired key causes `repo-add --sign` to fail
with a cryptographic error that may not clearly indicate expiry.

**Proposed fix:** After import, run `gpg --list-keys --with-colons | grep -E
'^pub:.*:e:'` to detect expired keys. Fail with a clear message.

**Files:** `release.yml`.

---

## 10. Container Image Visibility Audit

**Problem:** Could not determine via `gh` CLI whether
`ghcr.io/pngdeity/aur/arch-builder:latest` is public or private (the
authenticated token lacks `read:packages` scope). If private, external consumers
cannot pull it.

**Proposed fix:** Verify visibility in GHCR package settings. If intended to be
public, change to public. Document the decision.

**Files:** None (GHCR web UI operation).

---

## 11. Snapshot Arch Package Versions

**Problem:** The `pacman -Syu` in both Dockerfile and release.yml means every
build runs against a different set of system packages. Historical builds are
unreproducible — a user cannot determine which `gcc` or `glibc` version produced
a given `.pkg.tar.zst`.

**Proposed fix:** Add `pacman -Q > /tmp/build-package-versions.txt` after
`pacman -Syu`. Upload as a build artifact alongside packages.

**Files:** `Dockerfile`, `release.yml`, `scripts/arch-builder.sh`.

---

## 12. Remove `$OLDPWD` Reliance

**Problem:** `release.yml:111` uses `cd "$OLDPWD"` to return to the previous
directory after the `cd repo-root/x86_64/` on line 91. `$OLDPWD` is a bash
builtin, but its value is the directory before the LAST `cd`. If any script
call between lines 91 and 111 does `cd`, `$OLDPWD` is wrong.

**Proposed fix:** Save the directory explicitly: `BUILD_DIR=$(pwd)` before `cd
repo-root/x86_64/`, and `cd "$BUILD_DIR"` to return.

**Files:** `release.yml`.

---

## 13. Determine utility of github.com/apple/pkl-pantry

**Problem:** Pkl is used for package schema validation and policy check pipelines, but other configuration surfaces like GitHub Actions workflows and `.nvchecker.toml` are written in raw YAML and TOML, leading to duplicated version pins and configuration drift. We need to evaluate whether the `apple/pkl-pantry` package registry can help us centralize and type-validate these configurations without reinventing the wheel.

**Proposed fix:** Integrate and leverage specific packages from `package://pkg.pkl-lang.org/pkl-pantry/`:
1. **`com.github.actions` (High Utility):** Allows defining our four GitHub Actions workflows (`build.yml`, `release.yml`, `discovery.yml`, `builder-image.yml`) in Pkl. This allows centralizing all version pins, directories, and shared steps in a single Pkl config, then compiling them to YAML. This directly resolves **Item #1** (duplicated package discovery commands) and **Item #2** (centralizing version pins) in a typesafe manner.
2. **`pkl.toml` (Moderate Utility):** Can generate `.nvchecker.toml` dynamically from our package registry declarations if we decide to generate nvchecker targets programmatically rather than managing them manually.
3. **Arch Linux Schemas (None):** The pantry has no native support for Arch Linux or pacman configuration formats; we must continue maintaining our custom `schemas/arch_pkg.pkl`.

**Files:** `.github/workflows/`, `.nvchecker.toml`.

---

## 14. `pkl-lsp` Package Deferred Improvements

All items refer to `packages/pkl-lsp/` — builds a GraalVM native image of
`apple/pkl-lsp` v0.7.1. Package is live on the AUR. Chroot build validated.

### 14a. `$srcdir` leak in binary (done)

**Problem:** `namcap` warns `/usr/bin/pkl-lsp` contains a reference to `$srcdir`
(`pkgctl-build-output.txt` line 268). GraalVM embeds classpath/source paths in
stack traces. Cosmetic but violates Arch packaging hygiene.

**Investigated (2026-10-15):** Both proposed flags are wrong for this.

- `-H:-PathInStackTrace` does not exist in GraalVM 25. There is no option of
  that name — `native-image --expert-options-all` (2661 lines) has no
  `PathInStackTrace` entry. The nearest matches are runtime stack-trace
  controls (`-H:MaxJavaStackTraceDepth`, `-H:±OmitHotExceptionStacktrace`,
  `-H:±StackTrace` which is "Deprecated, has no effect") and none of them strip
  build-time source paths from the image.
- `-H:±RemoveSaturatedTypeFlows` **is already enabled by default**
  (`--expert-options-all`: "Default: + (enabled)"), so passing it changes
  nothing.

**Root cause of the leak (reproduced):** The strings are real source artifacts,
not stack-trace metadata. The built binary contains
`/tmp/makepkg/pkl-lsp/src/pkl-lsp-0.7.1/.gradle/zig/zig-linux-amd64-0.16.0/lib/libc/include/generic-glibc/*.h`
and `build/repos/tree-sitter` paths. The pkl-lsp native build compiles
tree-sitter via **zig**, and the bundled zig libc headers carry absolute build
paths into the object files that `native-image` then links. No native-image
flag governs strings that arrive via the linker from a foreign toolchain.

**Status:** Accepted as cosmetic. Removing it would require controlling zig's
header staging (patching upstream's `zig.gradle.kts`/tree-sitter build) for a
warning with no runtime effect.

**Files:** `PKGBUILD` (no change), `buildSrc/.../zig.gradle.kts` (upstream).

### 14b. `-H:+FullRelro` (done)

**Done:** Added `-H:NativeLinkerOption=-Wl,-z,relro,-z,now` (2026-06-19). `-H:+FullRelro`
doesn't exist in GraalVM 25; the correct approach is passing linker flags. namcap clean.

**Files:** `PKGBUILD` (line 99).

### 14c. Reflection surface verification (done)

**Problem:** `run-lsp-agent.py` was written for `colelawrence/pkl-lsp`. Five
reflection surfaces (kotlin-reflect, Gson, lsp4j Proxy, jtreesitter FFM,
ServiceLoader SPI) must be verified against `apple/pkl-lsp` v0.7.1 classes.

**Root cause (found 2026-10-15):** The old driver spawned the JAR as a
subprocess over pipes, so the tracing agent observed only JSON-RPC wire traffic.
lsp4j's launcher reflection surface (`Launcher.Builder.create()` delegate
discovery, `ServiceEndpoints.toEndpoint` / `toServiceObject` proxy creation,
`GenericEndpoint` construction) never executed in the traced JVM. The resulting
metadata therefore registered **0 of 565** lsp4j classes and was structurally
blind to the whole DTO surface. Reproduced live against the installed package:
a well-formed `initialize` carrying `workspaceFolders` aborted with
`MissingReflectionRegistrationError: Cannot reflectively invoke constructor
'public org.eclipse.lsp4j.WorkspaceFolder()'` and published no diagnostics.

**Done:** Replaced the subprocess driver with upstream's two-step mechanism
(`apple/pkl-lsp` PR #226, which is why this issue is fixed upstream):

1. `RunLspAgent.java` — hosts client and server **in the same JVM** (mirrors
   upstream `simpleclientrunner`), so the agent observes the lsp4j launcher
   internals. 243 reflection entries, 5 `proxy` entries (`LanguageServer`,
   `TextDocumentService`, `WorkspaceService`, `NotebookDocumentService`,
   `PklLanguageClient`), a `foreign` key (FFM/tree-sitter) and 12 resources.
   Still only 182/565 lsp4j classes — the sweep is what closes the remainder.
2. `merge-lsp4j-metadata.py` — the classgraph equivalent (upstream
   `reflectionmetadatagenerator`): drops agent `org.eclipse.lsp4j` entries, then
   registers every `org/eclipse/lsp4j/**.class` in the fat JAR. Final metadata:
   **626 reflection entries** (565 lsp4j + 61 agent), 5 proxies, 1 foreign,
   12 resources.

`run-lsp-agent.py` is deleted. Verified A/B on the same request: installed
0.7.1-3 crashes with the `WorkspaceFolder` error; the rebuilt binary returns a
valid `initialize` result advertising `workspace.workspaceFolders.changeNotifications`
and serves a full session with clean stderr. 31.63 MiB stripped in 2m45s.

**Injection path (found 2026-10-15, after the first three builds):** the merged
metadata was produced correctly but the binary still died, this time on the
`PklLanguageClient`/`Endpoint` proxy. `jar -u` stores the archive path verbatim
from its argument, and more importantly native-image only scans
`META-INF/native-image/<group>/<artifact>/*.json`. A file placed directly at
`META-INF/native-image/reachability-metadata.json` is **silently ignored** —
confirmed with controlled probes: the direct-child path produced no
`Apply jar:...` line under `native-image --verbose`, while one- and two-level
subdirectories both did. The recipe now stages to
`META-INF/native-image/${pkgname}/${pkgname}/reachability-metadata.json` and
guards the result, because without that guard the build silently succeeds and
ships a binary that crashes on any real LSP client.

**Guard corrected for the chroot (same day):** the first successful
`pkgctl build` failed at the guard with
`/startdir/PKGBUILD: line 111: unzip: command not found` — `unzip` is not in
base-devel, so the check was inoperable for every AUR user. Replacing it exposed
a second trap: `jar` has no stdout-extract mode, and `jar --extract` returns
**exit 0 even when it matches nothing**, so its status cannot serve as the gate.
The guard now extracts into `${srcdir}/jar-verify` and tests for the file on
disk before grepping `"proxy"`. Verified both ways — a bogus path leaves no file
and trips the guard; the real entry yields 5 proxy entries. Uses only `jar`,
`mkdir`, `rm` and `grep`, so no new `makedepends`.

Also fixed here: `--initialize-at-build-time=` (empty argument) means
*initialize all packages* — once lsp4j was registered it ran
`com.sun.jna.internal.Cleaner`'s static initializer at build time and failed with
`UnsupportedFeatureException: Detected a started Thread in the image heap.
Thread name: JNA Cleaner.` The flag is removed. Upstream passes neither
`--initialize-at-build-time` nor `--initialize-at-run-time`.

**Not fixed (not packaging):** `PklLspServer.kt:79` throws `NullPointerException`
in `initialized()` when the client's `initialize` omits the `workspace`
capability. Upstream Kotlin source bug, present in tag `0.7.1`.

**Files:** `RunLspAgent.java`, `merge-lsp4j-metadata.py`, `PKGBUILD`.

### 14d. Tighten `-H:IncludeResources` (done)

**Done:** Removed `-H:IncludeResources='.*'` entirely (2026-06-19). The
agent-generated `reachability-metadata.json` auto-detected by native-image
contains exactly 84 resources (Pkl stdlib, ServiceLoader SPI, tree-sitter
natives, Kotlin builtins, JDK resources). Binary: 328 MiB → 60 MiB (–82%),
compressed: 107 MiB → 19 MiB (–82%). Build time: 5m 36s → 2m 56s (–47%).
Verified via `-H:+GenerateEmbeddedResourcesFile` diagnostic — no class files
or Gradle artifacts embedded.

**Files:** `PKGBUILD`.

### 14e. Binary size optimization (partial) (done)

**Done:** Primary reduction via 14d (82% drop). Added `-R:MaxHeapSize=1g` to
cap generated image runtime heap. G1GC for builder JVM (`-J-XX:+UseG1GC`)
attempted but conflicts with native-image's internal GC configuration.

**Remaining:** Both flagged items are now resolved (2026-10-15):

- `-H:+RemoveUnusedSymbols` is **already enabled by default** in GraalVM 25
  (`--expert-options-all`: "Use linker option to prevent unreferenced symbols in
  image. Default: + (enabled)"). Nothing to add.
- `-H:+ReportExceptionStackTraces` also **requires no unlock** — it is a plain
  `-H:±` expert option ("Show exception stack traces for exceptions during image
  building. Default: - (disabled)"), unlike `-H:+StripDebugInfo` which is gated
  behind `-H:+UnlockExperimentalVMOptions`. It is left enabled deliberately:
  the cost is build-time-only verbosity in the event of a build failure, with no
  effect on the produced image. The existing unlock scope stands as-is.

**Files:** `PKGBUILD` (no change).

### 14f. Check function (done)

**Done:** Added `check()` as a smoke test (`pkgname --version | grep -q "^${pkgname} version "`). The full upstream Gradle suite is deliberately not used: it downloads a ~95 MB native Pkl CLI as a test dependency and needs two custom JUnit 5 engines plus `--enable-native-access=ALL-UNNAMED`, so it is unsuitable for a distribution build. Rationale recorded in `docs/TODO.md` under Completeness. Chroot-validated with the rest of the package on 2026-10-15.

**Files:** `PKGBUILD` (lines 150-154).

### 14g. aarch64 build validation

**Problem:** `sha512sums_aarch64` present and GraalVM aarch64 tarball in source
array, but build only tested on x86_64. Requires aarch64 hardware.

**Proposed fix:** `makepkg` on ARM host, verify LSP initialize response.

**Files:** None (build logic is arch-agnostic).

### 14h. GraalVM stable migration (done)

**Done:** Migrated from the pruned `graalvm-ce-dev-builds` tag
`25.1.3-dev-20260619_0111` (upstream 404s) to the current stable GraalVM CE
release `25.4.4.1.1`. Moved to `graalvm-ce-builds` and the stable asset naming
(`graalvm-community-jdk-25i4-25.0.4.1.1_linux-{x64,aarch64}_bin.tar.gz`),
registered in `_graalvm_dir`. Checksums regenerated via `updpkgsums`; both
tarballs verified to contain `bin/native-image`. Local `makepkg` build succeeds:
`native-image` completes, binary reports `pkl-lsp version 0.7.1-dev+`, namcap
clean. Committed 2026-09-29.

**Files:** `PKGBUILD` (lines 18-35).

### 14i. `pkl-lsp-bin` rewrite (blocked)

**Blocked:** Apple does not currently publish native binaries for `pkl-lsp`
(tracking [issue #60](https://github.com/apple/pkl-lsp/issues/60)); the GitHub
releases ship only a `.jar`. Interrogated `apple/pkl-lsp` releases through
0.8.0 — every tag has exactly one asset, the JAR.

**Partial (2026-09-29):** Metadata hygiene applied without awaiting binaries —
maintainer line corrected, `_pkgname=pkl-lsp` added, `pkgdesc` aligned with the
base, `url`/`_githubname` pointed at `apple/pkl-lsp`, `_deploy_aur` removed
(previously set, and would have pushed the stale fork to the AUR), duplicate
`.nvchecker.toml` removed, `pkgrel` bumped to 2. The package is now explicitly
marked DEPRECATED in the PKGBUILD header.

**Remaining fix:** When native binaries appear: repoint source URLs, add
`options=('!strip')`, set `_deploy_aur=true`. Bootstrap, chroot validate,
register, deploy.

**Files:** `packages/pkl-lsp-bin/PKGBUILD`, root `.nvchecker.toml`.

### 14j. Metadata regeneration (done)

**Done:** Regenerated 2026-09-29 via `scripts/validate-pkgbuilds-pkl.sh`, which
now passes end-to-end (25 packages, exit 0). Required a `pkl_writer.py` fix:
the emitter no longer includes arbitrary local `_`-prefixed variables, only the
custom variables declared in `schemas/arch_pkg.pkl` (previously `_graalvm_ver`
produced invalid Pkl). Regenerated metadata reflects the corrected maintainer,
`pkgname`, `pkgrel`, `url`, and `makedepends`.

**Files:** `package.json`, `package.pkl` (generated artifacts, not tracked).

### 14k. Native-image deprecation warnings (done)

**Done:** Removed `-H:+ForeignAPISupport` (default-on in GraalVM 25.0+, causes
warning when passed explicitly). Removed `--no-fallback` (deprecated, no effect).
Removed `-H:-ParseRuntimeOptions` (unnecessary). Added `-H:+UnlockExperimentalVMOptions`
/ `-H:-UnlockExperimentalVMOptions` scope around `-H:+StripDebugInfo` (remains
experimental). Warnings: 7 → expected 1-2. Committed as `d60f980`, deployed as
pkgrel 3.

**Remaining:** Triage `-H:+ReportExceptionStackTraces` — may also require
unlocking. Consider adding to the existing unlock scope if needed.

**Files:** `PKGBUILD`.

---

## References

- Initial audit: `docs/TODO.md` § CI/CD Compliance (this file)
- Code review: 2026-06-18 session, 15 issues across 7 files
- Original fixes: `packages:read` permissions, cron schedule, atomic DB rebuild,
  unused-param cleanup, stderr suppression removal
