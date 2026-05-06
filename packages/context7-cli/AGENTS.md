# AGENTS.md - context7-cli Package Mandates

This document defines package-specific mandates for `context7-cli`.

## 1. Upstream Source
- **NPM Registry**: `ctx7`
- **Source Code**: `https://github.com/upstash/context7`

## 2. Packaging Logic
- **Build System**: Node.js / NPM.
- **Guideline Compliance**: Follows [Arch Linux Node.js package guidelines](https://wiki.archlinux.org/title/Node.js_package_guidelines).
- **Installation Path**: System-wide under `/usr/lib/node_modules` with a symlink in `/usr/bin/ctx7`.

## 3. Maintenance Procedures
- **Version Tracking**: Automated via `nvchecker` tracking the `ctx7` npm package.
- **Changelog**: Automatically extracted from the `upstash/context7` GitHub releases using the `ctx7@$pkgver` tag pattern.
- **Verification**: Ensure the `ctx7` binary is correctly symlinked and functional after every update.

## 4. Tribal Knowledge
- The CLI is part of a monorepo; ensure `_githubname` and `_tag` in `PKGBUILD` are correctly set to point to the relevant release notes.
- NPM installation in a clean chroot requires `makedepends=('npm')`.
