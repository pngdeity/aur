#!/bin/bash
set -e
LATEST_VER=$1
sed -i '2,$ s/^# Maintainer:/# Contributor:/g' PKGBUILD
