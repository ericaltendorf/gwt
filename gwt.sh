#!/usr/bin/env bash

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/gwt.py"

_gwt_get_branches() {
    # Function to get list of branch names with worktrees
    # Only run if GWT_GIT_DIR is set and valid
    if [ -n "$GWT_GIT_DIR" ] && [ -d "$GWT_GIT_DIR" ]; then
        # Get branch names from worktree list
        git --git-dir="$GWT_GIT_DIR" worktree list 2>/dev/null | 
            awk '{print $3}' | 
            sed 's/\[//' | 
            sed 's/\]//' | 
            grep -v '(detached)' |
            grep -v 'HEAD'
    fi
}

_gwt_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="new repo switch s list ls l remove rm"
    
    # Don't use file completion as a fallback
    compopt -o nospace

    # For the first argument (position 1), complete with commands
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
        return 0
    fi

    # For position 2, handle specific subcommand completions
    if [[ ${COMP_CWORD} -eq 2 ]]; then
        case "${prev}" in
            new)
                # No specific completions for new since it expects a new branch name
                return 0
                ;;
            repo)
                # Use directory completion for repo command
                compopt -o filenames
                COMPREPLY=( $(compgen -d -- "${cur}") )
                return 0
                ;;
            switch|s|remove|rm)
                # Get branch names and provide them as completions
                local branches=$(_gwt_get_branches)
                if [ -n "$branches" ]; then
                    COMPREPLY=( $(compgen -W "${branches}" -- "${cur}") )
                fi
                return 0
                ;;
            list|ls|l)
                # No completions needed for list commands
                return 0
                ;;
            *)
                # No completions for unknown commands
                return 0
                ;;
        esac
    fi

    # Default: no completions for other positions
    return 0
}

# Function to handle all gwt operations
gwt() {
    # Run the Python script and capture output
    local output=$("$PYTHON_SCRIPT" "$@")
    
    # Parse the output for special commands
    if [[ "$output" == cd* ]]; then
        # Extract the directory path and change to it
        local dir="${output#cd }"
        cd "$dir" || echo "Failed to change directory to $dir"
    elif [[ "$output" == GWT_GIT_DIR=* ]]; then
        # Extract the git directory and set it
        local dir="${output#GWT_GIT_DIR=}"
        if [ -d "$dir" ]; then
            export GWT_GIT_DIR="$dir"
            echo "GWT_GIT_DIR set to $dir"
        else
            echo "Error: $dir is not a valid directory" >&2
            return 1
        fi
    else
        # Just print the output
        echo "$output"
    fi
}

# If this script is being sourced (not executed directly)
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # Set up the completion
    complete -F _gwt_completions gwt
else
    # If executed directly, just run the function with all arguments
    gwt "$@"
fi