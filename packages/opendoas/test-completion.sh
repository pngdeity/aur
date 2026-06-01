#!/bin/bash
set -eo pipefail

BC=/usr/share/bash-completion/bash_completion
if [[ ! -r $BC ]]; then
	echo "skip: bash-completion not installed"
	exit 0
fi
source "$BC"

if ! declare -F _comp_initialize >/dev/null; then
	echo "skip: bash-completion >= 2.12 required"
	exit 0
fi

COMPLETION_FILE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/doas.bash"
# shellcheck disable=SC1090
source "$COMPLETION_FILE"

PASS=0
FAIL=0

_run() {
	local line=$1
	COMP_LINE=$line
	# shellcheck disable=SC2206
	COMP_WORDS=($line)
	[[ $line == *" " ]] && COMP_WORDS+=("")
	COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
	COMP_POINT=${#COMP_LINE}
	COMPREPLY=()
	_comp_cmd_doas 2>/dev/null || true
}

case_nonempty() {
	local desc=$1 line=$2
	_run "$line"
	if [[ ${#COMPREPLY[@]} -gt 0 ]]; then
		PASS=$((PASS + 1))
		printf 'ok   %s\n' "$desc"
	else
		FAIL=$((FAIL + 1))
		printf 'FAIL %s\n     line: %q\n     got:  (empty)\n' \
			"$desc" "$line"
	fi
}

case_match() {
	local desc=$1 line=$2 pattern=$3
	_run "$line"
	if printf '%s\n' "${COMPREPLY[@]}" | grep -qE -e "$pattern"; then
		PASS=$((PASS + 1))
		printf 'ok   %s\n' "$desc"
	else
		FAIL=$((FAIL + 1))
		printf 'FAIL %s\n     line: %q\n     got:  %s\n     want match: %s\n' \
			"$desc" "$line" "${COMPREPLY[*]:-(empty)}" "$pattern"
	fi
}

case_not_match() {
	local desc=$1 line=$2 pattern=$3
	_run "$line"
	if ! printf '%s\n' "${COMPREPLY[@]}" | grep -qE -e "$pattern"; then
		PASS=$((PASS + 1))
		printf 'ok   %s\n' "$desc"
	else
		FAIL=$((FAIL + 1))
		printf 'FAIL %s\n     line: %q\n     got:  %s\n     want NOT: %s\n' \
			"$desc" "$line" "${COMPREPLY[*]:-(empty)}" "$pattern"
	fi
}

# Flag completion
case_match "flags offered at -" "doas -" '-L|-n|-s|-u|-C'
case_match "-C flag offered" "doas -" '-C'
case_match "-L flag offered" "doas -" '-L'
case_match "-n flag offered" "doas -" '-n'
case_match "-s flag offered" "doas -" '-s'

# Username completion for -u
case_match "-u completes users" "doas -u " '^root$'

# File completion for -C (any file, location-independent)
case_nonempty "-C completes files" "doas -C "

# Command offset (completes available commands after doas)
case_nonempty "command completion after doas" "doas l"

# P0: -L, -n, -s don't eat the next word — command completion still works
case_nonempty "-n doesn't eat next word" "doas -n l"

# After a command is identified, inner command gets its own completion
case_not_match "doas flags not offered after command" "doas ls -" '-L'

echo "---"
printf 'PASS: %d  FAIL: %d\n' "$PASS" "$FAIL"
exit $((FAIL > 0 ? 1 : 0))
