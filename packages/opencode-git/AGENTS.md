# AGENTS.md - opencode-git Package Policy

This document defines package-specific mandates and tribal knowledge for `opencode-git`.

## Upstream Reference
- **Canonical Source**: [anomalyco/opencode](https://github.com/anomalyco/opencode)
- **Reference Instruction**: All build logic, environment requirements, and architectural assumptions MUST be validated against the upstream repository's `package.json` and build scripts.

## Tribal Knowledge
- **Build System**: This package is built using **Bun**. The `prepare()` function uses `bun install --frozen-lockfile` to ensure deterministic builds.
- **External Dependencies**: The build requires an external JSON file (`models.dev-api.json`) fetched from `https://models.dev/api.json`. This is handled via the `source` array and the `MODELS_DEV_API_JSON` environment variable during `build()`.
- **Targeting**: The package supports `x86_64` and `aarch64`. The `_target_arch()` function maps the Arch Linux `${CARCH}` to the application's internal architecture naming (`x64` or `arm64`).
- **Binary Extraction**: The final binary is extracted from a platform-specific path: `packages/opencode/dist/opencode-linux-${target}/bin/opencode`.

## Maintenance Routine
- **Version Tracking**: Uses `nvchecker` via the global `.nvchecker.toml` and package-local `.nvchecker.toml`.
- **VCS Versioning**: The `pkgver()` function follows standard Arch VCS guidelines, combining the version from `package.json` with the git commit count and hash.
