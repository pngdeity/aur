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

### 14a. `$srcdir` leak in binary

**Problem:** `namcap` warns `/usr/bin/pkl-lsp` contains a reference to `$srcdir`
(`pkgctl-build-output.txt` line 268). GraalVM embeds classpath/source paths in
stack traces. Cosmetic but violates Arch packaging hygiene.

**Proposed fix:** Test `-H:-PathInStackTrace` and `-H:+RemoveSaturatedTypeFlows`
flags. If ineffective, accept as cosmetic.

**Files:** `PKGBUILD`.

### 14b. `-H:+FullRelro` ✅

**Done:** Added `-H:NativeLinkerOption=-Wl,-z,relro,-z,now` (2026-06-19). `-H:+FullRelro`
doesn't exist in GraalVM 25; the correct approach is passing linker flags. namcap clean.

**Files:** `PKGBUILD` (line 99).

### 14c. Reflection surface verification

**Problem:** `run-lsp-agent.py` was written for `colelawrence/pkl-lsp`. Five
reflection surfaces (kotlin-reflect, Gson, lsp4j Proxy, jtreesitter FFM,
ServiceLoader SPI) must be verified against `apple/pkl-lsp` v0.7.1 classes.

**Proposed fix:** Run a full LSP session trace (initialize → didOpen →
completion → hover → diagnostic). Diff trace metadata against agent-generated
`META-INF/native-image/*.json`. Update agent if gaps found. Then run
`--exact-reachability-metadata` as one-off validation.

**Files:** `run-lsp-agent.py` (if gaps), `PKGBUILD` (temporary flag).

### 14d. Tighten `-H:IncludeResources` ✅

**Done:** Removed `-H:IncludeResources='.*'` entirely (2026-06-19). The
agent-generated `reachability-metadata.json` auto-detected by native-image
contains exactly 84 resources (Pkl stdlib, ServiceLoader SPI, tree-sitter
natives, Kotlin builtins, JDK resources). Binary: 328 MiB → 60 MiB (–82%),
compressed: 107 MiB → 19 MiB (–82%). Build time: 5m 36s → 2m 56s (–47%).
Verified via `-H:+GenerateEmbeddedResourcesFile` diagnostic — no class files
or Gradle artifacts embedded.

**Files:** `PKGBUILD`.

### 14e. Binary size optimization (partial)

**Done:** Primary reduction via 14d (82% drop). Added `-R:MaxHeapSize=1g` to
cap generated image runtime heap. G1GC for builder JVM (`-J-XX:+UseG1GC`)
attempted but conflicts with native-image's internal GC configuration.

**Remaining:** Verify `-H:+RemoveUnusedSymbols` active (likely default in
GraalVM 25). Evaluate dropping `-H:+ReportExceptionStackTraces` (debug info
tradeoff).

**Files:** `PKGBUILD`.

### 14f. Check function

**Problem:** No `check()` in PKGBUILD. Upstream has `./gradlew test`.

**Proposed fix:** Add smoke test (`pkl-lsp --version`). Upgrade to full Gradle
test suite if tests are fast and meaningful.

**Files:** `PKGBUILD`.

### 14g. aarch64 build validation

**Problem:** `sha512sums_aarch64` present and GraalVM aarch64 tarball in source
array, but build only tested on x86_64. Requires aarch64 hardware.

**Proposed fix:** `makepkg` on ARM host, verify LSP initialize response.

**Files:** None (build logic is arch-agnostic).

### 14h. GraalVM stable migration

**Problem:** Current `_graalvm_ver=25.1.3-dev-20260619_0111` references a dev
build because GraalVM CE 25.0.2 has a `linkToNative` bug. Dev build URL is
ephemeral.

**Proposed fix:** When GraalVM CE 25.1.x stable ships (~June 25 2026): bump
`_graalvm_ver`, update `source_x86_64`/`source_aarch64` URL patterns (stable
releases use `graalvm/graalvm-ce-builds` with different path conventions), run
`updpkgsums`, rebuild, push AUR update.

**Files:** `PKGBUILD` (lines 16, 22-27, 31-32).

### 14i. `pkl-lsp-bin` rewrite (blocked)

**Blocked:** Apple does not currently publish native binaries for `pkl-lsp`
(tracking [issue #60](https://github.com/apple/pkl-lsp/issues/60)). Plan assumes
they will follow `apple/pkl` convention: bare binaries
(`pkl-lsp-linux-{amd64,aarch64}`), no tarball, tag without `v` prefix.

**Proposed fix:** When native binaries appear: rewrite `packages/pkl-lsp-bin/`
with `_pkgname=pkl-lsp`, `provides/conflicts`, `options=('!strip')`,
`_deploy_aur=true`. Bootstrap, chroot validate, register, deploy.

**Files:** `packages/pkl-lsp-bin/PKGBUILD`, `.nvchecker.toml`.

### 14j. Metadata regeneration

**Problem:** `package.json` and `package.pkl` stale after `makedepends` changed
from `('python')` to `('git' 'python')`. Also the build warnings in
`pkgctl-build-output.txt` §0.2 need triage (7 native-image deprecation
warnings; tracked, no action until GraalVM enforces `-H:+UnlockExperimentalVMOptions`).

**Proposed fix:** Regenerate both metadata files. Document deprecation timeline.

**Files:** `package.json`, `package.pkl`.

### 14k. Native-image deprecation warnings ✅

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
