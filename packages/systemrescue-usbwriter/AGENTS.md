# Specialized Mandates: systemrescue-usbwriter

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://gitlab.com/systemrescue/systemrescue-usbwriter

## 2. Build Pattern
- **Reproducibility**: Use `SOURCE_DATE_EPOCH` for injecting the build date into the binary via `sed`.
- **AppImage Removal**: This package explicitly de-AppImages the upstream source. Ensure the `_no_appimage.patch` is updated if upstream CLI flags change.
