# Handoff: AUR "Verify-then-Publish" Workflow

## 1. Objective
Implement a secure automation path that uploads build files to the Arch User Repository (AUR) ONLY after a successful binary build and test run.

## 2. Strategic Context
- **Base Branch**: `feat/align-gha`
- **Work Branch**: `feat/aur-publishing`
- **Context**: We want to ensure that broken `PKGBUILD`s or failing tests never reach the public AUR.

## 3. Technical Requirements
1.  **Orchestration Script**: Create `scripts/publish-aur.sh`.
2.  **The Gate**: The script MUST run `pkgctl build` or a localized `makepkg` (with `check()`) before proceeding.
3.  **Metadata Parity**: `.SRCINFO` MUST be regenerated *after* the successful build to ensure it matches the verified state.
4.  **Security**: Use SSH for AUR interactions. Never log secrets or private keys during the push process.
5.  **GHA Integration**: Create a GitHub Action that triggers this script on a successful `build.yml` run for specific branches/tags.

## 4. Verification & Iteration
- **Self-Feedback**: If the build passes but the `git push` to AUR fails due to metadata mismatch, the agent must iterate on the `.SRCINFO` generation timing.
- **Success Criteria**:
    - A package build failure correctly blocks the AUR upload.
    - A package build success results in the build files being pushed to a (mocked or real) AUR remote.
