# Specialized Mandates: ranger-doas

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://github.com/ranger/ranger

## 2. Automation & Transformation
- **Naive Patching**: The `update.sh` hook uses a simple `sed` replacement. This does NOT account for the missing `-b` (background) flag in `doas`. This is a known functional limitation.
- **Separation**: `update.sh` is strictly for code transformation; do not add metadata or hashing logic to this script.

## 3. Standards
- **Reproducibility**: `SOURCE_DATE_EPOCH` MUST be exported during the `build()` phase to ensure deterministic Python wheel generation.
