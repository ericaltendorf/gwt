#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "tomli>=2.0.0; python_version < '3.11'",
#   "tomli-w>=1.0.0",
# ]
# ///

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Try to import TOML libraries, but fall back to no-op config if unavailable
try:
    # Python 3.11+ has tomllib built-in
    if sys.version_info >= (3, 11):
        import tomllib as tomli
    else:
        import tomli
    import tomli_w

    HAS_TOML = True
except ImportError:
    print(
        "Warning: tomli/tomli_w packages not found. Configuration features will be disabled.",
        file=sys.stderr,
    )
    print("Install with: pip install tomli tomli-w", file=sys.stderr)
    HAS_TOML = False


# Configuration functions
def get_config_path():
    """Get the path to the config file."""
    # Use XDG_CONFIG_HOME if available, otherwise ~/.config
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / "gwt"
    else:
        config_dir = Path.home() / ".config" / "gwt"

    # Create the directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir / "config.toml"


def load_config():
    """Load the configuration from the config file."""
    # Default configuration
    default_config = {"default_repo": None, "repos": {}}

    # If TOML libraries aren't available, return default config
    if not HAS_TOML:
        return default_config

    config_path = get_config_path()

    # If the config file doesn't exist, create it
    if not config_path.exists():
        try:
            with open(config_path, "wb") as f:
                tomli_w.dump(default_config, f)
        except Exception as e:
            print(f"Error creating config file: {e}", file=sys.stderr)
        return default_config

    # Load the config
    try:
        with open(config_path, "rb") as f:
            config = tomli.load(f)
        return config
    except Exception as e:
        print(f"Error loading config file: {e}", file=sys.stderr)
        return default_config


def save_config(config):
    """Save the configuration to the config file."""
    # If TOML libraries aren't available, do nothing
    if not HAS_TOML:
        return

    config_path = get_config_path()

    try:
        with open(config_path, "wb") as f:
            tomli_w.dump(config, f)
    except Exception as e:
        print(f"Error saving config file: {e}", file=sys.stderr)


def get_repo_config(git_dir):
    """Get the configuration for a specific repository.

    Config file format:

    ```toml
    # ~/.config/gwt/config.toml

    # Default repository to use if GWT_GIT_DIR env var isn't set
    default_repo = "/path/to/default/repo.git"

    # Repository-specific configurations
    [repos."/path/to/repo1.git"]
    # Commands to run after creating a new worktree
    # These run in the new worktree directory
    post_create_commands = [
        "npm install",
        "cp ../.env.example .env",
        "echo 'Worktree setup complete!'"
    ]

    [repos."/path/to/repo2.git"]
    post_create_commands = [
        "pip install -e .",
        "pre-commit install"
    ]
    ```
    """
    config = load_config()

    # Try to find the repo in the config
    if "repos" in config and git_dir in config["repos"]:
        return config["repos"][git_dir]

    # If not found, create a default repo config
    default_repo_config = {"post_create_commands": []}

    # Add it to the config
    if "repos" not in config:
        config["repos"] = {}
    config["repos"][git_dir] = default_repo_config
    save_config(config)

    return default_repo_config


def run_git_command(cmd_args, git_dir, capture=True):
    """Run a git command using the specified git directory.
    
    Args:
        cmd_args: List of git command arguments
        git_dir: Path to the git directory
        capture: If True, capture output to prevent it from interfering with shell commands.
                If False, let git interact directly with the terminal (for interactive commands).
    """
    cmd = ["git", f"--git-dir={git_dir}"] + cmd_args
    if capture:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # Print git's output to stderr so it doesn't interfere with shell commands
        if result.stdout:
            print(result.stdout, file=sys.stderr, end='')
        if result.stderr:
            print(result.stderr, file=sys.stderr, end='')
        return result
    else:
        # For interactive commands, don't capture output
        return subprocess.run(cmd, check=True)


