# Specialized Mandates: gemini-cli-git

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://github.com/google-gemini/gemini-cli

## 2. VCS Standards
- **Version Tracking**: `pkgver()` MUST follow the standard git rev-list/rev-parse pattern for consistency.
- **Metadata**: Regenerate `.SRCINFO` immediately after any change to the `source` or `provides` arrays.

## 3. Node.js Standards
- **Isolation**: Use `--cache "$srcdir/npm-cache"` for all npm operations.
- **Reproducibility**: Ensure `package.json` cleanup logic matches the stable `gemini-cli` variant.
