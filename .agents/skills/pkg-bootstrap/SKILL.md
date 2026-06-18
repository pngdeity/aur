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
     (aspirational — no current packages use this)
   - `_deploy_aur=true` if this package should be published to the AUR by the
     CI/CD pipeline
   - For CPU-optimization variants, set `_repo_subarch` (e.g., `"x86_64_v3"`) —
     mutually exclusive with `_deploy_aur` If the package is entirely custom and
     does not mirror any upstream PKGBUILD, omit the `_upstream_*` variables and
     define a standard `source` array directly. In this case, perform step 1a
     below, then skip step 2 and proceed to step 3.

1a. **Verify upstream dependencies** against the PKGBUILD `depends` and
`makedepends` arrays. For packages that do not mirror an existing Arch/AUR
PKGBUILD (no `_upstream_aur_pkg` or `_upstream_arch_repo` set), you MUST inspect
the upstream project's dependency manifest to ensure all runtime dependencies
are captured. The manifest type depends on the language — these are common
examples, not an exhaustive list:

    | Language | Manifest file |
    |----------|--------------|
    | Python   | `pyproject.toml` (`project.dependencies`) or `setup.cfg` |
    | Go       | `go.mod` (`require` directives; only cgo-linked C libs need `depends`) |
    | Rust     | `Cargo.toml` (`[dependencies]`) |

    For any other language, consult the upstream project's build
    documentation to identify its dependency manifest. For each dependency,
    map the upstream package name to its corresponding Arch Linux package
    name (e.g., `websockets` → `python-websockets`, `GitPython` →
    `python-gitpython`). Omit build-only/test-only dependencies from
    `depends` and Python stdlib modules. Add any missing entries to
    `depends` or `makedepends` as appropriate. Conditional dependencies
    (e.g., `tomli; python_version < "3.11"`) should use the Arch Python
    version as the reference — skip those gated behind an older Python
    version than Arch ships. For dependencies with version range constraints
    (e.g., `websockets>=12,<17`), verify that the packaged Arch version
    satisfies the constraint (`pacman -Si <arch-package>`). If a future
    Arch package update could breach an upper bound (e.g., `<17`), note
    the ceiling in a comment above the `depends` array so a maintainer is
    alerted during version bumps.

    If the upstream PKGBUILD already exists on the AUR or Arch GitLab,
    this check is handled automatically by `sync-package.sh` in the
    next step — skip to step 2.

2. For mirrored packages, run the bootstrap script. Look up the upstream version
   from the source repository (AUR web interface, Arch GitLab tags, or release
   page) before running:
   ```bash
   python scripts/sync-package.py <pkgname> <version>
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