def get_worktree_base(git_dir):
    """Get the standard worktree base directory from git_dir."""
    git_dir_path = Path(git_dir).resolve()
    
    # Check if this is a non-bare repo (ends with /.git subdirectory)
    if git_dir_path.name == ".git" and git_dir_path.is_dir():
        # Non-bare repo: /path/to/repo/.git -> /path/to/repo.gwt
        repo_path = git_dir_path.parent
        worktree_base = str(repo_path) + ".gwt"
    elif git_dir.endswith(".git"):
        # Bare repo: /path/to/repo.git -> /path/to/repo.gwt
        worktree_base = git_dir[:-4] + ".gwt"
    else:
        # Fallback for other cases
        worktree_base = git_dir.rstrip("/") + ".gwt"
    # Create the directory if it doesn't exist
    if not os.path.exists(worktree_base):
        os.makedirs(worktree_base, exist_ok=True)
        # Create a README.md file explaining the directory
        readme_path = os.path.join(worktree_base, "README.md")
        with open(readme_path, "w") as f:
            f.write(
                """# Git Worktree Directory

This directory contains git worktrees managed by the gwt tool.
Each subdirectory is a separate worktree for a branch.

For more information, see: https://github.com/username/gwt
"""
            )

    return worktree_base


def create_branch_and_worktree(branch_name, git_dir):
    worktree_base = get_worktree_base(git_dir)

    try:
        # Create new branch (will fail if it already exists)
        run_git_command(["branch", branch_name], git_dir)
        # Add worktree
        worktree_path = os.path.join(worktree_base, branch_name)
        run_git_command(["worktree", "add", worktree_path, branch_name], git_dir)
        print(
            f"Created branch '{branch_name}' and worktree at {worktree_path}",
            file=sys.stderr,
        )

        # Get the repo config to check for post-create commands
        repo_config = get_repo_config(git_dir)
        if repo_config.get("post_create_commands"):
            print(f"Running post-create commands for {branch_name}...", file=sys.stderr)
            current_dir = os.getcwd()
            try:
                # Change to the worktree directory to run the commands
                os.chdir(worktree_path)
                for cmd in repo_config["post_create_commands"]:
                    print(f"Running: {cmd}", file=sys.stderr)
                    subprocess.run(cmd, shell=True, check=True)
            except Exception as e:
                print(f"Error running post-create commands: {e}", file=sys.stderr)
            finally:
                # Change back to the original directory
                os.chdir(current_dir)

        # Print the command to change directory (like switch_to_worktree does)
        # The calling shell script will parse this and execute the cd
        print(f"cd {worktree_path}")

    except subprocess.CalledProcessError as e:
        # Show git's actual error message if available
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        elif hasattr(e, 'stdout') and e.stdout:
            print(f"Error: {e.stdout.strip()}", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def track_remote_branch(branch_name, git_dir, remote="origin"):
    """Create a worktree that tracks a remote branch.
    
    First fetches the remote branch, then creates a local branch tracking the remote,
    and sets up a worktree for it.
    """
    worktree_base = get_worktree_base(git_dir)
    worktree_path = os.path.join(worktree_base, branch_name)
    
    try:
        # Fetch the remote branch
        print(f"Fetching {remote}/{branch_name}...", file=sys.stderr)
        run_git_command(["fetch", remote, branch_name], git_dir)
        
        # Create worktree with tracking branch
        print(f"Creating worktree at {worktree_path}...", file=sys.stderr)
        run_git_command(
            ["worktree", "add", "-b", branch_name, worktree_path, f"{remote}/{branch_name}"],
            git_dir
        )
        print(
            f"Created tracking branch '{branch_name}' for '{remote}/{branch_name}' and worktree at {worktree_path}",
            file=sys.stderr,
        )
        
        # Get the repo config to check for post-create commands
        repo_config = get_repo_config(git_dir)
        if repo_config.get("post_create_commands"):
            print(f"Running post-create commands for {branch_name}...", file=sys.stderr)
            current_dir = os.getcwd()
            try:
                # Change to the worktree directory to run the commands
                os.chdir(worktree_path)
                for cmd in repo_config["post_create_commands"]:
                    print(f"Running: {cmd}", file=sys.stderr)
                    subprocess.run(cmd, shell=True, check=True)
            except Exception as e:
                print(f"Error running post-create commands: {e}", file=sys.stderr)
            finally:
                # Change back to the original directory
                os.chdir(current_dir)

        # Print the command to change directory (like switch_to_worktree does)
        # The calling shell script will parse this and execute the cd
        print(f"cd {worktree_path}")

    except subprocess.CalledProcessError as e:
        # Show git's actual error message if available
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        elif hasattr(e, 'stdout') and e.stdout:
            print(f"Error: {e.stdout.strip()}", file=sys.stderr)
        else:
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
            if worktree["branch"] == branch_name:
                worktree_path = worktree["path"]
                break
        else:
            # Branch not found in any worktree
            print(
                f"Error: Worktree for branch '{branch_name}' not found", file=sys.stderr
            )
            sys.exit(1)

    # Print the command to change directory
    # The calling shell script will parse this and execute the cd
    print(f"cd {worktree_path}")


def get_git_worktrees(git_dir):
    """Get worktrees as reported by git worktree list command.

    Returns a dict mapping branch names to their paths.
    Excludes the main working tree (first entry).
    """
    git_worktrees = {}
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
        )

        lines = result.stdout.splitlines()
        for i, line in enumerate(lines):
            parts = line.split()
            if len(parts) >= 3:
                path = parts[0]
                branch_info = parts[2]
                # Extract branch name from [branch] format
                branch = branch_info.strip("[]")
                
                # Skip the first entry - it's the main working tree
                if i == 0:
                    continue
                    
                # Skip detached HEAD worktrees
                if branch != "(detached)" and not branch.startswith("(HEAD"):
                    git_worktrees[branch] = path

        return git_worktrees
    except subprocess.CalledProcessError as e:
        print(f"Error listing git worktrees: {e}", file=sys.stderr)
        sys.exit(1)


