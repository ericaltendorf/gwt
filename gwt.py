#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

# Default to current directory if GWT_GIT_DIR is not set
GIT_DIR = os.environ.get("GWT_GIT_DIR")
if not GIT_DIR:
    print("Error: GWT_GIT_DIR environment variable is not set.", file=sys.stderr)
    print("Please set it with: gwt --set-git-dir /path/to/your/repo.git", file=sys.stderr)
    sys.exit(1)

WORKTREE_BASE = f"{GIT_DIR}/worktrees"


def run_git_command(cmd_args):
    cmd = ["git", f"--git-dir={GIT_DIR}"] + cmd_args
    return subprocess.run(cmd, check=True)


def create_branch_and_worktree(branch_name):
    try:
        # Create new branch
        run_git_command(["branch", branch_name])
        # Add worktree
        worktree_path = os.path.join(WORKTREE_BASE, branch_name)
        run_git_command(["worktree", "add", worktree_path, branch_name])
        print(f"Created branch '{branch_name}' and worktree at {worktree_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def switch_to_worktree(branch_name):
    worktree_path = os.path.join(WORKTREE_BASE, branch_name)
    if not os.path.isdir(worktree_path):
        print(f"Error: Worktree for branch '{branch_name}' not found", file=sys.stderr)
        sys.exit(1)

    # Print the command to change directory
    # The calling shell script will parse this and execute the cd
    print(f"cd {worktree_path}")


def list_worktrees():
    try:
        result = subprocess.run(
            ["git", f"--git-dir={GIT_DIR}", "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout, end="")
    except subprocess.CalledProcessError as e:
        print(f"Error listing worktrees: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Git worktree wrapper")
    parser.add_argument("-a", metavar="BRANCH", help="Create a new branch and worktree")
    parser.add_argument("branch", nargs="?", help="Switch to existing branch worktree")

    args = parser.parse_args()

    if args.a:
        create_branch_and_worktree(args.a)
    elif args.branch:
        switch_to_worktree(args.branch)
    else:
        list_worktrees()


if __name__ == "__main__":
    main()
