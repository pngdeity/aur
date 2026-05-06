# Example: Package-Specific AGENTS.md

This file is an EXAMPLE of a package-level AGENTS.md. According to the root `AGENTS.md`, this file should ONLY be created if the package requires documentation for non-standard build requirements, undocumented quirks, or specific environmental constraints relevant only to this package.

## 1. Documentation Guidelines
- **Self-Healing Requirement**: Documentation must be **self-healing**. If you discover that any reference (including those below) is outdated or inconsistent during a task, you MUST update it.
- **CI/CD Changes**: If the CI/CD system or the orchestration layer (`sync-package.sh`) is refactored, the "Architectural Philosophy" section in `docs/BUILD-SYSTEM-ARCHITECTURE.md` should be updated.
- **Variable Deprecation**: If a custom variable (e.g., `_githubname`) is no longer supported, it should be documented in a "Deprecated Variables" section in `docs/PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md`.

## 2. Standards for Exceptions
- **Footnotes**: Policy exceptions documented here should ideally be accompanied by a footnote citing the official Arch Wiki or man page.
- **Intent-Focused**: Documentation should focus on the *intent* and *requirements* of the process rather than temporary implementation details.
