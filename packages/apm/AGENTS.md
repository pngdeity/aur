# Specialized Mandates: apm

## 1. Upstream Source
- **GitHub**: https://github.com/microsoft/apm

## 2. Tribal Knowledge
- **Python Dependencies**: This package builds from source using standard `python-build` and `python-installer`. Several dependencies (e.g., `python-llm`, `python-llm-github-models`) may need to be resolved from the AUR as they are not in the official Arch repositories.
- **Build System**: Uses `setuptools.build_meta` as defined in the upstream `pyproject.toml`.
