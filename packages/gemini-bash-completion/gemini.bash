# BASH completion for gemini-cli (Standard 2.16+)

_comp_cmd_gemini() {
    local cur prev words cword split
    _comp_initialize -n : || return

    # Dynamic flag completion via --help parsing
    if [[ "$cur" == -* ]]; then
        _comp_compgen_help
        return
    fi

    # Subcommand list (Managed by update.sh)
    local commands="mcp extensions skills hooks"

    # Specific subcommand logic
    case "${words[1]}" in
        mcp)
            _comp_compgen -W "add remove list enable disable" -- "$cur"
            return ;;
        extensions|extension)
            _comp_compgen -W "install uninstall list update disable enable link new validate config" -- "$cur"
            return ;;
        skills|skill)
            _comp_compgen -W "list enable disable install link uninstall" -- "$cur"
            return ;;
        hooks|hook)
            _comp_compgen -W "migrate" -- "$cur"
            return ;;
    esac

    # Default to top-level commands
    _comp_compgen -W "$commands" -- "$cur"
}

complete -F _comp_cmd_gemini gemini
