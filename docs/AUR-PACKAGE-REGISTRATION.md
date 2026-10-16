# AUR Package Registration

How an AUR entry comes into existence, and the order of operations that
`_deploy_aur=true` presumes. This is the procedure that `scripts/aur-deploy.sh`
enforces at runtime but cannot perform: it fails when the remote is absent, and
never creates one.

## When this applies

Register an AUR entry **before** setting `_deploy_aur=true` on a package. The
flag asserts *current maintainership*, and maintainership cannot exist for a
pkgbase that was never created. The two steps are ordered, not simultaneous:
registration is a human act performed with the maintainer's own SSH credentials,
and the flag is a repository declaration that the act has already happened.

The failure mode of getting this backwards is defined in
[`docs/TODO.md`](TODO.md) (the `go-bifrost` rename note): a package carrying
`_deploy_aur=true` for a pkgbase absent from the AUR. `aur-deploy.sh` catches it
and exits 1 rather than pushing anywhere, so nothing is lost — but the flag is
false for as long as the entry is missing.

Registration is needed in three situations:

- A package that has never existed on the AUR (`bws`, `seiche`).
- A rename: the new pkgbase is a new entry even though the software is not new.
- Reclaiming a pkgbase that was **deleted** rather than disowned — see the
  empty-clone caveat below, which differs.

It is **not** needed for a package mirrored from an AUR PKGBUILD
(`_upstream_aur_pkg`) that someone else still maintains. Those packages never
carry `_deploy_aur` — see [../AGENTS.md](../AGENTS.md) §"AUR Deployment Gate".

## Source authority

