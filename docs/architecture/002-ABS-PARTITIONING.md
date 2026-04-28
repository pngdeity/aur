### Phase 1: Specification & Validation (The Source Stage)
This sub-scope is dedicated entirely to the authoring and static analysis of the package definitions. It assumes no compilation is taking place yet.
* **Core Responsibilities:** Generating valid `PKGBUILD` files, generating `.SRCINFO` files, and integrating optional auxiliary files (`.install`, `.patch`, `.service`).
* **Context Targets for Collection:**
    * Arch Linux packaging standards and naming conventions.
    * `PKGBUILD(5)` man page (variables, arrays, functions).
    * `namcap` documentation (the standard Arch Linux package analysis/linting utility).
    * Reference `PKGBUILD` files from the core/extra repositories.

### Phase 2: Build Orchestration & Isolation (The Build Stage)
This sub-scope handles the transition from specification to compiled artifact. For robust package development, this phase must handle isolated build environments to guarantee that dependencies are correctly specified and the build is reproducible.
* **Core Responsibilities:** Executing `makepkg`, managing clean chroot environments, and capturing the final `.pkg.tar.zst` artifacts.
* **Context Targets for Collection:**
    * `makepkg(8)` and `makepkg.conf(5)` man pages.
    * Arch `devtools` documentation (specifically `mkarchroot` and `makechrootpkg` for building in clean namespaces).
    * Procedures for mapping dependencies during the build process.

### Phase 3: Binary Distribution (The Release Stage)
This sub-scope is strictly concerned with managing the custom package repository where the compiled artifacts from Phase 2 are deployed.
* **Core Responsibilities:** Database creation and management, package addition/removal from the database, and exposing the repository to `pacman` clients.
* **Context Targets for Collection:**
    * `repo-add(8)` and `repo-remove(8)` man pages.
    * Database file structures (`.db.tar.gz`, `.files.tar.gz`).
    * `pacman.conf(5)` documentation for configuring clients to consume the custom repository.
    * Package signing requirements (if cryptographic verification is within your operational scope).

### Phase 4: AUR Publication (The Community Stage)
This sub-scope handles the distinct workflow of publishing the raw Phase 1 scaffolding (not the binaries) to the Arch User Repository.
* **Core Responsibilities:** Managing the Git lifecycle for AUR repositories (cloning, committing, pushing), handling SSH authentication, and ensuring `.SRCINFO` parity with the `PKGBUILD`.
* **Context Targets for Collection:**
    * AUR submission guidelines and rules.
    * AUR RPC interface documentation (useful for checking name collisions or existing packages).
    * Git operations specific to the `aur.archlinux.org` endpoints.
