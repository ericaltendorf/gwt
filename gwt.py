#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def run_git_command(cmd_args, git_dir):
    """Run a git command using the specified git directory."""
    cmd = ["git", f"--git-dir={git_dir}"] + cmd_args
    return subprocess.run(cmd, check=True)


def create_branch_and_worktree(branch_name, git_dir):
    worktree_base = f"{git_dir}/worktrees"
    
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
    worktree_base = f"{git_dir}/worktrees"
    worktree_path = os.path.join(worktree_base, branch_name)
    
    if not os.path.isdir(worktree_path):
        print(f"Error: Worktree for branch '{branch_name}' not found", file=sys.stderr)
        sys.exit(1)

    # Print the command to change directory
    # The calling shell script will parse this and execute the cd
    print(f"cd {worktree_path}")


def list_worktrees(git_dir):
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
        # First find the worktree path
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
        )
        
        # Parse the output to find the worktree for this branch
        worktree_path = None
        for line in result.stdout.splitlines():
            if f"[{branch_name}]" in line:
                worktree_path = line.split()[0]
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
