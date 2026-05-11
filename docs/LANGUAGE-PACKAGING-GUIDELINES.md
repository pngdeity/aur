# Packaging Guidelines Catalog

Canonical index of the [Arch package guidelines](https://wiki.archlinux.org/title/Category:Arch_package_guidelines) category on the Arch Linux Wiki. These 35 articles define the packaging standard for specific languages, frameworks, build systems, and package roles.

For general packaging practice (PKGBUILD authoring, build verification, AUR, repo management), see [`docs/WIKI-REFERENCE.md`](WIKI-REFERENCE.md).

## Usage

When working on any `PKGBUILD`:
1. Scan `makedepends` and `pkgname` against the tables below.
2. Consult every matched article for community-established best practices.
3. These articles are **tier 7 (advisory)** in the project's [source authority hierarchy](../AGENTS.md#source-authority-hierarchy). If a guideline contradicts a higher-ranked source, the higher source governs. Report the discrepancy per the [escalation protocol](../AGENTS.md#conflict-resolution--escalation).

## Language & Build System Guidelines

Detectable by `makedepends` entries.

| Guideline | URL | Makedepends Key |
|-----------|-----|-----------------|
| Node.js | https://wiki.archlinux.org/title/Node.js_package_guidelines | `npm`, `nodejs` |
| Python | https://wiki.archlinux.org/title/Python_package_guidelines | `python`, `python-*` |
| Rust | https://wiki.archlinux.org/title/Rust_package_guidelines | `rust`, `cargo` |
| Go | https://wiki.archlinux.org/title/Go_package_guidelines | `go` |
| CMake | https://wiki.archlinux.org/title/CMake_package_guidelines | `cmake` |
| Meson | https://wiki.archlinux.org/title/Meson_package_guidelines | `meson` |
| Java | https://wiki.archlinux.org/title/Java_package_guidelines | `java-runtime`, `jdk-openjdk`, `java-environment` |
| Ruby | https://wiki.archlinux.org/title/Ruby_package_guidelines | `ruby`, `rubygems` |
| Perl | https://wiki.archlinux.org/title/Perl_package_guidelines | `perl` |
| PHP | https://wiki.archlinux.org/title/PHP_package_guidelines | `php` |
| Haskell | https://wiki.archlinux.org/title/Haskell_package_guidelines | `ghc`, `stack`, `cabal-install` |
| CLR (.NET) | https://wiki.archlinux.org/title/CLR_package_guidelines | `dotnet-sdk`, `mono` |
| OCaml | https://wiki.archlinux.org/title/OCaml_package_guidelines | `ocaml` |
| R | https://wiki.archlinux.org/title/R_package_guidelines | `r` |
| Lisp | https://wiki.archlinux.org/title/Lisp_package_guidelines | `sbcl`, `clisp`, `ecl` |
| Free Pascal | https://wiki.archlinux.org/title/Free_Pascal_package_guidelines | `fpc`, `lazarus` |
| Electron | https://wiki.archlinux.org/title/Electron_package_guidelines | `electron` |
| MinGW | https://wiki.archlinux.org/title/MinGW_package_guidelines | `mingw-w64-*` |

## Package-Type Guidelines

Detectable by `pkgname` suffix, install path, or package purpose.

| Guideline | URL | Detection |
|-----------|-----|-----------|
| VCS | https://wiki.archlinux.org/title/VCS_package_guidelines | `pkgname` ends in `-git`, `-hg`, `-svn`, `-bzr` |
| 32-bit | https://wiki.archlinux.org/title/32-bit_package_guidelines | `pkgname` starts with `lib32-` |
| Kernel module | https://wiki.archlinux.org/title/Kernel_module_package_guidelines | `makedepends` includes `linux-headers` |
| DKMS | https://wiki.archlinux.org/title/DKMS_package_guidelines | `makedepends` includes `dkms` |
| Font | https://wiki.archlinux.org/title/Font_package_guidelines | Installs to `/usr/share/fonts/` |
| Shell | https://wiki.archlinux.org/title/Shell_package_guidelines | Shell scripts as executables |
| Web application | https://wiki.archlinux.org/title/Web_application_package_guidelines | Serves HTTP content |
| Audio plugin | https://wiki.archlinux.org/title/Audio_plugins_package_guidelines | LV2, VST, LADSPA plugins |
| Eclipse plugin | https://wiki.archlinux.org/title/Eclipse_plugin_package_guidelines | Eclipse IDE extensions |
| Init | https://wiki.archlinux.org/title/Init_package_guidelines | Provides system init scripts |

## Environment & Cross-Cutting Guidelines

Apply based on the package's role or target, not its build system.

| Guideline | URL | Applies When |
|-----------|-----|-------------|
| Security | https://wiki.archlinux.org/title/Arch_package_guidelines/Security | setuid binaries, PAM, capabilities, polkit |
| GNOME | https://wiki.archlinux.org/title/GNOME_package_guidelines | GNOME applications or shell extensions |
| KDE | https://wiki.archlinux.org/title/KDE_package_guidelines | KDE Plasma applications |
| Wine | https://wiki.archlinux.org/title/Wine_package_guidelines | Windows applications via Wine/Proton |
| Nonfree | https://wiki.archlinux.org/title/Nonfree_applications_package_guidelines | Proprietary or nonfree software |
| Cross-compiling | https://wiki.archlinux.org/title/Cross-compiling_tools_package_guidelines | Cross-toolchain packages |

## Parent Article

| Guideline | URL | Notes |
|-----------|-----|-------|
| Arch package guidelines | https://wiki.archlinux.org/title/Arch_package_guidelines | Top-level article; covers universal PKGBUILD conventions |

**Source**: [Category:Arch package guidelines](https://wiki.archlinux.org/title/Category:Arch_package_guidelines)