def get_directory_worktrees(git_dir):
    """Get worktrees by examining the worktree directory structure.

    Returns a dict mapping branch names to their paths.
    """
    dir_worktrees = {}
    worktree_base = get_worktree_base(git_dir)

    # Check if the worktree directory exists
    if not os.path.isdir(worktree_base):
        return dir_worktrees

    # Look for subdirectories in the worktree base directory
    try:
        for entry in os.listdir(worktree_base):
            path = os.path.join(worktree_base, entry)
            if os.path.isdir(path):
                # Check if it looks like a git worktree
                if os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(
                    os.path.join(path, ".git")
                ):
                    dir_worktrees[entry] = path

        return dir_worktrees
    except OSError as e:
        print(f"Error examining worktree directory: {e}", file=sys.stderr)
        return dir_worktrees


def get_worktree_list(git_dir):
    """Get a list of all worktrees for the repository, comparing git command output
    with directory examination.

    Returns a list of dicts with 'path' and 'branch' keys.
    """
    # Get worktrees from both sources (already excludes main working tree)
    git_worktrees = get_git_worktrees(git_dir)
    dir_worktrees = get_directory_worktrees(git_dir)

    # Combine results, reporting any discrepancies
    worktrees = []
    all_branches = set(git_worktrees.keys()) | set(dir_worktrees.keys())

    for branch in all_branches:
        git_path = git_worktrees.get(branch)
        dir_path = dir_worktrees.get(branch)

        if git_path and dir_path:
            # Branch exists in both sources
            if git_path != dir_path:
                print(f"Warning: Mismatch for branch '{branch}':", file=sys.stderr)
                print(f"  Git reports: {git_path}", file=sys.stderr)
                print(f"  Directory shows: {dir_path}", file=sys.stderr)

            # Use the git path as the source of truth
            worktrees.append({"path": git_path, "branch": branch})
        elif git_path:
            # Branch exists in git but not in directory - only warn if it's
            # supposed to be in the .gwt directory
            worktree_base = get_worktree_base(git_dir)
            if git_path.startswith(worktree_base):
                print(
                    f"Warning: Branch '{branch}' found by git but not in worktree directory",
                    file=sys.stderr,
                )
            worktrees.append({"path": git_path, "branch": branch})
        elif dir_path:
            # Branch exists in directory but not reported by git
            print(
                f"Warning: Directory '{branch}' exists in worktree path but not recognized by git",
                file=sys.stderr,
            )
            # Don't add to the list as it's not a valid worktree according to git

    return worktrees


def list_worktrees(git_dir, branches_only=False):
    """Display list of worktrees to the user.

    If branches_only is True, only prints the branch names, one per line.
    """
    try:
        # Get worktrees using our shared function
        worktrees = get_worktree_list(git_dir)

        if not worktrees:
            if not branches_only:
                print("No worktrees found")
            return

        if branches_only:
            # Just print branch names, one per line (for tab completion)
            for worktree in worktrees:
                print(worktree["branch"])
        else:
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
    except Exception as e:
        if not branches_only:
            print(f"Error: {e}", file=sys.stderr)
        # In branches-only mode, just return silently on error
        return


