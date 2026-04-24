# Handoff: Multi-Variant Build Farm (HPA)

## 1. Objective
Transform the repository into a High-Performance Architecture (HPA) build farm capable of producing optimized binaries (e.g., x86-64-v3) alongside generic variants.

## 2. Strategic Context
- **Base Branch**: `feat/align-gha`
- **Work Branch**: `feat/hpa-builds`
- **Context**: Modern CPUs benefit from AVX2/FMA, but `makepkg` defaults to generic x86_64. We want to automate the detection and production of optimized versions.

## 3. Technical Requirements
1.  **Capability Detection**: Update hierarchical `AGENTS.md` files with an `Optimizable: Yes/No` flag.
2.  **Optimization Library**: Create `scripts/lib-opt.sh` to map microarchitecture levels to `CFLAGS`, `RUSTFLAGS`, and `GOFLAGS`.
3.  **Matrix CI**: Refactor `.github/workflows/build.yml` to use a strategy matrix for `arch_level` (e.g., `x86_64`, `x86-64-v3`).
4.  **Artifact Suffixing**: Binaries MUST be suffixed (e.g., `-v3`) or placed in architecture-specific repository paths to prevent conflicts.

## 4. Verification & Iteration
- **Self-Feedback**: If a Node.js package is caught in the matrix, the agent must refine the `AGENTS.md` scanning logic to exclude non-compilable packages.
- **Success Criteria**:
    - Parallel build jobs produce two distinct `.pkg.tar.zst` files for a single package.
    - `strings <binary> | grep AVX` (or equivalent) verifies that optimized flags were successfully applied to the v3 variant.
