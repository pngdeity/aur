# pngdeity's Arch Linux User Repository (AUR)

This repository contains Arch Linux package sources for packages I maintain,
co-maintain, or host modified versions of.

## Automated Updates & CI/CD

This repository utilizes a CI/CD pipeline powered by GitHub Actions:

- **Upstream Monitoring:** `nvchecker` tracks upstream releases for all
  packages.
- **Automated Builds:** Packages are automatically built in a containerized Arch
  Linux environment upon upstream updates.
- **Custom Build Environment:** A specialized Docker image
  (`ghcr.io/pngdeity/aur/arch-builder`) is used to ensure consistent and fast
  build environments.
- **Repository Management:** Built packages are automatically added to the
  custom Pacman repository and deployed.

## Usage

To use this Pacman package repository, first add the GPG key to your Pacman
keyring:

```bash
sudo pacman-key --recv-keys 63CC496475267693
sudo pacman-key --lsign-key 63CC496475267693
```

Then add the following repository configuration to your `/etc/pacman.conf`:

```ini
[pngdeity]
SigLevel = Optional TrustAll
Server = https://aur.pngdeity.ru/x86_64
```

## Repository Structure

- `packages/`: Contains the `PKGBUILD` and supporting files for each package.
- `.nvchecker.toml`: Configuration for tracking upstream versions.
- `.github/workflows/`: CI/CD pipeline definitions.
- `.github/docker/`: Custom build environment definition.

## Credits

Maintained using automated tools and GitHub Actions.
