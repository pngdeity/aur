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

## References

- Initial audit: `docs/TODO.md` § CI/CD Compliance (this file)
- Code review: 2026-06-18 session, 15 issues across 7 files
- Original fixes: `packages:read` permissions, cron schedule, atomic DB rebuild,
  unused-param cleanup, stderr suppression removal