The procedure below is tier 7 (advisory) in the project's
[source authority hierarchy](../AGENTS.md#source-authority-hierarchy). It
restates the Arch Wiki's *AUR submission guidelines*, which is the authoritative
source for the act itself, and adds the repository-local facts (tier 5) that
determine what this pipeline does with the result. Where the two disagree, the
wiki governs the AUR-side mechanics and [`../AGENTS.md`](../AGENTS.md) governs
this repository's conventions.

| Tier | Source | What it settles |
| --- | --- | --- |
| 7 | [AUR submission guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines) | Authentication, the registration command, what a push must contain, submission rules, requests |
| 7 | [Arch User Repository](https://wiki.archlinux.org/title/Arch_User_Repository) | Package lifecycle, what the AUR is and is not |
| 7 | [Aurweb RPC interface](https://wiki.archlinux.org/title/Aurweb_RPC_interface) | Verifying ownership and existence programmatically |
| 1 | `man 5 PKGBUILD`, `man 8 makepkg` | PKGBUILD directives, `makepkg --printsrcinfo` |
| 5 | [`../AGENTS.md`](../AGENTS.md) §"AUR Deployment Gate" | `_deploy_aur` semantics, mutual exclusion with `_repo_subarch` |
| 5 | `docs/TODO.md` | The recorded `go-bifrost` rename case |
| 5 | `.agents/skills/pkg-bootstrap/SKILL.md` | The new-package workflow this fits into |
| 4 | `scripts/aur-deploy.sh` | What the pipeline actually does with the entry once it exists |

## Step 1 — Authentication

The AUR authenticates over SSH with a key pair. The **public** half is pasted
into *My Account* on `aur.archlinux.org`; the **private** half stays local and is
selected for the `aur.archlinux.org` host.

The wiki advises a dedicated key rather than reusing one already in service
elsewhere:

```bash
ssh-keygen -f ~/.ssh/aur
```

and a host stanza in `~/.ssh/config`:

```
Host aur.archlinux.org
  IdentityFile ~/.ssh/aur
  User aur
```

Multiple public keys may be registered, newline-separated, so a key rotation is
add-new-then-remove-old rather than a gap in access.

Verify the account is usable before trying to create anything:

```bash
ssh -T aur@aur.archlinux.org help
```

An authenticated connection returns the available commands. This is the same
probe `scripts/aur-deploy.sh` runs before it clones, with
`-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10` for
non-interactive use.

### Repository license

The wiki asks for a `LICENSE` file and/or `REUSE.toml` **in the AUR repository
itself**, 0BSD recommended. This licenses the packaging files, not the software
they build, and is separate from the `license=` variable. Its absence does not
block a push, but it makes the package ineligible for promotion to the official
repositories (RFC 0040). The repo's packages overwhelmingly declare `license=`
and ship the upstream licence into `/usr/share/licenses/`; only some also carry a
repository `LICENSE`, so this is a per-package judgement rather than an
established convention here.

## Step 2 — Create the entry (the registration act)

Cloning a nonexistent pkgbase is what creates it:

```bash
git -c init.defaultBranch=master clone ssh://aur@aur.archlinux.org/<pkgbase>.git
```

The expected output is:

```
warning: You appear to have cloned an empty repository.
```

**That warning is the success signal, not an error.** A brand-new AUR entry is a
zero-commit repository, so git says so on the way in.

### The one ambiguity to resolve before pushing

If the clone **succeeds and contains history**, the pkgbase is not new: it
matches a package that was submitted and later **deleted**. The wiki's rule for
that case is to pull and base your work on what is there rather than force a
push over it — the deletion request is a separate act from the entry reclaiming
its name.

The two cases are distinguishable from the clone result alone. An empty clone is
a fresh entry; a populated clone is a reclaim, and the disposition (adopt the
history, or request a merge/deletion first) is the maintainer's decision, not
something to infer.

## Step 3 — Populate and push

A push is accepted only if it carries at least `PKGBUILD` **and** `.SRCINFO`.

```bash
cd <pkgbase>
# copy in PKGBUILD, and any repo-local sources the AUR copy needs
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD .SRCINFO
git commit -m "Initial upload"
git push
```

- `.SRCINFO` is generated, never hand-edited, and must be regenerated whenever
  metadata changes. A push whose `.SRCINFO` is stale is rejected; if it was
  missing from the last commit, `git commit --amend` to add it.
- **Only the `master` branch is accepted.** A local branch with another name must
  be renamed (`git branch -m master`) or pushed explicitly to it.
- Commits are attributed to the repository's global `git config user.name` and
  `user.email`, and are very hard to change afterwards (FS#45425). Set them
  per-package if a different identity is wanted.
- Do not bump `pkgver`/`pkgrel` for cosmetic PKGBUILD edits, and never commit a
  bare version bump for a VCS (`-git`) package — that is what `-git` is for.

### Relationship to this repository's pipeline

In this repository the AUR repository is **not** a development worktree. The
package is developed in `packages/`, and `scripts/aur-deploy.sh` performs the
first and all subsequent pushes by:

1. probing SSH connectivity, then
2. `git -c init.defaultBranch=master clone ssh://aur@aur.archlinux.org/<pkgname>.git`
   into a temporary clone, and
3. copying the processed `PKGBUILD` and a freshly generated `.SRCINFO` in, then
   pushing.

So the manual `git clone` above is needed exactly once per pkgbase, to create it.
After that the entry is CI's to push to, and re-running the manual procedure
would only duplicate work. The script's clone failure path is the enforcement of
step 2:

```
::error::AUR repository for <pkgname> does not exist.
::error::Register it first: git -c init.defaultBranch=master clone ssh://aur@aur.archlinux.org/<pkgname>.git
```

## Step 4 — Verify, then set the flag

Registration completes when the entry is visible and owned. Verify against the
live API rather than assuming:

```bash
curl -fsSL 'https://aur.archlinux.org/rpc/v5/info?arg[]=<pkgbase>' \
  | jq -r '.results[] | "\(.Name) \(.Version) \(.Maintainer)"'
```

A registered-but-unowned pkgbase reports `Maintainer: null`; a pkgbase that does
not exist returns `resultcount: 0`. **Neither state justifies setting
`_deploy_aur=true`.** The flag requires the entry to exist *and* be yours, and
`scripts/check-deploy-aur-ownership.sh` (where it is wired in) fails closed on
both — an unreachable API and a non-owned maintainer both exit 1.

Only then add `_deploy_aur=true` to the PKGBUILD. Setting it earlier is how a
package ends up declaring maintainership it does not have.

## Requests

Deletion, merge, and orphan requests are made through *Submit Request* under
*Package Actions* on the package's AUR page. Orphaning is normally requested
after the package has been flagged out-of-date for two weeks, and is
auto-accepted after 180 days. These are maintainer acts performed in the web
interface; nothing in this repository automates them.

## See Also

- [`../AGENTS.md`](../AGENTS.md) — §"AUR Deployment Gate" (`_deploy_aur`
  semantics), §"Publishing Targets & Platform Responsibilities" (what the
  pipeline deploys), §"Source Authority Hierarchy".
- [`WIKI-REFERENCE.md`](WIKI-REFERENCE.md) — the catalog entry for the upstream
  page this procedure restates.
- [`TODO.md`](TODO.md) — the recorded `go-bifrost` rename case, and the
  withdrawn-maintainership audit.
- [`.agents/skills/pkg-bootstrap/SKILL.md`](../.agents/skills/pkg-bootstrap/SKILL.md)
  — the new-package workflow, whose `_deploy_aur` step depends on this one.
- [`SRCINFO-VERSION-CONTROL-POLICY.md`](SRCINFO-VERSION-CONTROL-POLICY.md) — why
  `.SRCINFO` is generated in this repository but committed on the AUR.
