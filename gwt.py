#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def run_git_command(cmd_args, git_dir):
    """Run a git command using the specified git directory."""
    cmd = ["git", f"--git-dir={git_dir}"] + cmd_args
    return subprocess.run(cmd, check=True)


def get_worktree_base(git_dir):
    """Get the standard worktree base directory from git_dir."""
    # Replace .git extension with .gwt
    if git_dir.endswith('.git'):
        worktree_base = git_dir[:-4] + '.gwt'
    else:
        # Fallback if no .git extension
        worktree_base = git_dir + '.gwt'
    
    # Create the directory if it doesn't exist
    if not os.path.exists(worktree_base):
        os.makedirs(worktree_base, exist_ok=True)
        # Create a README.md file explaining the directory
        readme_path = os.path.join(worktree_base, 'README.md')
        with open(readme_path, 'w') as f:
            f.write("""# Git Worktree Directory

This directory contains git worktrees managed by the gwt tool.
Each subdirectory is a separate worktree for a branch.

For more information, see: https://github.com/username/gwt
""")
        
    return worktree_base


def create_branch_and_worktree(branch_name, git_dir):
    worktree_base = get_worktree_base(git_dir)
    
    try:
        # Create new branch
        run_git_command(["branch", branch_name], git_dir)
        # Add worktree
        worktree_path = os.path.join(worktree_base, branch_name)
        run_git_command(["worktree", "add", worktree_path, branch_name], git_dir)
        print(f"Created branch '{branch_name}' and worktree at {worktree_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def switch_to_worktree(branch_name, git_dir):
    # Use the standard worktree base directory
    worktree_base = get_worktree_base(git_dir)
    worktree_path = os.path.join(worktree_base, branch_name)
    
    if not os.path.isdir(worktree_path):
        # Try to find the worktree using our shared function
        worktrees = get_worktree_list(git_dir)
        
        # Check if the branch exists but is in a different location
        for worktree in worktrees:
            if worktree['branch'] == branch_name:
                worktree_path = worktree['path']
                break
        else:
            # Branch not found in any worktree
            print(f"Error: Worktree for branch '{branch_name}' not found", file=sys.stderr)
            sys.exit(1)

    # Print the command to change directory
    # The calling shell script will parse this and execute the cd
    print(f"cd {worktree_path}")


def get_worktree_list(git_dir):
    """Get a list of all worktrees for the repository.
    
    Returns a list of dicts with 'path' and 'branch' keys.
    """
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
        )
        
        worktrees = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                path = parts[0]
                branch_info = parts[2]
                # Extract branch name from [branch] format
                branch = branch_info.strip('[]')
                # Skip detached HEAD worktrees
                if branch != '(detached)' and not branch.startswith('(HEAD'):
                    worktrees.append({
                        'path': path,
                        'branch': branch
                    })
        
        return worktrees
    except subprocess.CalledProcessError as e:
        print(f"Error listing worktrees: {e}", file=sys.stderr)
        sys.exit(1)


def list_worktrees(git_dir):
    """Display list of worktrees to the user."""
    # Get worktrees using our shared function
    worktrees = get_worktree_list(git_dir)
    
    if not worktrees:
        print("No worktrees found")
        return
    
    # Display the full worktree list using the git command for consistent output
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
    except subprocess.CalledProcessError as e:
        print(f"Error listing worktrees: {e}", file=sys.stderr)
        sys.exit(1)
        
        
def remove_worktree(branch_name, git_dir):
    try:
        # Find the worktree path using our shared function
        worktrees = get_worktree_list(git_dir)
        
        # Find the worktree for this branch
        worktree_path = None
        for worktree in worktrees:
            if worktree['branch'] == branch_name:
                worktree_path = worktree['path']
                break
        
        if not worktree_path:
            print(f"Error: Worktree for branch '{branch_name}' not found", file=sys.stderr)
            sys.exit(1)
        
        # Remove the worktree
        run_git_command(["worktree", "remove", worktree_path], git_dir)
        
        # Then remove the branch if the user confirms
        confirm = input(f"Do you also want to delete the branch '{branch_name}'? (y/N): ")
        if confirm.lower() == 'y':
            run_git_command(["branch", "-D", branch_name], git_dir)
            print(f"Branch '{branch_name}' has been deleted")
        
        print(f"Worktree for '{branch_name}' has been removed")
    except subprocess.CalledProcessError as e:
        print(f"Error removing worktree: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Git worktree wrapper")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create a 'new' subcommand
    new_parser = subparsers.add_parser("new", help="Create a new branch and worktree")
    new_parser.add_argument("branch_name", help="Name of the new branch")

    # Create a 'repo' subcommand 
    repo_parser = subparsers.add_parser("repo", help="Set the git directory")
    repo_parser.add_argument("git_dir", help="Path to the git directory")
    
    # Create a 'switch' subcommand with 's' as alias
    switch_parser = subparsers.add_parser("switch", aliases=["s"], help="Switch to existing branch worktree")
    switch_parser.add_argument("branch_name", help="Name of the branch to switch to")
    
    # Create a 'remove' subcommand with 'rm' as alias
    remove_parser = subparsers.add_parser("remove", aliases=["rm"], help="Remove a worktree and optionally its branch")
    remove_parser.add_argument("branch_name", help="Name of the branch worktree to remove")
    
    # Create a 'list' subcommand that's implicit if no command is provided
    list_parser = subparsers.add_parser("list", aliases=["ls", "l"], help="List all worktrees")
    list_parser.add_argument("--branches", action="store_true", help="List only branch names (for tab completion)")
    list_parser.add_argument("--paths", action="store_true", help="List only paths (for scripts)")
    
    args = parser.parse_args()

    # Handle repo command without needing GIT_DIR
    if args.command == "repo":
        # Just print a message for the shell script to handle
        print(f"GWT_GIT_DIR={args.git_dir}")
        return
        
    # If no command specified, default to list
    if args.command is None:
        args.command = "list"

    # For other commands, check GIT_DIR once
    git_dir = os.environ.get("GWT_GIT_DIR")
    if not git_dir:
        print("Error: GWT_GIT_DIR environment variable is not set.", file=sys.stderr)
        print("Please set it with: gwt repo /path/to/your/repo.git", file=sys.stderr)
        sys.exit(1)

    # Now pass git_dir to all functions that need it
    if args.command == "new":
        create_branch_and_worktree(args.branch_name, git_dir)
    elif args.command in ["switch", "s"]:
        switch_to_worktree(args.branch_name, git_dir)
    elif args.command in ["remove", "rm"]:
        remove_worktree(args.branch_name, git_dir)
    elif args.command in ["list", "ls", "l"]:
        list_worktrees(git_dir)


if __name__ == "__main__":
    main()
