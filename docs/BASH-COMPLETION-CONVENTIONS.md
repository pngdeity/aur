# Bash Completion Conventions

This document defines the shared standards for bash-completion packages in this repository. All completion scripts installed to `/usr/share/bash-completion/completions/` must follow these conventions.

**Applicable packages:**
- `doas-bash-completion` — bash completion for opendoas
- `gemini-bash-completion` — bash completion for gemini-cli

## 1. Namespace Convention

All functions and variables in completion scripts must use the `_comp_` prefix. This is required by bash-completion 2.16+ to avoid collisions with other loaded completions and user-defined functions.

The main completion function follows the pattern:

```
_comp_cmd_<command>
```

**Examples:**

| Command | Completion function |
|---------|-------------------|
| `doas`   | `_comp_cmd_doas`   |
| `gemini` | `_comp_cmd_gemini` |

Any helper functions or variables within the completion script must also use the `_comp_` prefix (e.g., `_comp_doas_options`, `_comp_gemini_subcommands`).

**Enforcement:** Completion scripts that do not use the `_comp_` namespace will be rejected. Generic names like `_doas` or `_gemini_completion` violate the bash-completion 2.16+ standard.

## 2. Dynamic Option Parsing (`_comp_compgen_help`)

Use `_comp_compgen_help` to parse options and subcommands dynamically from the target binary's `--help` output at runtime. This avoids hardcoding option lists that drift from the upstream CLI.

**Pattern:**

```bash
_comp_compgen_help -- <binary> <subcommand>
```

**Examples:**
- `_comp_compgen_help -- doas` — extracts options from `doas --help`
- `_comp_compgen_help -- gemini` — extracts global options from `gemini --help`
- `_comp_compgen_help -- gemini <subcommand>` — extracts subcommand-specific options

**Rationale:** bash-completion 2.16+ provides `_comp_compgen_help` as a built-in helper. It parses `--help` output (or man pages) and generates completion candidates automatically, eliminating manual maintenance of option lists across upstream releases.

## 3. Installation Path

Completion scripts must be installed to:

```
/usr/share/bash-completion/completions/<command>
```

The file name must match the command name exactly (no `.bash` suffix in the installed path).

**PKGBUILD example:**

```bash
package() {
  install -Dm644 "${pkgname%-bash-completion}.bash" \
    "$pkgdir/usr/share/bash-completion/completions/${pkgname%-bash-completion}"
}
```

or equivalently with explicit naming:

```bash
package() {
  install -Dm644 "doas.bash" \
    "$pkgdir/usr/share/bash-completion/completions/doas"
}
```

**Permissions:** Completion scripts are data files, not executables. Always use `0644` (`-Dm644`).

## 4. Dependency

All bash-completion packages must declare:

```bash
depends=('bash-completion')
```

The `bash-completion` package provides the framework at `/usr/share/bash-completion/bash_completion` and the `_comp_compgen_help` helper.

## 5. Automation (update.sh)

If the completion script uses dynamic subcommand discovery (e.g., extracting subcommands from the target binary at build time), logic must be placed in the package-local `update.sh` script. This ensures the completion data stays current without embedding fragile command lists in the PKGBUILD.

**Example** (`gemini-bash-completion`): The `update.sh` script uses `npx` to dynamically extract subcommands from the latest `gemini-cli` binary.

Keep `update.sh` logic isolated to completion data generation tasks. Do not mix metadata manipulation (version bumps, hash updates) into `update.sh` — those are handled by `scripts/sync-package.sh`.

## 6. Naming Convention for Packages

Package names follow the pattern:

```
<command>-bash-completion
```

**Examples:**
- `doas-bash-completion`
- `gemini-bash-completion`

The source file uses a `.bash` extension (e.g., `doas.bash`, `gemini.bash`). The installed file drops the extension and matches the command name.

## 7. Verification Checklist

Before finalizing a bash-completion package, verify:

1. All functions and variables use the `_comp_` prefix
2. `_comp_compgen_help` is used for dynamic option parsing (not hardcoded lists)
3. The file installs to `/usr/share/bash-completion/completions/<command>` with `0644` permissions
4. `depends=('bash-completion')` is declared
5. `update.sh` (if present) is idempotent and isolated to completion data generation
6. `namcap PKGBUILD` produces no errors
