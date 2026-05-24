# AGENTS.md: justfile for aur repository
# Run `just` or `just --list` to see available recipes.

set dotenv-load := false

# Remove all gitignored artifacts (pycache, generated files, logs, build artifacts)
clean:
    git clean -fdX

# Run full Pkl + OPA validation pipeline on all packages
validate:
    bash scripts/validate-pkgbuilds-pkl.sh
