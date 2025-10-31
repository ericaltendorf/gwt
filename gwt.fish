#!/usr/bin/env fish
# GWT Fish Shell Integration

function gwt
    # Use the Python script from the same directory
    set -l SCRIPT_DIR (dirname (status -f))
    set -l PYTHON_SCRIPT "$SCRIPT_DIR/gwt.py"
    
    # Check if this is an interactive command that shouldn't have output captured
    if test "$argv[1]" = "remove" -o "$argv[1]" = "rm"
        # Run interactively but capture output to check for cd command
        # Use a temp file to capture output while still allowing interaction
        set -l tmpfile (mktemp)
        $PYTHON_SCRIPT $argv | tee $tmpfile
        set -l exit_code $status
        set -l last_line (tail -n1 $tmpfile)
        rm $tmpfile
        
        # Check if the last line is a cd command
        if string match -q "cd *" $last_line
            set -l dir (string replace "cd " "" $last_line)
            cd $dir
            or echo "Failed to change directory to $dir"
        end
        
        return $exit_code
    else
        # Run the Python script and capture output for non-interactive commands
        # Don't redirect stderr to stdout - let error messages go to the terminal
        set -l output ($PYTHON_SCRIPT $argv)
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
end

# Tab completion for gwt
function __gwt_complete_branches
    set -l SCRIPT_DIR (dirname (status -f))
    set -l PYTHON_SCRIPT "$SCRIPT_DIR/gwt.py"
    # Try all branches first, fallback to worktrees
    $PYTHON_SCRIPT list --branches all 2>/dev/null
    or $PYTHON_SCRIPT list --branches worktrees 2>/dev/null
end

function __gwt_complete
    set -l cmd (commandline -opc)
    set -l cur (commandline -ct)
    
    # Commands
    set -l commands repo switch s list ls l remove rm
    
    # Complete first argument with commands
    if test (count $cmd) -eq 1
        printf '%s\n' $commands
        return
    end
    
    # Complete second argument based on subcommand
    set -l subcmd $cmd[2]
    set -l SCRIPT_DIR (dirname (status -f))
    set -l PYTHON_SCRIPT "$SCRIPT_DIR/gwt.py"
    switch $subcmd
        case switch s
            $PYTHON_SCRIPT list --branches all --annotate fish 2>/dev/null
        case remove rm
            $PYTHON_SCRIPT list --branches worktrees --annotate fish 2>/dev/null
        case repo
            __fish_complete_directories
        case '*'
            return
    end
end

complete -c gwt -f -k -a '(__gwt_complete)'