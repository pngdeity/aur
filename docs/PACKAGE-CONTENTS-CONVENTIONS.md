# Package Contents Conventions

What a consumer of one of this repository's packages receives **besides the
software itself**: the optional companion files a PKGBUILD may ship, where each
one lands on the installed system, and when each is warranted.

A package is not only a binary. Three classes of companion content can travel
with it, and they take three different routes to the filesystem — two of them
through makepkg directives that place the file for you, one through explicit
installs in `package()`. This document separates the three so that a maintainer
can tell which mechanism applies before writing anything.

## Source Authority

Per the repository's [source authority hierarchy](../AGENTS.md#source-authority-hierarchy),
sources are ranked, and where two disagree the higher rank governs and the
discrepancy is reported rather than silently resolved. This document draws on:

| Rank | Source | What it settles here |
| --- | --- | --- |
| **1** | `PKGBUILD(5)` (`man 5 PKGBUILD`) | The `install=`, `changelog=`, and `backup=` directives: their syntax, where the file must live, and whether it belongs in `source=()`. |
| **1** | `makepkg(8)` (`man 8 makepkg`) | The build/packaging model. **It defines nothing about companion-file paths** — see the gap noted below. |
| **2** | Upstream project documentation | Which companion files an upstream project actually ships and whether they are worth repackaging. |
| **3** | Official Arch GitLab PKGBUILDs | Distro-wide practice for where these files are installed. |
| **4** | Observable build behavior | Where the files actually land in the built package — verified here by building and listing the archive. |
| **5** | Repo conventions (`AGENTS.md`, this file) | Which of the permitted options this repository exercises, and its preferred install paths. |

### Tier conflict: the install paths are convention, not law

**`PKGBUILD(5)` and `makepkg(8)` say nothing about `usr/share/licenses` or
`usr/share/doc`.** They define the *directives* that hand a file to makepkg
(`install=`, `changelog=`) but no per-path rule for the files a `package()`
function copies itself. The paths this repository uses are therefore **tier 3
(distro practice)** and **tier 5 (repo convention)** in force, not tier 1
requirements — a PKGBUILD that installs a licence elsewhere is not violating a
man page. This document states the convention so that a deviation is a visible
choice rather than an accident.

The one place the hierarchy *does* bind is the two directives below: `PKGBUILD(5)`
is explicit that neither file belongs in `source=()`, and that is a tier-1
requirement.

## 1. Files makepkg places for you

Two directives name a file that sits **beside the PKGBUILD** and is copied into
the package by makepkg. Neither is installed under `usr/`; each becomes an
archive member at the package's root.

### `changelog=`

> Specifies a changelog file that is to be included in the package. The
> changelog file should end in a single newline. This file should reside in the
> same directory as the PKGBUILD and will be copied into the package by makepkg.
> It does not need to be included in the source array (e.g.,
> `changelog=$pkgname.changelog`).
> — `PKGBUILD(5)`, tier 1

Declare it when upstream publishes meaningful release notes and the packaged
version's history is worth having on the installed system without a network
fetch. The file must end in **a single newline** (tier 1); a missing trailing
newline is a defect makepkg will not fix for you.

**Where it lands:** the archive's `.CHANGELOG` member, not `usr/share/doc`.
Verified (tier 4) by building `packages/clash-geoip` and listing the archive:
`.BUILDINFO  .CHANGELOG  .MTREE  .PKGINFO  etc/clash/Country.mmdb`.

**Repo practice (tier 5):** three packages declare it — `apm`, `go-regal-bin`,
`clash-geoip`. The sync pipeline generates the file for packages that track an
upstream changelog, so the declaration and the file travel together.

### `install=`

> Specifies a special install script that is to be included in the package.
> This file should reside in the same directory as the PKGBUILD and will be
> copied into the package by makepkg. It does not need to be included in the
> source array (e.g., `install=$pkgname.install`).
> — `PKGBUILD(5)`, tier 1

An install script — called a **scriptlet** — runs on the *installing* system at
`pre_install`, `post_install`, `pre_upgrade`, `post_upgrade`, `pre_remove`, and
`post_remove`. Reach for it only when a package must act on the host beyond
laying down files: creating users, migrating state between versions, or
rebuilding a cache the software cannot rebuild itself. A template with every
available function defined is available at `/usr/share/pacman/proto.install`
(tier 1).

Two cautions that follow from what a scriptlet is:

- It runs as root, on a machine you do not control. Keep it minimal, make it
  idempotent, and never assume a companion tool is present.
- Anything it does cannot be undone by removing the package unless
  `pre_remove`/`post_remove` reverses it. This is why the repository treats a
  scriptlet as a review flag: the CI policy engine **warns** on any package
  carrying one and requires that it be checked by hand for privilege escalation.

**Where it lands:** the archive's `.INSTALL` member. Verified (tier 4) by
building `packages/opendoas` and listing the archive:
`.BUILDINFO  .INSTALL  .MTREE  .PKGINFO  usr/  usr/bin/ …`.

**Repo practice (tier 5):** exactly one package uses it, `opendoas`. It is a
setuid-capable privilege tool, which is precisely the case where a scriptlet is
warranted and where it must be audited.

## 2. `backup=` — declaring mutable files

