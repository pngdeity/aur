---
name: pkg-bootstrap
description: Initialize a new Arch Linux package in the repository. Use when adding a new package, creating a PKGBUILD from scratch, bootstrapping from an upstream AUR or Arch GitLab source, or setting up a package for the first time — even if the user doesn't explicitly mention "bootstrap" or "PKGBUILD."
allowed-tools: bash
compatibility: Requires bash, pkgctl, and makepkg. Designed for the pngdeity aur repository.
---

## Package Bootstrap Workflow

When adding a new package to `packages/`:

1. Create the package directory and a minimal `PKGBUILD`. For packages that
   mirror an existing Arch or AUR package, define the upstream source variable
   and the maintainer demotion flag:
   - `_upstream_aur_pkg` for AUR packages
   - `_upstream_arch_repo` for official Arch GitLab packages
   - `_demote_upstream_maintainer=true` to automatically demote upstream
     maintainers to contributors
   - `_pkgname=<canonical-name>` to declare the canonical software name (set on
     ALL packages in a variant family, including the base). If the package is
     standalone with no variants, omit `_pkgname`.
   - For `gemini-cli` variants, add `_use_common_gemini_settings=true`
   - `_deploy_aur=true` if this package should be published to the AUR by the
     CI/CD pipeline
   - For CPU-optimization variants, set `_repo_subarch` (e.g., `"x86_64_v3"`) —
     mutually exclusive with `_deploy_aur` If the package is entirely custom and
     does not mirror any upstream PKGBUILD, omit the `_upstream_*` variables and
     define a standard `source` array directly. In this case, skip step 2 and
     proceed to step 3.

2. For mirrored packages, run the bootstrap script. Look up the upstream version
   from the source repository (AUR web interface, Arch GitLab tags, or release
   page) before running:
   ```bash
   bash scripts/sync-package.sh <pkgname> <version>
   ```
   This fetches the upstream PKGBUILD, initializes tracking state, applies
   declarative identity rules (demotion, asset sync), and updates hashes. Only
   one invocation is needed.

3. Set up version checking from within the package directory:
   ```bash
   pkgctl version setup
   ```
   This generates a valid `.nvchecker.toml` from the PKGBUILD source array.

4. Create a package-local `AGENTS.md` ONLY if the package has non-standard build
   requirements, undocumented quirks, or specific environmental constraints.
   Otherwise skip this step. The file must follow the Hierarchical Policies in
   the root `AGENTS.md`.

5. Register the package in the root `.nvchecker.toml` for global version
   monitoring. Also ensure the `[__config__]` section has `oldver` and `newver`
   paths configured (e.g., `oldver = "oldver.json"`, `newver = "newver.json"`),
   otherwise `nvtake` will fail.

6. Run the full verification sequence:
   ```bash
   namcap PKGBUILD
   makepkg --printsrcinfo > /dev/null
   pkgctl build
   pkgctl diff --list
   ```

## Gotchas

- The `sync-package.sh` script expects the upstream source variable to be set
  correctly. If the upstream package uses a non-standard name, verify the
  variable before bootstrapping.
- `pkgctl version setup` must be run inside the package directory. The
  `.nvchecker.toml` it generates is package-specific.
