#!/usr/bin/env bash
set -e

install_tools() {
	yay -S --noconfirm pkl-bin conftest
}

missing=()

if ! which pkl >/dev/null 2>&1; then
	missing+=("pkl")
fi

if ! which conftest >/dev/null 2>&1; then
	missing+=("conftest")
fi

if [[ ${#missing[@]} -gt 0 ]]; then
	echo "Missing tools: ${missing[*]}"
	echo "Attempting install via yay..."
	if ! install_tools; then
		echo "ERROR: Failed to install required tools" >&2
		exit 1
	fi
fi

if ! which pkl >/dev/null 2>&1 || ! which conftest >/dev/null 2>&1; then
	echo "ERROR: Required tools (pkl, conftest) not found on PATH" >&2
	exit 1
fi

pkl --version
conftest --version
exit 0
