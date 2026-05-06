# Specialized Mandates: opendoas

## 1. Patch Management
- **PR Tracking**: This package carries several critical out-of-tree patches (Rowhammer resistance, retry limits). Always verify if these have been merged upstream before adding new ones.
- **Path Standards**: The `--default-path` option in `configure` MUST follow the Arch Linux standard path order (local first).

## 2. Security
- **Permissions**: The binary MUST be installed with setuid root permissions (4755).
- **PAM**: Do not modify `doas.pam` without verifying against the system-auth standard.
