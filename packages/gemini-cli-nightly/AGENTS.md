# Specialized Mandates: gemini-cli-nightly

## 1. Standards
- **Version Tracking**: Implements `pkgver()` to track nightly tags; do not hardcode versions.
- **Keytar Addon**: The `build()` function manually triggers `node-gyp rebuild` for the `keytar` native module; ensure build dependencies like `libsecret` are present.
- **Test Exclusions**: Specific flaky integration tests are excluded in `check()`; consult the `PKGBUILD` before attempting to re-enable them.
