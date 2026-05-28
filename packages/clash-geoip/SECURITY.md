# Security: Attestation Verification

## Overview

This package verifies the `Country.mmdb` file against a Sigstore in-toto release
attestation published by GitHub. The attestation proves the file was produced by
the `Loyalsoldier/geoip` release workflow at the claimed version.

Verification is implemented via the `verify()` function and runs automatically
when building with `makepkg`. Use `makepkg --noverify` to skip it.

## Trust Model

```
ca-certificates (Arch Linux, always present on every system)
  └── TLS connection to Sigstore TUF repository (gh attestation trusted-root)
       └── TUF signed metadata → trusted_root.json (Sigstore + GitHub private instance)
            └── Fulcio CA chains (with validFor time ranges)
                 └── Attestation signing certificate
                      └── DSSE envelope signature
                           └── Attested SHA256 hash of Country.mmdb
```

The trust anchor is **Arch Linux's `ca-certificates` package** — the same root
of trust that `pacman` uses to verify HTTPS connections for package downloads
from mirrors. `gh attestation trusted-root` fetches the trusted root material
via TUF (The Update Framework) — a signed, verifiable distribution — from
Sigstore's TUF repository. This includes both the public good instance trust
material and GitHub's private instance (`fulcio.githubapp.com`) trust material.

### Why TUF-Based Trust Material

TUF distributes the trust material through a signed metadata hierarchy. This is
superior to bundling CA certificates in `source[]` (circular trust: the bundled
material's authenticity is only as trustworthy as the PKGBUILD maintainer who
committed it) or fetching from a live HTTP endpoint (raw TLS, no cryptographic
integrity protection for the trust material itself). TUF provides both —
cryptographic signatures on the trust material AND out-of-band distribution.

## What Verification Catches

### Verified layers

| Layer             | Mechanism                                                        | Protects Against                          |
| ----------------- | ---------------------------------------------------------------- | ----------------------------------------- |
| File integrity    | `sha256sums[]` (makepkg built-in)                                | Corrupted download, accidental wrong file |
| Certificate chain | `cosign` + trusted root from `gh attestation trusted-root` (TUF) | Forged/malicious certificate authority    |
| Identity          | `--certificate-identity https://dotcom.releases.github.com`      | Attestation from non-GitHub source        |
| Signature         | `cosign` DSSE envelope verification                              | Tampered attestation payload              |
| Subject hash      | `cosign` artifact-vs-attestation match                           | Release contains wrong file               |

### What is NOT verified (acceptable limitations)

**RFC 3161 signed timestamp.** The trusted root obtained via
`gh attestation trusted-root` includes the TSA certificate chains for
`timestamp.githubapp.com`. Using `--use-signed-timestamps` to verify RFC 3161
timestamps against these chains could be explored as a future improvement. At
present, timestamp verification is skipped with `--insecure-ignore-sct`.

**Transparency log (Rekor).** GitHub Artifact Attestations use RFC 3161 signed
timestamps instead of the public Rekor transparency log. The
`--insecure-ignore-tlog` flag is semantically correct.

**SCT (Signed Certificate Timestamp).** GitHub's Fulcio CA does not embed SCTs
in its certificates. The `--insecure-ignore-sct` flag is semantically correct.

## Dependency Rationale

| Dependency                 | Role                  | Justification                                                                                                                                                                                                        |
| -------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cosign` (makedepends)     | Sigstore verification | Purpose-built tool for verifying in-toto attestations signed by Sigstore. In Arch extra repo.                                                                                                                        |
| `github-cli` (makedepends) | Trust root resolution | `gh attestation trusted-root` fetches the Sigstore and GitHub private instance trusted roots via TUF — a signed, verifiable distribution. In Arch extra repo. No GitHub authentication required for this subcommand. |
