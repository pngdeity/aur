# Specialized Mandates: ranger-doas

## 1. Automation & Transformation
- **Naive Patching**: The `update.sh` hook uses a simple `sed` replacement. This does NOT account for the missing `-b` (background) flag in `doas`. This is a known functional limitation.
- **Separation**: `update.sh` is strictly for code transformation; do not add metadata or hashing logic to this script.

## 2. Standards
- **Reproducibility**: `SOURCE_DATE_EPOCH` MUST be exported during the `build()` phase to ensure deterministic Python wheel generation.
