# doas(1) completion (Standard 2.16+)

_comp_cmd_doas() {
    local cur prev words cword split
    _comp_initialize -n : || return

    # Skip options and identify the command offset
    local i
    for ((i = 1; i <= cword; i++)); do
        if [[ ${words[i]} != -* ]]; then
            # We found a command, offset to complete it
            _comp_command_offset "$i"
            return
        fi
        # Skip options that take an argument
        [[ ${words[i]} == -@(!(-*)[uCLs]) ]] && ((i++))
    done

    # Handle completion for doas-specific options
    case "$prev" in
        -!(-*)u)
            _comp_compgen -u -- "$cur"
            return ;;
        -!(-*)C)
            _filedir
            return ;;
        -!(-*)[Ls])
            return ;;
    esac

    # Dynamic flag completion via --help parsing
    if [[ "$cur" == -* ]]; then
        _comp_compgen_help
        return
    fi
}

complete -F _comp_cmd_doas doas
