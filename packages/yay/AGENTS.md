# Specialized Mandates: yay

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://github.com/Jguer/yay

## 2. Go Standards
- **Build Environment**: Ensure `GOPATH` and `CGO` flags are correctly exported to match Arch Linux's Go packaging guidelines.
- **Testing**: Run unit tests via `make test` in the `check()` function to verify the build integrity.
