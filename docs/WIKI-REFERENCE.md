# Arch Wiki Reference Catalog

Comprehensive index of the Arch Linux Wiki articles relevant to this
repository's packaging operations. These articles are **tier 7 (advisory)** in
the project's
[source authority hierarchy](../AGENTS.md#source-authority-hierarchy). Consult
them for community-established best practices, but verify against higher-ranked
sources when discrepancies arise.

**Source categories**:
[Category:Package development](https://wiki.archlinux.org/title/Category:Package_development)
and
[Category:Package management](https://wiki.archlinux.org/title/Category:Package_management).

**See also**:
[`docs/LANGUAGE-PACKAGING-GUIDELINES.md`](LANGUAGE-PACKAGING-GUIDELINES.md) for
language-specific and framework-specific packaging guidelines (35 articles from
[Category:Arch package guidelines](https://wiki.archlinux.org/title/Category:Arch_package_guidelines)).

---

## PKGBUILD Authoring

Consult these when writing, editing, or syncing a `PKGBUILD`.

| Article                        | URL                                                             | Relevant To                                      |
| ------------------------------ | --------------------------------------------------------------- | ------------------------------------------------ |
| Creating packages              | https://wiki.archlinux.org/title/Creating_packages              | All `PKGBUILD` authoring                         |
| PKGBUILD                       | https://wiki.archlinux.org/title/PKGBUILD                       | Variable definitions, functions, conventions     |
| .SRCINFO                       | https://wiki.archlinux.org/title/.SRCINFO                       | Metadata generation, `makepkg --printsrcinfo`    |
| Patching packages              | https://wiki.archlinux.org/title/Patching_packages              | `source` array patches, `prepare()`, `update.sh` |
| Meta package and package group | https://wiki.archlinux.org/title/Meta_package_and_package_group | `pkgbase`, `groups` array, split packages        |

## Build & Verification

Consult these when building, linting, or validating a package.

| Article                    | URL                                                                       | Relevant To                                            |
| -------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------ |
| Makepkg                    | https://wiki.archlinux.org/title/Makepkg                                  | Build execution, flag usage, environment variables     |
| Namcap                     | https://wiki.archlinux.org/title/Namcap                                   | Static analysis of `PKGBUILD` and binary packages      |
| Building in a clean chroot | https://wiki.archlinux.org/title/DeveloperWiki:Building_in_a_clean_chroot | `pkgctl build`, `makechrootpkg`, environment isolation |
| Reproducible Builds        | https://wiki.archlinux.org/title/Reproducible_builds                      | `SOURCE_DATE_EPOCH`, deterministic outputs             |
| Reproducible Builds/Status | https://wiki.archlinux.org/title/Reproducible_builds/Status               | Tracking reproducibility across official packages      |
| Rebuilderd                 | https://wiki.archlinux.org/title/Rebuilderd                               | Automated reproducibility verification infrastructure  |

## AUR Interaction

Consult these when publishing to or syncing from the AUR.

| Article                   | URL                                                        | Relevant To                                                 |
| ------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------- |
| Arch User Repository      | https://wiki.archlinux.org/title/Arch_User_Repository      | AUR structure, voting, comments, package lifecycle          |
| AUR submission guidelines | https://wiki.archlinux.org/title/AUR_submission_guidelines | New package requirements, naming, quality standards         |
| Aurweb RPC interface      | https://wiki.archlinux.org/title/Aurweb_RPC_interface      | Programmatic AUR queries, version checks, `sync-package.sh` |

## Repository Management

Consult these when managing the custom binary repository.

| Article                      | URL                                                           | Relevant To                                          |
| ---------------------------- | ------------------------------------------------------------- | ---------------------------------------------------- |
| Unofficial user repositories | https://wiki.archlinux.org/title/Unofficial_user_repositories | Custom repo structure, `repo-add`, database signing  |
| Package proxy cache          | https://wiki.archlinux.org/title/Package_proxy_cache          | Local caching of upstream packages for chroot builds |

## Foundational Concepts

| Article           | URL                                                | Relevant To                                                                          |
| ----------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Arch build system | https://wiki.archlinux.org/title/Arch_build_system | ABS overview, SVN-to-Git migration context (note: `asp` is deprecated; use `pkgctl`) |

---

**Source**: Articles sourced from
[Category:Package development](https://wiki.archlinux.org/title/Category:Package_development)
and
[Category:Package management](https://wiki.archlinux.org/title/Category:Package_management).
Curated for relevance to this repository's packaging workflow.
