# Repository Manager's Manual Intervention Guide

This guide outlines the specific steps you must take when the automated pipeline requires human intervention.

## 1. **Infrastructure & Secrets Setup**
When setting up a new repository or updating access:

### **Generating Rclone Secrets**
1.  On a local machine with `rclone` installed, run `rclone config` to set up your Google Drive remote (name it `gdrive`).
2.  Locate your `rclone.conf` (usually `~/.config/rclone/rclone.conf`).
3.  Base64-encode the file: `base64 -w 0 ~/.config/rclone/rclone.conf | xsel -b`.
4.  Add the result to your GitHub Repository Secrets as `RCLONE_CONFIG_BASE64`.

---

## 2. **Adding a New Package**
To add a new package to the repository:

### **Standard Package (AUR/GitHub/NPM)**
1.  Create a new folder: `mkdir -p packages/new-pkg`.
2.  Place a valid `PKGBUILD` and any required files (e.g., `.install`) in that folder.
3.  Add the package to `nvchecker.toml`:
    ```toml
    [new-pkg]
    source = "github"
    github = "user/repo"
    use_latest_tag = true
    ```
4.  Initialize the version in `nvc_versions.json`:
    ```json
    "new-pkg": "0.0.1"
    ```
5.  Commit and push: `git add . && git commit -m "feat: add new-pkg" && git push`.

### **Custom Patched Package (e.g., ranger-doas)**
Follow the steps above, then:
1.  Create an `update.sh` in `packages/new-pkg/`.
2.  Define the `sed` or `patch` logic in the script (it will receive the new version as `$1`).
3.  Test it locally before pushing: `cd packages/new-pkg && ./update.sh <version>`.

---

## 3. **Handling Automation Failures (CI Broken)**
When a GitHub Action fails (Red X):

### **Diagnosing the Failure**
1.  Open the GitHub Actions log for the failed run.
2.  **Case A: Patch Failed (`patch -Np1 -i ...` returned 1)**
    *   The upstream code has changed significantly.
    *   Manually clone the upstream repo at the new version.
    *   Attempt to apply the patch: `patch -p1 < your-patch.patch`.
    *   Fix the rejects (`.rej` files) and generate a new patch: `git diff > new-patch.patch`.
    *   Update the file in your repository and push.
3.  **Case B: Checksum Failed (`sha256sums` mismatch)**
    *   The upstream author may have re-rolled the release.
    *   Go to the package directory and run `updpkgsums`.
    *   Commit the updated `PKGBUILD`.
4.  **Case C: Missing Dependency**
    *   Update the `depends` or `makedepends` array in the `PKGBUILD`.

---

## 4. **Maintaining OpenDoas Patches**
The `opendoas` package requires proactive curation:

### **Updating Candidate Patches**
If a GitHub PR is updated:
1.  Navigate to `packages/opendoas/`.
2.  Re-download the patch: `curl -L -O https://github.com/Duncaen/OpenDoas/pull/<PR_ID>.patch`.
3.  Run `updpkgsums` and push.

### **New Official Release (e.g., v6.9.0)**
1.  **Delete the old snapshot patch**: `rm packages/opendoas/post-release-v6.8.2.patch`.
2.  **Verify Candidate Patches**: Check the `v6.9.0` source to see if `retry.patch` or others were merged.
3.  **Update `PKGBUILD`**: Remove merged patches from the `source` array and `prepare()` function.
4.  **Update `nvc_versions.json`**: Update the `opendoas` version manually if needed.

---

## 5. **Security & GPG Signing (Optional)**
If you decide to enable package signing:
1.  Generate a GPG key locally: `gpg --full-generate-key`.
2.  Export the private key: `gpg --export-secret-keys --armor YOUR_KEY_ID`.
3.  Store it in GitHub Secrets as `GPG_PRIVATE_KEY`.
4.  Modify `repo-master.yml` to run `repo-add --sign` (ensure `makepkg.conf` in the chroot is also configured for signing).

---

## **Final Verification Checklist**
Before pushing any manual change:
- [ ] Does the `PKGBUILD` pass `namcap`?
- [ ] Does `updpkgsums` run without errors?
- [ ] Are all variables in the `PKGBUILD` properly quoted?
- [ ] Did you remember to reset `pkgrel` to `1` for new versions?