def remove_worktree(branch_name, git_dir):
    try:
        # Find the worktree path using our shared function
        worktrees = get_worktree_list(git_dir)

        # Find the worktree for this branch
        worktree_path = None
        for worktree in worktrees:
            if worktree["branch"] == branch_name:
                worktree_path = worktree["path"]
                break

        if not worktree_path:
            print(
                f"Error: Worktree for branch '{branch_name}' not found", file=sys.stderr
            )
            sys.exit(1)

        # Check if we're currently in the worktree being removed
        current_dir = os.getcwd()
        worktree_abs = os.path.abspath(worktree_path)
        current_abs = os.path.abspath(current_dir)
        
        need_cd = False
        if current_abs.startswith(worktree_abs + os.sep) or current_abs == worktree_abs:
            need_cd = True
            # Determine the safe directory based on repo type
            git_dir_path = Path(git_dir).resolve()
            
            if git_dir_path.name == ".git" and git_dir_path.is_dir():
                # Non-bare repo: git_dir is /path/to/repo/.git
                # Safe dir should be the repo itself: /path/to/repo
                safe_dir = str(git_dir_path.parent)
            else:
                # Bare repo: git_dir is /path/to/repo.git
                # Safe dir should be parent of .gwt: /path/to
                safe_dir = os.path.dirname(get_worktree_base(git_dir))
            
            print(f"You're in the worktree being removed. Will change to {safe_dir} after removal.", file=sys.stderr)

        # Remove the worktree (don't capture output as it might prompt the user)
        run_git_command(["worktree", "remove", worktree_path], git_dir, capture=False)

        # Then remove the branch if the user confirms
        # Print to stderr and flush to ensure prompt is visible immediately
        print(
            f"Do you also want to delete the branch '{branch_name}'? (y/N): ",
            end="",
            file=sys.stderr,
        )
        sys.stderr.flush()
        confirm = input()
        if confirm.lower() == "y":
            # Change to safe directory first if needed, before trying to delete branch
            if need_cd:
                os.chdir(safe_dir)
            run_git_command(["branch", "-D", branch_name], git_dir, capture=False)
            print(f"Branch '{branch_name}' has been deleted")

        print(f"Worktree for '{branch_name}' has been removed")
        
        # Output the cd command for the shell to execute if we were in the removed worktree
        if need_cd:
            print(f"cd {safe_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Error removing worktree: {e}", file=sys.stderr)
        sys.exit(1)