> An array of file names, without preceding slashes, that should be backed up if
> the package is removed or upgraded. This is commonly used for packages placing
> configuration files in `/etc`. See "Handling Config Files" in `pacman(8)` for
> more information.
> — `PKGBUILD(5)`, tier 1

`backup=` does not add a file to the package — the `package()` function still
has to install it. It tells pacman that the named paths are **user-owned
configuration**: on upgrade, a locally modified file is preserved and the new
version written alongside as `.pacnew`, and on removal the file is kept as
`.pacsave`. See `pacman(8)`, "Handling Config Files" (tier 1).

Declare it for **every** file the package installs under `/etc` that a user is
expected to edit, and only for those. Names are written without a leading slash
(`backup=('etc/foo.conf')`). Declaring it for a file the software rewrites
itself is a bug: pacman will start preserving generated state as if it were
config.

**Repo practice (tier 5):** exactly one package declares it, `seiche`.

## 3. Files installed by `package()`

Everything else a maintainer chooses to ship is copied into `$pkgdir` by
`package()`. The two recurring classes are licences and documentation.

### `usr/share/licenses/<pkgname>/`

Install the licence text here when the software's own license **requires the
text to accompany distribution**, or when upstream ships a licence file that
would otherwise be lost. `PKGBUILD(5)` defines the `license=` array but no
install path for its text; the `usr/share/licenses/<pkgname>/` location is
distro convention (tier 3), and the repository follows it consistently.

**Repo practice (tier 5):** every package ships its licence this way, e.g.
`install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"`. When the
licence has to be fetched rather than coming with the sources, the repository
declares it as a `source=("LICENSE.txt::https://…")` entry with a checksum so
the payload is pinned and reproducible.

### `usr/share/doc/<pkgname>/`

Install upstream's README, CHANGELOG, or similar prose here when it is genuinely
useful offline and upstream has already published it. This is pure convention
(tier 3/5) — nothing requires it.

Two judgement calls worth making explicitly:

- **Do not duplicate the `changelog=` member.** A file installed under
  `usr/share/doc/<pkgname>/CHANGELOG.md` and a `changelog=` file are two copies
  of the same history. Prefer the directive when the file is a *release
  changelog*; use `usr/share/doc` when the prose is *not* a changelog, or when a
  single package ships several documents and organising them together is
  clearer.
- **Prefer not to install a COPYING that duplicates the licence already in
  `usr/share/licenses/`.** One licence copy is enough.

**Repo practice (tier 5):** the convention is young in this repository. Three
packages install documentation this way — `fantomas-bin` (CHANGELOG.md,
README.md), `fsautocomplete` (README.md, CHANGELOG.md), and `seiche`
(README.md). All three pair it with a licence under `usr/share/licenses/`, which
is the intended shape.

## Quick Reference

| What you want to ship | How it is declared | Where it lands | Tier of the path rule |
| --- | --- | --- | --- |
| Release changelog | `changelog=$pkgname.changelog`, file beside the PKGBUILD, **not** in `source=()` | archive member `.CHANGELOG` | 1 (mechanism) |
| Install scriptlet | `install=$pkgname.install`, file beside the PKGBUILD, **not** in `source=()` | archive member `.INSTALL` | 1 (mechanism) |
| Mutable config | `backup=('etc/foo.conf')` **plus** an install in `package()` | as installed; pacman preserves it as `.pacnew`/`.pacsave` | 1 (mechanism) |
| Licence text | `package()` install | `usr/share/licenses/<pkgname>/` | 3/5 (convention) |
| README / docs | `package()` install, from a `source=()` entry | `usr/share/doc/<pkgname>/` | 3/5 (convention) |

The two directives in the middle rows and the top row take the file from beside
the PKGBUILD. Everything in the bottom two rows must be declared as a real
source — under `source=()` with a checksum if it is fetched, or as a plain local
file if it is written by hand — because `package()` reads it out of `$srcdir`.

## Verifying What a Package Actually Ships

The archive listing is the authority (tier 4). Build and list:

```
makepkg -f --noconfirm --nodeps
tar --zstd -tf ./"$pkgname-$pkgver-$pkgrel-$CARCH.pkg.tar.zst"
```

Pass `--zstd -tf` a `./`-prefixed filename: without it tar can read the `:` in a
versioned filename as a remote host. `.CHANGELOG` and `.INSTALL` appear at the
archive root, above `usr/`; companion files placed by `package()` appear under
`usr/share/`. `.PKGINFO` carries no line for either directive, so the listing is
how you confirm they were picked up.

## See Also

- [PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md](PKGBUILD-CUSTOM-VARIABLES-REFERENCE.md)
  — the repository-specific `_`-prefixed variables these directives sit beside.
- [SRCINFO-VERSION-CONTROL-POLICY.md](SRCINFO-VERSION-CONTROL-POLICY.md) — why
  `.SRCINFO` is generated rather than tracked.
- `man 5 PKGBUILD`, `man 8 makepkg`, `man 8 pacman` — tier 1.
- [../AGENTS.md](../AGENTS.md) — tier 5: the source authority hierarchy, the
  mandatory verification workflow, and the package-local `AGENTS.md` exception
  mechanism.
