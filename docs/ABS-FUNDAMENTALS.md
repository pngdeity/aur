# Arch Build System (ABS) Fundamentals

The Arch Build System (ABS) is a framework of tools for compiling and packaging software from source. It automates the creation of standardized archives (`.pkg.tar.zst`) that can be installed by `pacman`. 

This document outlines the core components and the distinct phases of the package lifecycle.

## 1. Core Components

### A. The Scaffolding Files
- **`PKGBUILD`**: The primary Bash script defining metadata, dependencies, and build instructions.
- **`.SRCINFO`**: Static metadata generated from the `PKGBUILD` for AUR compatibility.
- **`.install` Files**: Optional scripts for package lifecycle hooks (e.g., user creation).
- **Auxiliary Files**: Local patches, systemd services, or configuration files.

### B. The Engine: `makepkg`
`makepkg` is the core utility that parses the `PKGBUILD`, creates a build environment, compiles the software, and generates the final package archive.

### C. Distribution & Management
- **Arch User Repository (AUR)**: A community repository hosting package scaffolding.
- **Custom Package Repository**: A collection of compiled binaries and a signed database (`.db.tar.gz`) for direct `pacman` installation.

---

## 2. The Packaging Lifecycle

### Phase 1: Specification & Validation (Source Stage)
The authoring and static analysis of package definitions.
- **Responsibilities**: Creating `PKGBUILD` and `.SRCINFO`, integrating patches.
- **Tools**: `namcap` for linting, `PKGBUILD(5)` for specification.

### Phase 2: Build Orchestration & Isolation (Build Stage)
The transition from specification to compiled artifact using isolated environments.
- **Responsibilities**: Executing `makepkg` in clean chroots to ensure reproducibility.
- **Tools**: `devtools` (`mkarchroot`, `makechrootpkg`).

### Phase 3: Binary Distribution (Release Stage)
Managing the custom package repository where compiled artifacts are deployed.
- **Responsibilities**: Database management via `repo-add`, package signing.
- **Tools**: `repo-add(8)`, `repo-remove(8)`.

> **Repository Context**: In this repository, Phase 3 is fully abstracted by CI/CD infrastructure. Pushing verified commits via `git push` triggers automated `repo-add --sign` and artifact hosting. Do not attempt manual database management or signing.

### Phase 4: AUR Publication (Community Stage)
Publishing raw scaffolding files to the AUR.
- **Responsibilities**: Git operations on `aur.archlinux.org` endpoints, ensuring metadata parity.

> **Repository Context**: In this repository, AUR publication is handled by external infrastructure. The local maintainer's publishing interface is `git push`; do not attempt direct Git operations on `aur.archlinux.org` endpoints.
