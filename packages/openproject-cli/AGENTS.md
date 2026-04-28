# Specialized Mandates: Documentation Template

## 1. Documentation Updates
- **CI/CD Changes**: If the CI/CD system or the orchestration layer (`sync-package.sh`) is refactored, you MUST update the "Architectural Philosophy" section in `REFERENCE.md`.
- **Variable Deprecation**: If a custom variable (e.g., `_githubname`) is no longer supported by the scripts, it MUST be moved to a "Deprecated Variables" section in `REFERENCE.md` with an explanation of why it was removed.

## 2. Standards
- **Footnotes**: All new policy mandates in this directory MUST be accompanied by a footnote citing the official Arch Wiki or man page, including the 'Last Modified' date of the source.
- **Abstractness**: When describing processes, avoid referencing specific line numbers or temporary filenames in the current script implementation. Focus on the *intent* and *requirements* of the process.
