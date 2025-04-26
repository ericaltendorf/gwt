#!/usr/bin/env bash

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/gwt.py"

_gwt_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="new repo"

    # Handle subcommands
    if [[ ${prev} == "new" ]]; then
        # No specific completions for new since it expects a new branch name
        return 0
    elif [[ ${prev} == "repo" ]]; then
        # Use directory completion for repo
        COMPREPLY=( $(compgen -d -- "${cur}") )
        return 0
    fi

    # Complete commands or branch names if it's the first word
    if [[ ${COMP_CWORD} -eq 1 ]]; then        
        # If GWT_GIT_DIR is not set, only complete commands
        if [ -z "$GWT_GIT_DIR" ]; then
            COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
            return 0
        fi
        
        # Get list of branches that have worktrees
        local worktrees=$(git --git-dir="$GWT_GIT_DIR" worktree list | awk '{print $3}' | sed 's/\[//' | sed 's/\]//' | grep -v '(detached)')
        COMPREPLY=( $(compgen -W "${commands} ${worktrees}" -- "${cur}") )
        return 0
    fi
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