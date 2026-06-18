from __future__ import annotations

_CHECKSUM_KEYS = ("sha256sums", "sha512sums", "sha224sums", "sha384sums", "b2sums")

_SKIP_CUSTOM_KEYS = {"_prereview", "_pkgver_func_body"}


def render_pkgbuild(vars_: dict, funcs: dict) -> str:
    lines: list[str] = []

    # Maintainer / Contributors
    maint = vars_.get("maintainer", "")
    if maint:
        lines.append(f"# Maintainer: {maint}")
    for c in vars_.get("contributor", []) or []:
        lines.append(f"# Contributor: {c}")
    if lines:
        lines.append("")

    # Custom variables — data-driven: emit all _-prefixed keys except internals
    custom_keys = sorted(
        k for k in vars_ if k.startswith("_") and k not in _SKIP_CUSTOM_KEYS
    )
    for key in custom_keys:
        val = vars_[key]
        if val is None or val is False or val == "":
            continue
        if isinstance(val, bool):
            lines.append(f"{key}=true")
        else:
            lines.append(f'{key}="{val}"')

    # PREREVIEW marker
    prereview = vars_.get("_prereview")
    if prereview:
        lines.append(f"# PREREVIEW: {prereview}")
        lines.append(
            "# Review the diff, verify build, then remove this marker to unblock release."
        )

    # Identity & versioning
    for key in ("pkgname", "pkgver"):
        if vars_.get(key):
            lines.append(f"{key}={vars_[key]}")
    lines.append(f"pkgrel={vars_.get('pkgrel', 1)}")
    if vars_.get("epoch") is not None:
        lines.append(f"epoch={vars_['epoch']}")
    if vars_.get("pkgdesc"):
        lines.append(f"pkgdesc={_q(vars_['pkgdesc'])}")

    # Metadata
    if vars_.get("arch"):
        lines.append(f"arch=({' '.join(_q(a) for a in vars_['arch'])})")
    if vars_.get("url"):
        lines.append(f"url='{vars_['url']}'")
    if vars_.get("license"):
        lines.append(f"license=({' '.join(_q(l) for l in vars_['license'])})")
    if vars_.get("groups"):
        lines.append(f"groups=({' '.join(_q(g) for g in vars_['groups'])})")

    # Dependencies
    for key in ("depends", "makedepends", "checkdepends"):
        val = vars_.get(key)
        if val:
            lines.append(f"{key}=({' '.join(_q(d) for d in val)})")

    # Optdepends
    opt = vars_.get("optdepends")
    if opt:
        items = []
        for o in opt:
            name = o.get("name", "")
            desc = o.get("desc", "")
            items.append(_q(f"{name}: {desc}" if desc else name))
        lines.append(f"optdepends=({' '.join(items)})")

    # Provides/Conflicts/Replaces
    for key in ("provides", "conflicts", "replaces"):
        val = vars_.get(key)
        if val:
            lines.append(f"{key}=({' '.join(_q(v) for v in val)})")

    # Config
    if vars_.get("backup"):
        lines.append(f"backup=({' '.join(_q(b) for b in vars_['backup'])})")
    if vars_.get("install"):
        lines.append(f"install={vars_['install']}")
    if vars_.get("options"):
        lines.append(f"options=({' '.join(_q(o) for o in vars_['options'])})")
    if vars_.get("changelog"):
        lines.append(f"changelog={vars_['changelog']}")

    # Source
    sources = vars_.get("source")
    if sources:
        items = []
        for s in sources:
            filename = s.get("filename", "")
            url = s.get("url", "")
            if filename and filename != url:
                items.append(f'"{filename}::{url}"')
            else:
                items.append(f'"{url}"')
        lines.append(f"source=({' '.join(items)})")

    # Checksums — use first available
    checksum_key = None
    for key in _CHECKSUM_KEYS:
        if key in vars_:
            checksum_key = key
            break
    if checksum_key and vars_.get(checksum_key):
        items = []
        for c in vars_[checksum_key]:
            items.append(f"'{c}'")
        lines.append(f"{checksum_key}=({' '.join(items)})")

    # validpgpkeys, noextract
    for key in ("validpgpkeys", "noextract"):
        val = vars_.get(key)
        if val:
            lines.append(f"{key}=({' '.join(_q(v) for v in val)})")

    # Lifecycle functions
    func_order = [
        ("pkgver", "pkgver"),
        ("prepare", "prepare"),
        ("build", "build"),
        ("check", "check"),
        ("package", "package"),
    ]
    for func_key, func_name in func_order:
        body = funcs.get(func_key)
        if body:
            lines.append("")
            lines.append(f"{func_name}() {{")
            for bline in body.strip().split("\n"):
                lines.append(f"    {bline}")
            lines.append("}")

    return "\n".join(lines) + "\n"


def _q(s: str) -> str:
    if not s:
        return "''"
    if " " not in s and "'" not in s and '"' not in s:
        return s
    return f"'{s}'"
