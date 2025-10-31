#!/usr/bin/env bash

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/gwt.py"

# Verify Python script exists and is executable
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found at $PYTHON_SCRIPT" >&2
    echo "This could happen if the script was moved or renamed." >&2
    echo "Verify that the script is installed correctly." >&2
    # shellcheck disable=SC2317
    return 1 2>/dev/null || exit 1
fi

if [ ! -x "$PYTHON_SCRIPT" ]; then
    echo "Warning: Python script is not executable. Fixing permissions..." >&2
    chmod +x "$PYTHON_SCRIPT"
fi

_gwt_get_branches() {
    # Function to get list of branch names
    # Default to "all" branches for comprehensive completion
    output=$("$PYTHON_SCRIPT" list --branches all 2>&1)
    result=$?
    
    if [ $result -eq 0 ]; then
        echo "$output"
    else
        # Fallback to worktrees only if all branches fails
        output=$("$PYTHON_SCRIPT" list --branches worktrees 2>&1)
        echo "$output"
    fi
}

_gwt_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="repo switch s list ls l remove rm"
    
    # Don't use file completion as a fallback
    compopt -o nospace

    # For the first argument (position 1), complete with commands
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        # Add space after command completion
        compopt +o nospace
        mapfile -t COMPREPLY < <(compgen -W "${commands}" -- "${cur}")
        return 0
    fi

    # For position 2, handle specific subcommand completions
    if [[ ${COMP_CWORD} -eq 2 ]]; then
        case "${prev}" in
            repo)
                # Use directory completion for repo command
                compopt -o filenames -o nospace
                mapfile -t COMPREPLY < <(compgen -d -- "${cur}")
                return 0
                ;;
            switch|s)
                # All branches for switch
                _gwt_get_branches_output=$("$PYTHON_SCRIPT" list --branches all --annotate bash 2>/dev/null)
                if [ -n "$_gwt_get_branches_output" ]; then
                    branches=$(echo "$_gwt_get_branches_output" | tr '\n' ' ')
                    mapfile -t COMPREPLY < <(compgen -W "${branches}" -- "${cur}")
                fi
                return 0
                ;;
            remove|rm)
                # Only worktrees (excluding main)
                _gwt_get_branches_output=$("$PYTHON_SCRIPT" list --branches worktrees --annotate bash 2>/dev/null)
                if [ -n "$_gwt_get_branches_output" ]; then
                    branches=$(echo "$_gwt_get_branches_output" | tr '\n' ' ')
                    mapfile -t COMPREPLY < <(compgen -W "${branches}" -- "${cur}")
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
    # Helper: strip leading icons (●, ○, ⊙) and spaces from a single token
    _gwt_strip_visual() {
        local arg="$1"
        # Remove optional icon + space
        arg="${arg/#● /}"
        arg="${arg/#○ /}"
        arg="${arg/#⊙ /}"
        echo "$arg"
    }

    # Normalize the branch argument if present for switch/remove commands
    if [[ "$1" == "remove" || "$1" == "rm" || "$1" == "switch" || "$1" == "s" ]]; then
        if [[ $# -ge 2 ]]; then
            set -- "$1" "$(_gwt_strip_visual "$2")" "${@:3}"
        fi
    fi

    # Check if this is an interactive command that shouldn't have output captured
    if [[ "$1" == "remove" || "$1" == "rm" ]]; then
        # Run interactively but capture the last line for potential cd command
        # Use a temp file to capture output while still allowing interaction
        local tmpfile
        tmpfile=$(mktemp)
        "$PYTHON_SCRIPT" "$@" | tee "$tmpfile"
        local last_line
        last_line=$(tail -n1 "$tmpfile")
        rm "$tmpfile"
        
        # Check if the last line is a cd command
        if [[ "$last_line" == cd* ]]; then
            local dir="${last_line#cd }"
            cd "$dir" || echo "Failed to change directory to $dir"
        fi
    else
        # Run the Python script and capture output for non-interactive commands
        local output
        output=$("$PYTHON_SCRIPT" "$@")
        
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