# BASH completion for gemini CLI

_gemini() {
    local cur prev words cword
    _init_completion || return

    local commands="mcp extensions skills hooks"
    local opts="-d --debug -m --model -p --prompt -i --prompt-interactive"
    opts+=" -w --worktree -s --sandbox -y --yolo --approval-mode --policy"
    opts+=" --admin-policy --acp --experimental-acp"
    opts+=" --allowed-mcp-server-names --allowed-tools -e --extensions"
    opts+=" -l --list-extensions -r --resume --list-sessions"
    opts+=" --delete-session --include-directories --screen-reader"
    opts+=" -o --output-format --raw-output --accept-raw-output-risk"
    opts+=" -v --version -h --help"

    case $prev in
        -m | --model)
            # Future possibility: dynamic completion for models
            # COMPREPLY=( $(compgen -W "..." -- "$cur") )
            return
            ;;
        --approval-mode)
            COMPREPLY=($(compgen -W "default auto_edit yolo plan" -- "$cur"))
            return
            ;;
        -o | --output-format)
            COMPREPLY=($(compgen -W "text json stream-json" -- "$cur"))
            return
            ;;
        -r | --resume | --delete-session)
            # Future possibility: dynamic completion for sessions
            # (e.g., using gemini --list-sessions)
            return
            ;;
        -e | --extensions | --allowed-mcp-server-names | \
            --allowed-tools | --policy | --admin-policy | \
            --include-directories)
            # These are usually files/directories or comma-separated lists
            _filedir
            return
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "$opts" -- "$cur"))
        return
    fi

    local i cmd
    for ((i = 1; i < cword; i++)); do
        if [[ ${words[i]} != -* ]]; then
            cmd=${words[i]}
            break
        fi
    done

    case "$cmd" in
        mcp)
            local subcmds="add remove list enable disable"
            case $prev in
                add | remove | enable | disable)
                    # Future possibility: dynamic completion for mcp server
                    # names (e.g., using gemini mcp list)
                    return
                    ;;
            esac
            COMPREPLY=($(compgen -W "$subcmds" -- "$cur"))
            ;;
        extensions | extension)
            local subcmds="install uninstall list update disable enable"
            subcmds+=" link new validate config"
            case $prev in
                uninstall | update | disable | enable | config)
                    # Future possibility: dynamic completion for extension
                    # names (e.g., using gemini extensions list)
                    return
                    ;;
                install | link | new | validate)
                    _filedir
                    return
                    ;;
            esac
            COMPREPLY=($(compgen -W "$subcmds" -- "$cur"))
            ;;
        skills | skill)
            local subcmds="list enable disable install link uninstall"
            case $prev in
                enable | disable | uninstall)
                    # Future possibility: dynamic completion for skill names
                    # (e.g., using gemini skills list)
                    return
                    ;;
                install | link)
                    _filedir
                    return
                    ;;
            esac
            COMPREPLY=($(compgen -W "$subcmds" -- "$cur"))
            ;;
        hooks | hook)
            local subcmds="migrate"
            COMPREPLY=($(compgen -W "$subcmds" -- "$cur"))
            ;;
        *)
            COMPREPLY=($(compgen -W "$commands" -- "$cur"))
            ;;
    esac
} &&
    complete -F _gemini gemini

# ex: ts=4 sw=4 et filetype=sh
