#!/usr/bin/env bash

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/gwt.py"

_gwt_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-a --set-git-dir"

    # Handle options that take arguments
    if [[ ${prev} == "-a" ]]; then
        # No specific completions for -a since it expects a new branch name
        return 0
    elif [[ ${prev} == "--set-git-dir" ]]; then
        # Use directory completion for --set-git-dir
        COMPREPLY=( $(compgen -d -- "${cur}") )
        return 0
    fi

    # Complete -a if it's the current word
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
        return 0
    fi

    # If this is the first word (not an option), complete with branch names
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        # Get list of branches that have worktrees
        if [ -z "$GWT_GIT_DIR" ]; then
            return 0  # No completions if GWT_GIT_DIR not set
        fi
        local worktrees=$(git --git-dir="$GWT_GIT_DIR" worktree list | awk '{print $3}' | sed 's/\[//' | sed 's/\]//' | grep -v '(detached)')
        COMPREPLY=( $(compgen -W "${worktrees}" -- "${cur}") )
        return 0
    fi
}

# Function to handle all gwt operations
gwt() {
    # Check for setting GIT_DIR
    if [ "$1" = "--set-git-dir" ] && [ -n "$2" ]; then
        if [ -d "$2" ]; then
            export GWT_GIT_DIR="$2"
            echo "GWT_GIT_DIR set to $2"
            return 0
        else
            echo "Error: $2 is not a valid directory" >&2
            return 1
        fi
    fi
    
    # If no arguments or starts with -, execute Python script directly
    if [ $# -eq 0 ] || [ "${1:0:1}" = "-" ]; then
        "$PYTHON_SCRIPT" "$@"
    else
        # For branch switching, we need to parse the output ourselves
        local output=$("$PYTHON_SCRIPT" "$@")
        # Check if output starts with "cd "
        if [[ "$output" == cd* ]]; then
            # Extract the directory path and change to it
            local dir="${output#cd }"
            cd "$dir" || echo "Failed to change directory to $dir"
        else
            # Just print the output
            echo "$output"
        fi
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