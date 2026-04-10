# OpenDoas Patches

This directory contains several patches for the `opendoas` package to fix various issues or add features that have not yet been merged into the upstream repository.

## Applied Patches

- **119.patch**: Adds a `--default-path` option to the `configure` script to allow setting the default `PATH` at build time. [GitHub PR #119](https://github.com/Duncaen/OpenDoas/pull/119)
- **rowhammer.patch**: Implements rowhammer resistance in the password entry logic. [GitHub PR #124](https://github.com/Duncaen/OpenDoas/pull/124)
- **retry.patch**: Increases the number of allowed password retry attempts to 3. [GitHub PR #123](https://github.com/Duncaen/OpenDoas/pull/123)
- **post-release-v6.8.2.patch**: Includes various bug fixes and improvements committed to the repository after the 6.8.2 release.
- **Fix-typos-in-comments.patch**: Corrects minor spelling errors within the source code comments.
- **configure-Correct-value-assignment-to-GIDMAX.patch**: Fixes a bug in the `configure` script where `UID_MAX` was incorrectly assigned to `GID_MAX`. [GitHub Issue #129](https://github.com/Duncaen/OpenDoas/issues/129)

## Unused Patches

- **Add-bashcompletion-support.patch**: Adds support for Bash command-line completion for `doas`. (Currently not included in the PKGBUILD)
