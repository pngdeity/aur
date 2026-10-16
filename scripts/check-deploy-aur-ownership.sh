#!/usr/bin/env bash
#
# check-deploy-aur-ownership.sh -- assert every _deploy_aur=true package is ours.
#
# The _deploy_aur flag asserts *current maintainership* of the AUR entry, not
# merely that the package could be published. aur-deploy.sh pushes over whatever
# occupies that AUR name, so a flag left on a package this repository does not
# own silently overwrites someone else's work.
#
# This check closes that gap mechanically: for each package declaring
# _deploy_aur=true it queries the live AUR API and requires Maintainer to be
# the owner below. Anything else -- a different maintainer, a disowned entry,
# an entry that does not exist, or an unreachable API -- fails.
#
# Run from the repository root. Exit 0 if every flagged package is owned.

set -euo pipefail

OWNER="pngdeity"
AUR_RPC="https://aur.archlinux.org/rpc/v5/info"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"

cd "$REPO_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
	echo "::error::python3 is required to parse the AUR RPC response."
	exit 1
fi

# Collect the flagged packages.
flagged=()
for pkgbuild in packages/*/PKGBUILD; do
	[[ -f "$pkgbuild" ]] || continue
	if grep -q '^_deploy_aur=true' "$pkgbuild"; then
		flagged+=("$(basename -- "$(dirname -- "$pkgbuild")")")
	fi
done

echo "==> Checking _deploy_aur ownership against the live AUR API"
echo "    owner: ${OWNER}"

if [[ ${#flagged[@]} -eq 0 ]]; then
	echo "  -> No package declares _deploy_aur=true. Nothing to check."
	exit 0
fi

echo "    flagged packages: ${flagged[*]}"
echo

# Build one query string for every flagged package in a single request.
query=""
for pkg in "${flagged[@]}"; do
	query+="&arg[]=${pkg}"
done

if ! response="$(curl -fsSL "${AUR_RPC}?${query#&}")"; then
	echo "::error::Could not reach the AUR API at ${AUR_RPC}."
	echo "::error::Refusing to pass: ownership cannot be verified."
	exit 1
fi

# Parse the response into "pkg<TAB>version<TAB>maintainer" rows. The parser
# lives in a file rather than an inline -c string so quoting stays readable and
# a parse failure cannot be mistaken for an empty result.
parser="$(mktemp)"
trap 'rm -f "$parser"' EXIT
cat >"$parser" <<'PY'
import json
import sys

owner = sys.argv[1]
flagged = sys.argv[2:]

data = json.load(sys.stdin)
results = {r["Name"]: r for r in data.get("results", [])}

missing = [p for p in flagged if p not in results]
if missing:
    print("MISSING\t\t" + " ".join(missing), file=sys.stderr)

for pkg in flagged:
    r = results.get(pkg)
    if r is None:
        print(f"{pkg}\t\t")
    else:
        print(f"{pkg}\t{r.get('Version', '')}\t{r.get('Maintainer') or ''}")
PY

if ! rows="$(printf '%s' "$response" | python3 "$parser" "$OWNER" "${flagged[@]}")"; then
	echo "::error::Could not parse the AUR API response."
	exit 1
fi

# A response naming no flagged package cannot be a pass: the parse failed.
if [[ -z "$rows" ]]; then
	echo "::error::The AUR API response yielded no rows for ${#flagged[@]} flagged package(s)."
	exit 1
fi

failed=0
rows_seen=0
while IFS=$'\t' read -r pkg version maintainer; do
	[[ -n "$pkg" ]] || continue
	rows_seen=$((rows_seen + 1))
	if [[ "$maintainer" == "$OWNER" ]]; then
		printf '  OK    %-24s %-18s %s\n' "$pkg" "${version:-absent}" "$maintainer"
	else
		printf '  FAIL  %-24s %-18s %s\n' "$pkg" "${version:-absent}" "${maintainer:-none}"
		failed=1
	fi
done <<<"$rows"

if [[ "$rows_seen" -ne ${#flagged[@]} ]]; then
	echo "::error::Expected ${#flagged[@]} row(s) from the parser, got ${rows_seen}."
	exit 1
fi

echo
if [[ "$failed" -ne 0 ]]; then
	echo "::error::A package declares _deploy_aur=true but is not owned by ${OWNER} on the AUR."
	echo "::error::Remove the flag, or establish maintainership before it is deployed over."
	exit 1
fi

echo "  -> All flagged packages are owned by ${OWNER}."
