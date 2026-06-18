---
name: pkg-update
description: Update an Arch Linux package to a new upstream version. Use when a package version has changed, nvchecker reports a delta, oldver.json is stale, the user asks to update/sync/upgrade a package, or a version bump is needed — even if the user doesn't explicitly mention "PKGBUILD" or "sync-package.py."
allowed-tools: bash
compatibility: Requires bash, namcap, makepkg, pkgctl, and nvtake. Designed for the pngdeity aur repository.
---

## Package Update Workflow

When updating a package to a new upstream version:

1. Run the sync script:
   ```bash
   python scripts/sync-package.py <pkgname> <version>
   ```
   This performs the hybrid merge with upstream, applies `update.sh`, and
   updates hashes.

2. Lint the result:
   ```bash
   namcap PKGBUILD
   ```
   Fix any issues before proceeding.

3. Validate metadata generation:
   ```bash
   makepkg --printsrcinfo > /dev/null
   ```
    `.SRCINFO` is a generated build artifact per `SRCINFO-VERSION-CONTROL-POLICY.md`
    (not version-controlled).

4. Build in a clean chroot:
   ```bash
   pkgctl build
   ```
   This verifies the package compiles and passes `check()` in an isolated
   environment.

5. Sanity check the payload:
   ```bash
   pkgctl diff --list
   ```
   Verify the primary binary, license file, and directory structure are intact.
   A payload size deviation of >10% or disappearance of `/usr/bin/` targets must
   be investigated.

6. Acknowledge the update:
   ```bash
   nvtake <pkgname>
   ```
   Refer to the
   [Debian nvtake manual](https://manpages.debian.org/testing/python3-nvchecker/nvtake.1)
   for flags. Do not hallucinate options.

7. Commit `PKGBUILD` in a single commit. Use the format
   `<pkgname>: update to <version>`. `.SRCINFO` is gitignored (see step 3).

## Gotchas

- `pkgctl build` may require a pre-configured chroot. If missing, set up with
  `mkarchroot`.
- If `updpkgsums` fails due to a re-rolled upstream tarball, verify the file
  content before accepting new hashes.
- If the `sync-package.py` merge produces conflicts, manual intervention is
  required. Hybrid merge conflict recovery is not yet automated (see
  `docs/TODO.md`).
