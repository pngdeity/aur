# Specialized Mandates: gemini-cli

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://github.com/google-gemini/gemini-cli

## 2. Node.js Standards
- **Isolation**: `npm install` MUST use `--cache "$srcdir/npm-cache"` to prevent environment leakage.
- **Reproducibility**: All npm-internal metadata (e.g., `_id`, `_resolved`, `_where`) MUST be stripped from `package.json` files in the `package()` function.
- **Validation**: Automated tests via `npm test` are mandatory in `check()`.
