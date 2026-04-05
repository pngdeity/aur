# Personal Arch Linux Repository

This repository is a centralized hub for managing custom Arch Linux packages, automated with `nvchecker` and `devtools`.

## Included Packages

| Package | Description |
| :--- | :--- |
| **`ranger-doas`** | `ranger` file browser patched to use `doas` instead of `sudo`. |
| **`jules-tools`** | `jules` asynchronous coding agent from Google. |
| **`opendoas`** | OpenDoas (upstream) package, patched for enhanced security and UX. |
| **`profile-sync-daemon-opendoas`** | `profile-sync-daemon` variant using `doas`. |

## OpenDoas Patches
The `opendoas` package in this repository includes the following candidate patches:
- **`change-PATH.patch`**: Standardizes the default `PATH` to match Linux conventions (from Alpine Linux).
- **`rowhammer.patch`**: Backports security hardening to mitigate Rowhammer attacks (from GitHub PR #124).
- **`retry.patch`**: Adds a 3-try retry mechanism for password authentication, mirroring `sudo` behavior (from GitHub PR #123).
- **`arg-handling.patch`**: Improves command argument parsing and shell escaping (from GitHub PR #130).
- **`post-release-v6.8.2.patch`**: Includes all functional and documentation commits from the upstream master branch since the `v6.8.2` release, ensuring the package is at the absolute bleeding edge of the official repository.

## Automation Strategy: Scaling with nvchecker
The repository uses a professional-grade automation pipeline for version discovery and patching:

1.  **Unified Monitoring**: `nvchecker.toml` tracks all upstream sources simultaneously.
2.  **Self-Healing Patches**: For `ranger-doas`, a custom `update.sh` regenerates the `doas` patches whenever a new version is released.
3.  **Clean Build Chroot**: All packages are built in isolated, minimal containers (`extra-x86_64-build`) to ensure reproducibility.
4.  **Google Drive Deployment**: Built packages and the repository database (`my_private_repo.db`) are automatically synced to Google Drive via `rclone`.

## Installation from the Google Drive Repository (via rclone)

You can use Google Drive as a free, private repository backend for your packages.

### 1. Build and Deployment
The provided GitHub Actions workflow uses `rclone` to build the packages and sync the resulting `.pkg.tar.zst` and `.db` files to a folder named `arch-repo` in your Google Drive.

### 2. Client-Side Access: Connect pacman to Google Drive
To install these packages on your local machine, you must use `rclone` as a bridge.

#### Option A: Local Mount (Easiest)
Mount your Google Drive to a local directory:
```bash
rclone mount gdrive:arch-repo /mnt/arch-repo --daemon
```
Update `/etc/pacman.conf`:
```ini
[my_private_repo]
SigLevel = Optional TrustAll
Server = file:///mnt/arch-repo/x86_64
```

#### Option B: Local HTTP Proxy
Start an on-the-fly HTTP server using rclone:
```bash
rclone serve http gdrive:arch-repo/x86_64 --addr 127.0.0.1:8080
```
Update `/etc/pacman.conf`:
```ini
[my_private_repo]
SigLevel = Optional TrustAll
Server = http://127.0.0.1:8080
```

This setup keeps your repository completely private and inaccessible to others while remaining fully integrated into your Arch Linux package management workflow.
