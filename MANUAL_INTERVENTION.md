# Repository Manager's Manual Intervention Guide

This guide outlines the specific steps required when the automated pipeline fails or when manual package maintenance is necessary.

---

## 1. **Automated Maintenance with `sync-package.sh`**
The primary tool for updating a package is `bash scripts/sync-package.sh <pkgname> <version>`. 

This script automates:
1.  **Version Update**: Updates `pkgver` and resets `pkgrel` to `1` in the `PKGBUILD`.
2.  **Changelog Generation**: Automatically fetches GitHub release notes if `_githubname` is defined in the `PKGBUILD`.
3.  **Checksum Updates**: Runs `updpkgsums` to refresh the `sha256sums` array.

**Action**: Use this script whenever possible before resorting to manual edits.

---

## 2. **Adding a New Package**
To add a new package to the repository:

### **Standard Package (AUR/GitHub/NPM)**
1.  **Directory Structure**: Create a new folder in `packages/`.
2.  **PKGBUILD**: Place a valid `PKGBUILD`. Ensure the first line is exactly:
    ```bash
    # Maintainer: pngdeity <pngdeity@tutanota.com>
    ```
3.  **Version Tracking**: Initialize the package version in `oldver.json`.
4.  **Metadata**: Generate the mandatory `.SRCINFO` file:
    ```bash
    makepkg --printsrcinfo > .SRCINFO
    ```
5.  **Automation**: Add the package to `.nvchecker.toml` in the root and in the package's subdirectory.

### **Custom Patched Package**
Follow the steps above, then:
1.  **Update Script**: Create an `update.sh` in the package directory to handle complex patching or `sed` logic.
2.  **Logic**: Ensure it accepts the new version as `$1` and produces the necessary patches/changes.

---

## 3. **Handling Automation Failures (CI Broken)**
When a GitHub Action fails:

### **Case A: Patch Failed**
*   **Cause**: The upstream source code changed significantly, and the existing patch no longer applies cleanly.
*   **Resolution**: 
    1.  Manually clone the upstream repo at the target version.
    2.  Attempt to apply the patch: `patch -p1 < your-patch.patch`.
    3.  Resolve rejects (`.rej` files), delete them, and generate a new patch: `git diff > new-patch.patch`.
    4.  Update the `PKGBUILD` and refresh checksums.

### **Case B: Checksum Failed**
*   **Cause**: Upstream re-rolled the release or the download was corrupted.
*   **Resolution**: Run `updpkgsums` in the package directory and verify the file content.

---

## 4. **Maintaining opendoas Patches**
The `opendoas` package is heavily patched and requires proactive curation:

### **Updating Candidate Patches**
If a GitHub PR is updated:
1.  Re-download the patch to `packages/opendoas/`.
2.  Run `updpkgsums` and update `.SRCINFO`.

### **New Official Release**
1.  **Cleanup**: Delete the old snapshot patch (e.g., `post-release-v6.8.2.patch`).
2.  **Audit**: Check the new source to see if existing candidate patches (e.g., `retry.patch`) were merged upstream.
3.  **Refactor**: Remove merged patches from the `PKGBUILD`'s `source` array and `prepare()` function.

---

## 5. **Security & GPG Signing**
The repository uses `repo-add --sign` to ensure users can verify the integrity of the package database.

### **Setup Instructions**
1.  **Generate Key**: `gpg --full-generate-key` (Use RSA/RSA, 4096 bit, no expiry).
2.  **Export Private Key**: `gpg --export-secret-keys --armor <KEY_ID>`.
3.  **GitHub Secrets**: Add the exported key to a secret named `REPO_GPG_KEY`.
4.  **Verification**: The `release.yml` workflow will automatically import this key and sign the database (`nightly.db`) during the publishing phase.

---

## **Final Verification Checklist**
Before pushing any manual change:
- [ ] Does the `PKGBUILD` pass `namcap`?
- [ ] Does it contain the mandatory Maintainer flag?
- [ ] Is the `.SRCINFO` file updated (`makepkg --printsrcinfo > .SRCINFO`)?
- [ ] Did you reset `pkgrel` to `1` for new versions?
- [ ] Are all variables properly quoted in the `PKGBUILD`?
