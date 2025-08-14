#!/usr/bin/env fish
# GWT Fish Shell Integration

function gwt
    # Use the Python script from the same directory
    set -l SCRIPT_DIR (dirname (status -f))
    set -l PYTHON_SCRIPT "$SCRIPT_DIR/gwt.py"
    
    # Run the Python script and capture output
    set -l output ($PYTHON_SCRIPT $argv 2>&1)
    set -l exit_code $status
    
    # Parse output for special commands
    if string match -q "cd *" $output
        # Extract directory and change to it
        set -l dir (string replace "cd " "" $output)
        cd $dir
        or echo "Failed to change directory to $dir"
    else if string match -q "GWT_GIT_DIR=*" $output
        # Extract git directory and set it
        set -l dir (string replace "GWT_GIT_DIR=" "" $output)
        if test -d $dir
            set -gx GWT_GIT_DIR $dir
            echo "GWT_GIT_DIR set to $dir"
        else
            echo "Error: $dir is not a valid directory" >&2
            return 1
        end
    else
        # Just print the output
        echo $output
    end
    
    return $exit_code
end

# Tab completion for gwt
function __gwt_complete_branches
    set -l SCRIPT_DIR (dirname (status -f))
    set -l PYTHON_SCRIPT "$SCRIPT_DIR/gwt.py"
    $PYTHON_SCRIPT list --branches 2>/dev/null
end

function __gwt_complete
    set -l cmd (commandline -opc)
    set -l cur (commandline -ct)
    
    # Commands
    set -l commands new track repo switch s list ls l remove rm
    
    # Complete first argument with commands
    if test (count $cmd) -eq 1
        printf '%s\n' $commands
        return
    end
    
    # Complete second argument based on subcommand
    set -l subcmd $cmd[2]
    switch $subcmd
        case switch s remove rm
            __gwt_complete_branches
        case repo
            __fish_complete_directories
        case '*'
            return
    end
end

complete -c gwt -f -a '(__gwt_complete)'