def get_git_dir():
    """Get the git directory from either the environment variable or the config file.

    This is a common function to encapsulate the logic for determining the git dir.
    Automatically appends .git for non-bare repositories.

    Returns:
        str: The git directory path, or None if not found
    """
    # First, check if GWT_GIT_DIR is set in the environment
    git_dir = os.environ.get("GWT_GIT_DIR")
    if git_dir:
        # Auto-detect if we need to append .git
        if os.path.isdir(git_dir):
            # Check if this is a non-bare repo (has .git subdirectory)
            dot_git = os.path.join(git_dir, ".git")
            if os.path.isdir(dot_git):
                return dot_git
            return git_dir

    # If not set in environment, check the config file if TOML is available
    if HAS_TOML:
        config = load_config()
        default_repo = config.get("default_repo")
        if default_repo:
            # Auto-detect if we need to append .git
            if os.path.isdir(default_repo):
                # Check if this is a non-bare repo (has .git subdirectory)
                dot_git = os.path.join(default_repo, ".git")
                if os.path.isdir(dot_git):
                    return dot_git
                return default_repo

    # If neither source provides a valid git dir, return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Git worktree wrapper")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create a 'new' subcommand
    new_parser = subparsers.add_parser("new", help="Create a new branch and worktree")
    new_parser.add_argument("branch_name", help="Name of the new branch")

    # Create a 'track' subcommand
    track_parser = subparsers.add_parser("track", help="Create a worktree that tracks a remote branch")
    track_parser.add_argument("branch_name", help="Name of the branch to track")
    track_parser.add_argument(
        "--remote", "-r", 
        default="origin",
        help="Remote to track (default: origin)"
    )

    # Create a 'repo' subcommand
    repo_parser = subparsers.add_parser("repo", help="Set or show the git directory")
    repo_parser.add_argument("git_dir", nargs="?", help="Path to the git directory (omit to show current)")

    # Create a 'switch' subcommand with 's' as alias
    switch_parser = subparsers.add_parser(
        "switch", aliases=["s"], help="Switch to existing branch worktree"
    )
    switch_parser.add_argument("branch_name", help="Name of the branch to switch to")

    # Create a 'remove' subcommand with 'rm' as alias
    remove_parser = subparsers.add_parser(
        "remove", aliases=["rm"], help="Remove a worktree and optionally its branch"
    )
    remove_parser.add_argument(
        "branch_name", help="Name of the branch worktree to remove"
    )

    # Create a 'list' subcommand that's implicit if no command is provided
    list_parser = subparsers.add_parser(
        "list", aliases=["ls", "l"], help="List all worktrees"
    )
    list_parser.add_argument(
        "--branches",
        action="store_true",
        help="List only branch names (for tab completion)",
    )
    list_parser.add_argument(
        "--git-dir", help="Explicitly specify the git directory (for tab completion)"
    )

    # Special command to get the default repository from config
    get_repo_parser = subparsers.add_parser(
        "get-repo", help="Get the default repository from config (internal use)"
    )

    args = parser.parse_args()

    # Handle special commands that don't need a configured git dir
    if args.command == "repo":
        if args.git_dir:
            # Auto-detect if we need to append .git for non-bare repos
            git_dir = args.git_dir
            if os.path.isdir(git_dir):
                dot_git = os.path.join(git_dir, ".git")
                if os.path.isdir(dot_git):
                    git_dir = dot_git
            
            # Set the git directory
            print(f"GWT_GIT_DIR={git_dir}")

            # Update the config if TOML is available
            if HAS_TOML:
                config = load_config()
                config["default_repo"] = git_dir
                save_config(config)
                print(f"Default repo set to {git_dir}", file=sys.stderr)
            else:
                print(
                    f"Note: Config file not updated (TOML support not available)",
                    file=sys.stderr,
                )
        else:
            # Show the current git directory
            current_git_dir = get_git_dir()
            if current_git_dir:
                print(f"Current repo: {current_git_dir}")
            else:
                print("No repo currently configured")
        return
    elif args.command == "get-repo":
        # Special command to output the default repo from config
        # This is used by the shell completion function
        if HAS_TOML:
            config = load_config()
            if config.get("default_repo") and os.path.isdir(config["default_repo"]):
                print(config["default_repo"])
        return

    # If no command specified, default to list
    if args.command is None:
        args.command = "list"

    # Get the git directory from environment or config
    git_dir = None

    # Check for explicit git-dir in arguments (for list command)
    if hasattr(args, "git_dir") and args.git_dir:
        git_dir = args.git_dir
    else:
        # Use the common function to get the git dir
        git_dir = get_git_dir()

    # If no git dir is available, show error and exit
    if not git_dir:
        if HAS_TOML:
            print(
                "Error: GWT_GIT_DIR environment variable is not set and no default repo is configured.",
                file=sys.stderr,
            )
            print(
                "Please set it with: gwt repo /path/to/your/repo.git", file=sys.stderr
            )
            print(
                "Or configure a default repo in ~/.config/gwt/config.toml",
                file=sys.stderr,
            )
        else:
            print(
                "Error: GWT_GIT_DIR environment variable is not set.", file=sys.stderr
            )
            print(
                "Please set it with: gwt repo /path/to/your/repo.git", file=sys.stderr
            )
        sys.exit(1)

    # Now pass git_dir to all functions that need it
    if args.command == "new":
        create_branch_and_worktree(args.branch_name, git_dir)
    elif args.command == "track":
        track_remote_branch(args.branch_name, git_dir, args.remote)
    elif args.command == "repo":
        # Just print a message for the shell script to handle
        print(f"GWT_GIT_DIR={args.git_dir}")
    elif args.command in ["switch", "s"]:
        switch_to_worktree(args.branch_name, git_dir)
    elif args.command in ["remove", "rm"]:
        remove_worktree(args.branch_name, git_dir)
    elif args.command in ["list", "ls", "l"]:
        # Check if branches-only mode is requested
        branches_only = hasattr(args, "branches") and args.branches
        try:
            list_worktrees(git_dir, branches_only=branches_only)
        except Exception as e:
            # When in branches-only mode, don't raise errors, just fail silently
            if not branches_only:
                print(f"Error listing worktrees: {e}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
