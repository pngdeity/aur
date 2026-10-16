# doas(1) completion

_comp_cmd_doas() {
	local cur prev words cword split
	_comp_initialize -n : || return

	local i
	for ((i = 1; i <= cword; i++)); do
		if [[ ${words[i]} != -* ]]; then
			_comp_command_offset "$i"
			return
		fi
		[[ ${words[i]} == -[uC] ]] && ((i++))
	done

	case "$prev" in
	-u)
		COMPREPLY=($(compgen -u -- "$cur"))
		return
		;;
	-C)
		_filedir
		return
		;;
	esac

	if [[ "$cur" == -* ]]; then
		_comp_compgen -- -W '-C -L -n -s -u'
		return
	fi
}

complete -F _comp_cmd_doas doas
