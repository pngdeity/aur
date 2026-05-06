#!/bin/bash
set -e
LATEST_VER=$1

# Demote original AUR maintainers to Contributors (skip line 1)
sed -i '2,$ s/^# Maintainer:/# Contributor:/g' PKGBUILD

# Fix architecture for pure Python package
sed -i 's/arch=("x86_64")/arch=("any")/' PKGBUILD
