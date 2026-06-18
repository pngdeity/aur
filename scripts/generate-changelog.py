#!/usr/bin/env python3
"""Generate a changelog file from a GitHub release.

Fetches release notes via the GitHub API, formats @mentions into profile
links and PR references into clickable links, and writes the result.

Usage:
    python generate-changelog.py <owner/repo> <tag> <output_path> [api_version]

Exit codes:
    0 — changelog generated successfully
    1 — usage error or API failure
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error


def fetch_release_body(repo: str, tag: str, api_version: str, token: str | None) -> str:
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    headers = {
        "X-GitHub-Api-Version": api_version,
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("body", "No release notes available.")
    except urllib.error.HTTPError as e:
        print(f"ERROR: GitHub API returned {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach GitHub API: {e.reason}", file=sys.stderr)
        sys.exit(1)


def format_body(body: str) -> str:
    body = re.sub(
        r"@([a-zA-Z0-9-]+)",
        r"[@\1](https://github.com/\1)",
        body,
    )
    body = re.sub(
        r"https://github\.com/[^/\s]+/[^/\s]+/pull/([0-9]+)",
        r"[#\1](\g<0>)",
        body,
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a changelog from a GitHub release"
    )
    parser.add_argument("repo", help="GitHub owner/repo (e.g. microsoft/apm)")
    parser.add_argument("tag", help="Release tag (e.g. v1.2.3)")
    parser.add_argument("output", help="Path to write the changelog file")
    parser.add_argument(
        "api_version",
        nargs="?",
        default="2026-03-10",
        help="GitHub API version (default: 2026-03-10)",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    print(f"  -> Generating changelog for {args.tag}...")
    body = fetch_release_body(args.repo, args.tag, args.api_version, token)
    formatted = format_body(body)

    with open(args.output, "w") as f:
        f.write(formatted)


if __name__ == "__main__":
    main()
