#!/bin/bash
set -e
LATEST_VER=$1

# Demote original AUR maintainers to Contributors (skip line 1)
sed -i '2,$ s/^# Maintainer:/# Contributor:/g' PKGBUILD

# Use explicit build flags for clarity per Arch guidelines
sed -i 's/python -m build -nw/python -m build --wheel --no-isolation/' PKGBUILD
