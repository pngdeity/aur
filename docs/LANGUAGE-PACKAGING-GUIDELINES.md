# Packaging Guidelines Catalog

Canonical index of the Arch package guidelines. Most have moved from the Arch
Linux Wiki to the [Arch Linux Developer Manual](https://manual.archlinux.page/),
where they are maintained as the authoritative text; the wiki pages are now
redirects to them. Six articles have no Developer Manual equivalent and are
still maintained on the wiki. These 35 articles define the packaging standard
for specific languages, frameworks, build systems, and package roles.

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
| Node.js | https://manual.archlinux.page/package-guidelines/nodejs/ | `npm`, `nodejs` |
| Python | https://manual.archlinux.page/package-guidelines/python/ | `python`, `python-*` |
| Rust | https://manual.archlinux.page/package-guidelines/rust/ | `rust`, `cargo` |
| Go | https://manual.archlinux.page/package-guidelines/go/ | `go` |
| CMake | https://manual.archlinux.page/package-guidelines/cmake/ | `cmake` |
| Meson | https://manual.archlinux.page/package-guidelines/meson/ | `meson` |
| Java | https://manual.archlinux.page/package-guidelines/java/ | `java-runtime`, `jdk-openjdk`, `java-environment` |
| Ruby | https://manual.archlinux.page/package-guidelines/ruby/ | `ruby`, `rubygems` |
| Perl | https://manual.archlinux.page/package-guidelines/perl/ | `perl` |
| PHP | https://manual.archlinux.page/package-guidelines/php/ | `php` |
| Haskell | https://manual.archlinux.page/package-guidelines/haskell/ | `ghc`, `stack`, `cabal-install` |
| CLR (.NET) | https://manual.archlinux.page/package-guidelines/clr/ | `dotnet-sdk`, `mono` |
| OCaml | https://manual.archlinux.page/package-guidelines/ocaml/ | `ocaml` |
| R | https://manual.archlinux.page/package-guidelines/r/ | `r` |
| Lisp | https://manual.archlinux.page/package-guidelines/lisp/ | `sbcl`, `clisp`, `ecl` |
| Free Pascal | https://manual.archlinux.page/package-guidelines/free-pascal/ | `fpc`, `lazarus` |
| Electron | https://wiki.archlinux.org/title/Electron_package_guidelines | `electron` |
| MinGW | https://manual.archlinux.page/package-guidelines/mingw/ | `mingw-w64-*` |

## Package-Type Guidelines

Detectable by `pkgname` suffix, install path, or package purpose.

| Guideline | URL | Detection |
|-----------|-----|-----------|
| VCS | https://manual.archlinux.page/package-guidelines/vcs/ | `pkgname` ends in `-git`, `-hg`, `-svn`, `-bzr` |
| 32-bit | https://manual.archlinux.page/package-guidelines/32-bit/ | `pkgname` starts with `lib32-` |
| Kernel module | https://manual.archlinux.page/package-guidelines/kernel-module/ | `makedepends` includes `linux-headers` |
| DKMS | https://manual.archlinux.page/package-guidelines/dkms/ | `makedepends` includes `dkms` |
| Font | https://manual.archlinux.page/package-guidelines/font/ | Installs to `/usr/share/fonts/` |
| Shell | https://manual.archlinux.page/package-guidelines/shell/ | Shell scripts as executables |
| Web application | https://manual.archlinux.page/package-guidelines/webapp/ | Serves HTTP content |
| Audio plugin | https://wiki.archlinux.org/title/Audio_plugins_package_guidelines | LV2, VST, LADSPA plugins |
| Eclipse plugin | https://manual.archlinux.page/package-guidelines/eclipse-plugins/ | Eclipse IDE extensions |
| Init | https://wiki.archlinux.org/title/Init_package_guidelines | Provides system init scripts |

## Environment & Cross-Cutting Guidelines

Apply based on the package's role or target, not its build system.

| Guideline | URL | Applies When |
|-----------|-----|-------------|
| Security | https://manual.archlinux.page/package-guidelines/security/ | setuid binaries, PAM, capabilities, polkit |
| GNOME | https://manual.archlinux.page/package-guidelines/gnome/ | GNOME applications or shell extensions |
| KDE | https://manual.archlinux.page/package-guidelines/kde/ | KDE Plasma applications |
| Wine | https://manual.archlinux.page/package-guidelines/wine/ | Windows applications via Wine/Proton |
| Nonfree | https://manual.archlinux.page/package-guidelines/non-free/ | Proprietary or nonfree software |
| Cross-compiling | https://wiki.archlinux.org/title/Cross-compiling_tools_package_guidelines | Cross-toolchain packages |

## Parent Article

| Guideline | URL | Notes |
|-----------|-----|-------|
| Arch package guidelines | https://wiki.archlinux.org/title/Arch_package_guidelines | Top-level article; covers universal PKGBUILD conventions |

**Source**: [Category:Arch package guidelines](https://wiki.archlinux.org/title/Category:Arch_package_guidelines)
