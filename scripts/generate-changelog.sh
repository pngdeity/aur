#!/usr/bin/env bash
# scripts/generate-changelog.sh
# Centralized logic for fetching and formatting GitHub release notes.

set -euo pipefail

REPO=$1
TAG=$2
OUTPUT=$3
API_VER=${4:-"2026-03-10"}

echo "  -> Generating changelog for ${TAG}..."

# Fetch release body and format mentions/PRs
# Environment variable GITHUB_TOKEN should be provided by the caller.
curl -sH "X-GitHub-Api-Version: ${API_VER}" \
     -H "Authorization: token ${GITHUB_TOKEN:-}" \
    "https://api.github.com/repos/${REPO}/releases/tags/${TAG}" | \
    jq -r '.body // "No release notes available."' | \
    sed -E -e 's|@([a-zA-Z0-9-]+)|[@\1](https://github.com/\1)|g' \
           -e 's|https://github.com/[^/ ]+/[^/ ]+/pull/([0-9]+)|[#\1](&)|g' \
    > "${OUTPUT}"
