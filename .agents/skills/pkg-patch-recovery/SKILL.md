---
name: pkg-patch-recovery
description: Recover from patch failures when an upstream Arch Linux package source changes. Use when .rej files appear, a patch fails to apply during sync-package.py, updpkgsums reports checksum mismatches, or a build fails with patch-related errors — even if the user doesn't explicitly mention "patch" or ".rej."
allowed-tools: bash
compatibility: Requires bash, git, patch, and updpkgsums. Designed for the pngdeity aur repository.
---

## Patch Recovery Workflow

When a patch fails to apply (`.rej` files appear or `patch` exits non-zero):

1. Identify the failing patch from the error output. Patches are listed in the
   `source` array of the `PKGBUILD`.

2. Clone upstream at the target version:
   ```bash
   git clone <upstream-repo-url> /tmp/upstream-recovery
   cd /tmp/upstream-recovery
   git checkout <target-tag-or-commit>
   ```

3. Attempt manual application:
   ```bash
   patch -p1 < /path/to/failing.patch
   ```

4. Resolve any `.rej` (reject) files by editing the affected source files. The
   `.rej` file shows the failed hunk in context. After resolving, delete all
   `.rej` files.

5. Generate a fresh patch:
   ```bash
   git diff > <package-dir>/<patch-name>.patch
   ```

6. Update the `PKGBUILD` source array to reference the regenerated patch if the
   filename changed.

7. Refresh checksums:
   ```bash
   updpkgsums
   ```

8. Run the full verification sequence:
   ```bash
   namcap PKGBUILD
   makepkg --printsrcinfo > /dev/null
   pkgctl build
   ```

## Gotchas

- If the upstream source has been substantially refactored, the patch may be
  obsolete. Verify whether the patch's purpose (bug fix, feature) has been
  addressed upstream before spending time on regeneration.
- For packages using `update.sh` for transformations rather than `.patch` files
  (e.g., `ranger-doas`), this workflow does not apply. Consult the package's
  local `AGENTS.md` instead.
- If `updpkgsums` fails, the upstream tarball may have been re-rolled. Verify
  the file content manually before committing new hashes.

## When to Escalate

If a patch cannot be reconciled with upstream changes after 2-3 regeneration
attempts, or if the patch addresses a security vulnerability, escalate to the
user before proceeding.
