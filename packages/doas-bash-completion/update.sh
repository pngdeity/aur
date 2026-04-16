#!/bin/bash
set -e

# This script is called by scripts/sync-package.sh during the sync phase.
# It maintains the doas completion script.

LATEST_VER=$1

echo "Updating doas-bash-completion for version $LATEST_VER..."

# Note: doas completion is relatively stable as it follows the standard
# command offset pattern. Flags are parsed dynamically at runtime via
# _comp_compgen_help in doas.bash.
# If opendoas adds complex subcommands in the future, they should be
# extracted here from the man page or help output.

echo "  -> doas-bash-completion is up to date (dynamic help parsing enabled)."
