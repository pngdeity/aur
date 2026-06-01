# Specialized Mandates: seiche

## 1. CMake Standards
- **Build Type**: MUST use `-DCMAKE_BUILD_TYPE=None` to allow system-wide optimization flags from `makepkg.conf` to be respected.
- **Generator**: Prefer `-G Ninja` for performance and consistency with CI runners.

## 2. Validation
- **Testing**: Automated tests MUST be run via `ctest --test-dir build` in the `check()` function.
