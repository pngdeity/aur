# Handoff: Git Submodule Integration

## 1. Objective
Enable the repository to manage Arch Linux packages where the subdirectory is a Git Submodule pointing to an external repository.

## 2. Strategic Context
- **Base Branch**: `feat/align-gha`
- **Work Branch**: `feat/submodule-support`
- **Context**: The current `scripts/sync-package.sh` assumes all packages are local files. Mutation of submodule files without internal commits creates a "dirty" state.

## 3. Technical Requirements
1.  **Detection**: Update `scripts/sync-package.sh` to detect if a package directory is a submodule (e.g., `git rev-parse --is-inside-work-tree`).
2.  **Pointer-Based Sync**: If a submodule is detected, the script should run `git submodule update --remote` instead of attempting `sed` transformations on the `PKGBUILD`.
3.  **Context Discovery**: Ensure the hierarchical `AGENTS.md` loading still functions for subdirectories inside submodules.
4.  **Mandate Update**: Update the root `AGENTS.md` to define policies for "External Packages" (submodules).

## 4. Verification & Iteration
- **Self-Feedback**: If `sync-package.sh` fails due to "detached HEAD" or "uncommitted changes" within a submodule, the agent must refine the script to handle submodule staging.
- **Success Criteria**: 
    - A submodule package is updated to its latest upstream commit.
    - The parent repository correctly tracks the new commit hash.
    - `scripts/check-metadata.sh` passes for the submodule package.
