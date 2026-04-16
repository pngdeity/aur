#!/bin/bash
set -e

# This script is called by scripts/sync-package.sh during the sync phase.
# It dynamically updates the gemini bash completion script by extracting
# the latest commands and flags from the gemini-cli.

LATEST_VER=$1

echo "Updating gemini-bash-completion for version $LATEST_VER..."

# 1. Extract Top-Level Subcommands
# Use npx to run the cli help without needing a local build environment.
# We parse the 'Commands:' section of the help output.
if command -v npx &>/dev/null; then
    echo "  -> Fetching latest commands from gemini-cli@$LATEST_VER"
    CMDS=$(npx -y @google/gemini-cli@"$LATEST_VER" --help 2>/dev/null | \
           sed -n '/Commands:/,/Options:/p' | \
           grep -oP '^\s+\K[a-z]+' | xargs || echo "mcp extensions skills hooks")
    
    if [[ -n "$CMDS" ]]; then
        echo "  -> Found commands: $CMDS"
        sed -i "s/local commands=\".*\"/local commands=\"$CMDS\"/" gemini.bash
    fi
else
    echo "  -> npx not found, skipping dynamic command extraction."
fi

# 2. Metadata Update (Handled by sync-package.sh)
# Note: Flags are handled dynamically at runtime via _comp_compgen_help
# in the gemini.bash script itself.
