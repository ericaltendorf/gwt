#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "tomli>=2.0.0; python_version < '3.11'",
#   "tomli-w>=1.0.0",
# ]
# ///

import argparse
import os
import shutil
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


def get_main_worktree_path(git_dir):
    """Get the path to the main worktree."""
    git_dir_path = Path(git_dir).resolve()
    
    if git_dir_path.name == ".git" and git_dir_path.is_dir():
        # Non-bare repo: main worktree is parent of .git
        return str(git_dir_path.parent)
    else:
        # Bare repo: no main worktree
        return None


def get_main_branch_name(git_dir):
    """Get the name of the branch in the main worktree."""
    try:
        result = run_git_command(["worktree", "list"], git_dir)
        lines = result.stdout.splitlines()
        if lines:
            # First line is main worktree
            parts = lines[0].split()
            if len(parts) >= 3:
                return parts[2].strip("[]")
    except:
        pass
    return None


def branch_exists_locally(branch_name, git_dir):
    """Check if a branch exists locally."""
    result = subprocess.run(
        ["git", f"--git-dir={git_dir}", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def find_remote_branch(branch_name, git_dir):
    """Find a remote branch matching the given name.
    
    Returns the full remote ref (e.g., 'origin/branch') or None.
    """
    # First, fetch all remotes to ensure we have latest
    run_git_command(["remote", "update"], git_dir)
    
    # Look for matching remote branches
    result = run_git_command(
        ["for-each-ref", "--format=%(refname:short)", f"refs/remotes/*/{branch_name}"],
        git_dir
    )
    
    refs = result.stdout.strip().split('\n')
    refs = [r for r in refs if r]  # Filter empty
    
    if len(refs) == 1:
        return refs[0]
    elif len(refs) > 1:
        # Multiple remotes have this branch - prefer origin
        for ref in refs:
            if ref.startswith("origin/"):
                return ref
        # If no origin, return first
        return refs[0]
    
    return None


def create_worktree_for_branch(branch_name, git_dir, worktree_path):
    """Create a worktree for an existing local branch."""
    try:
        run_git_command(["worktree", "add", worktree_path, branch_name], git_dir)
        print(f"Created worktree at {worktree_path}", file=sys.stderr)
        run_post_create_commands(git_dir, worktree_path, branch_name)
        print(f"cd {worktree_path}")
    except subprocess.CalledProcessError as e:
        handle_worktree_error(e, branch_name)
        sys.exit(1)


def create_tracking_worktree(branch_name, git_dir, remote_ref, worktree_path):
    """Create a worktree that tracks a remote branch."""
    try:
        # Create local branch tracking the remote
        run_git_command(
            ["worktree", "add", "-b", branch_name, worktree_path, remote_ref],
            git_dir
        )
        print(f"Branch '{branch_name}' set up to track '{remote_ref}'", file=sys.stderr)
        print(f"Created worktree at {worktree_path}", file=sys.stderr)
        run_post_create_commands(git_dir, worktree_path, branch_name)
        print(f"cd {worktree_path}")
    except subprocess.CalledProcessError as e:
        handle_worktree_error(e, branch_name)
        sys.exit(1)


def handle_worktree_error(e, branch_name):
    """Handle errors from worktree creation."""
    # Show git's actual error message if available
    if hasattr(e, 'stderr') and e.stderr:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
    elif hasattr(e, 'stdout') and e.stdout:
        print(f"Error: {e.stdout.strip()}", file=sys.stderr)
    else:
        print(f"Error creating worktree for branch '{branch_name}': {e}", file=sys.stderr)


def run_post_create_commands(git_dir, worktree_path, branch_name):
    """Run post-create commands for a worktree."""
    repo_config = get_repo_config(git_dir)
    if repo_config.get("post_create_commands"):
        print(f"Running post-create commands for {branch_name}...", file=sys.stderr)
        current_dir = os.getcwd()
        try:
            os.chdir(worktree_path)
            for cmd in repo_config["post_create_commands"]:
                print(f"Running: {cmd}", file=sys.stderr)
                # Redirect stdout to stderr to not interfere with cd command
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout:
                    print(result.stdout, file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, cmd)
        except Exception as e:
            print(f"Error running post-create commands: {e}", file=sys.stderr)
        finally:
            os.chdir(current_dir)






def switch_branch(branch_name, git_dir, create=False, force_create=False, guess=True):
    """Unified switch logic that handles all branch scenarios."""
    worktree_base = get_worktree_base(git_dir)
    worktree_path = os.path.join(worktree_base, branch_name)
    
    # Special handling for switching to main repo
    if branch_name == get_main_branch_name(git_dir):
        main_path = get_main_worktree_path(git_dir)
        if main_path:
            print(f"cd {main_path}")
            return
    
    # Check if worktree already exists
    worktrees = get_worktree_list(git_dir, include_main=True)
    for wt in worktrees:
        if wt["branch"] == branch_name:
            print(f"cd {wt['path']}")
            return
    
    # Handle create flags
    if force_create:
        # Force create new branch
        try:
            run_git_command(["branch", "-f", branch_name], git_dir)
        except subprocess.CalledProcessError:
            run_git_command(["branch", branch_name], git_dir)
        create_worktree_for_branch(branch_name, git_dir, worktree_path)
        return
    
    if create:
        # Create new branch
        try:
            run_git_command(["branch", branch_name], git_dir)
            create_worktree_for_branch(branch_name, git_dir, worktree_path)
            return
        except subprocess.CalledProcessError as e:
            print(f"Error: Branch '{branch_name}' already exists", file=sys.stderr)
            print(f"Use -C to force create", file=sys.stderr)
            sys.exit(1)
    
    # Check if local branch exists
    if branch_exists_locally(branch_name, git_dir):
        create_worktree_for_branch(branch_name, git_dir, worktree_path)
        return
    
    # Check remote branches if guess is enabled
    if guess:
        remote_ref = find_remote_branch(branch_name, git_dir)
        if remote_ref:
            create_tracking_worktree(branch_name, git_dir, remote_ref, worktree_path)
            return
    
    # Branch doesn't exist
    print(f"fatal: invalid reference: {branch_name}", file=sys.stderr)
    if guess:
        print(f"hint: If you meant to create a new branch, use: gwt switch -c {branch_name}", file=sys.stderr)
    else:
        print(f"hint: If you meant to check out a remote branch, use: gwt switch --guess {branch_name}", file=sys.stderr)
        print(f"hint: If you meant to create a new branch, use: gwt switch -c {branch_name}", file=sys.stderr)
    sys.exit(1)



def parse_worktree_porcelain(git_dir, include_main=True):
    """
    Parse `git worktree list --porcelain`. Return a list of dict entries:
    {
      "path": str,
      "head": str,           # short SHA (7-10 chars) if available, else ""
      "branch": str or None, # branch name for normal, "(detached)" for detached, or None
      "is_main": bool,       # True for first block if it is the main worktree
      "locked": bool,
      "prunable": bool,
      "detached": bool,
    }
    Returns None if porcelain is unavailable or parsing fails (caller should fallback).
    """
    try:
        res = subprocess.run(
            ["git", f"--git-dir={git_dir}", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        return None

    lines = res.stdout.splitlines()
    if not lines:
        return []

    entries = []
    block = {}
    main_marked = False

    def push_block():
        nonlocal main_marked
        if not block:
            return
        # Normalize defaults
        block.setdefault("head", "")
        block.setdefault("branch", None)
        block.setdefault("locked", False)
        block.setdefault("prunable", False)
        block["detached"] = (block.get("branch") == "(detached)")
        if not main_marked:
            block["is_main"] = True
            main_marked = True
        else:
            block["is_main"] = False
        # Shorten head
        if block["head"]:
            block["head"] = block["head"][:10]
        entries.append(block.copy())

    for ln in lines:
        if not ln.strip():
            continue
        if ln.startswith("worktree "):
            # Start of a new block
            if "path" in block:
                push_block()
                block = {}
            block["path"] = ln.split(" ", 1)[1].strip()
        elif ln.startswith("HEAD "):
            block["head"] = ln.split(" ", 1)[1].strip()
        elif ln.startswith("branch "):
            ref = ln.split(" ", 1)[1].strip()
            if ref == "(detached)":
                block["branch"] = "(detached)"
            elif ref.startswith("refs/heads/"):
                block["branch"] = ref[len("refs/heads/"):]
            else:
                block["branch"] = ref  # fallback
        elif ln.startswith("locked"):
            block["locked"] = True
        elif ln.startswith("prunable"):
            block["prunable"] = True
        # ignore other keys

    if "path" in block:
        push_block()

    # Optionally drop main if not included
    if not include_main and entries:
        entries = [e for i, e in enumerate(entries) if i != 0]
    return entries


def parse_worktree_legacy(git_dir, include_main=True):
    """
    Use `git worktree list` and parse the legacy format.
    Returns entries similar to parse_worktree_porcelain (without locked/prunable).
    """
    try:
        res = subprocess.run(
            ["git", f"--git-dir={git_dir}", "worktree", "list"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        return []

    entries = []
    lines = res.stdout.splitlines()
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) >= 1:
            path = parts[0]
            branch = None
            head = ""  # We'll try to fill short SHA per worktree below
            if len(parts) >= 3:
                branch_info = parts[2].strip("[]")
                if branch_info == "(detached)" or branch_info.startswith("(HEAD"):
                    branch = "(detached)"
                else:
                    branch = branch_info

            if i == 0 and not include_main:
                continue

            # Attempt to get short SHA for each path (best-effort)
            try:
                sha_res = subprocess.run(
                    ["git", "-C", path, "rev-parse", "--short=10", "HEAD"],
                    capture_output=True, text=True, check=True
                )
                head = sha_res.stdout.strip()
            except subprocess.CalledProcessError:
                head = ""

            entries.append({
                "path": path,
                "head": head,
                "branch": branch,
                "is_main": (i == 0),
                "locked": False,
                "prunable": False,
                "detached": (branch == "(detached)"),
            })
    return entries


def get_git_worktrees(git_dir, include_main=False):
    """Get worktrees as reported by git worktree list command.

    Returns a dict mapping branch names to their paths.

    Args:
        git_dir: Path to git directory
        include_main: If True, include the main worktree in results
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
                if i == 0 and not include_main:
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


def get_worktree_list(git_dir, include_main=False, warnings=None):
    """Get a list of all worktrees for the repository, comparing git command output
    with directory examination.

    Args:
        git_dir: Path to git directory
        include_main: If True, include the main worktree in results
        warnings: If provided, append warning strings instead of printing them

    Returns a list of dicts with 'path' and 'branch' keys.
    """
    def warn(msg):
        if warnings is not None:
            warnings.append(msg)
        else:
            print(msg, file=sys.stderr)

    # Get worktrees from both sources (already excludes main working tree)
    git_worktrees = get_git_worktrees(git_dir, include_main=include_main)
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
                warn(f"Warning: Mismatch for branch '{branch}':")
                warn(f"  Git reports: {git_path}")
                warn(f"  Directory shows: {dir_path}")

            # Use the git path as the source of truth
            worktrees.append({"path": git_path, "branch": branch})
        elif git_path:
            # Branch exists in git but not in directory - only warn if it's
            # supposed to be in the .gwt directory
            worktree_base = get_worktree_base(git_dir)
            if git_path.startswith(worktree_base):
                warn(f"Warning: Branch '{branch}' found by git but not in worktree directory")
            worktrees.append({"path": git_path, "branch": branch})
        elif dir_path:
            # Branch exists in directory but not reported by git
            warn(f"Warning: Directory '{branch}' exists in worktree path but not recognized by git")
            # Don't add to the list as it's not a valid worktree according to git

    return worktrees


def is_path_current_worktree(path: str) -> bool:
    """Check if current working directory is inside this worktree path."""
    try:
        cur = os.path.abspath(os.getcwd())
        p = os.path.abspath(path)
        return cur == p or cur.startswith(p + os.sep)
    except Exception:
        return False


def rel_display_path(path: str, git_dir: str, force_absolute: bool) -> str:
    """
    Return relative path for .gwt worktrees; absolute for main.
    If force_absolute True, always absolute.
    """
    if force_absolute:
        return os.path.abspath(path)
    main = get_main_worktree_path(git_dir)
    base = get_worktree_base(git_dir)
    if main and os.path.abspath(path) == os.path.abspath(main):
        return os.path.abspath(path)
    # For .gwt entries, show base-relative path if inside base
    if base and os.path.abspath(path).startswith(os.path.abspath(base) + os.sep):
        return os.path.relpath(path, os.path.dirname(base))
    return os.path.abspath(path)


class ColorMode:
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


def format_worktree_rows(entries, git_dir, show_status=False, color_mode="auto", force_absolute=False):
    """
    entries: list of dicts from parse_worktree_porcelain/legacy
    Returns list[str] lines (without newline), formatted for pretty output.

    Column design:
    [markers:2] [branch:var]  [head:10]  [path:var]
    """
    # Decide color enablement (stderr TTY + NO_COLOR)
    enable_color = False
    if color_mode == ColorMode.ALWAYS:
        enable_color = True
    elif color_mode == ColorMode.AUTO:
        enable_color = sys.stderr.isatty() and (os.environ.get("NO_COLOR") is None)

    # ANSI codes
    BOLD = "\033[1m" if enable_color else ""
    DIM = "\033[2m" if enable_color else ""
    RED = "\033[31m" if enable_color else ""
    YELLOW = "\033[33m" if enable_color else ""
    MAGENTA = "\033[35m" if enable_color else ""
    RESET = "\033[0m" if enable_color else ""

    # Compute status (!) lazily per worktree if requested
    def is_dirty(path):
        if not show_status:
            return False
        try:
            r = subprocess.run(
                ["git", "-C", path, "status", "--porcelain", "-uno"],
                capture_output=True, text=True, check=True
            )
            return bool(r.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    # Sorting: current first, main second, others by branch (case-insensitive)
    def sort_key(e):
        current = is_path_current_worktree(e["path"])
        main = e.get("is_main", False)
        key_branch = (e.get("branch") or "").lower()
        return (0 if current else (1 if main else 2), key_branch)

    entries_sorted = sorted(entries, key=sort_key)

    # Precompute field sizes
    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    head_width = 10
    sep = "  "
    marker_width = 2
    branch_names = [(e.get("branch") or "") for e in entries_sorted]
    max_branch = min(max([len(b) for b in branch_names] + [0]), 40)

    # Build lines
    lines = []
    for e in entries_sorted:
        markers = []

        if is_path_current_worktree(e["path"]):
            markers.append("•")
        else:
            markers.append(" ")

        if e.get("is_main"):
            markers.append("M")
        elif e.get("locked"):
            markers.append("L")
        elif e.get("prunable"):
            markers.append("P")
        else:
            markers.append(" ")

        dirty = is_dirty(e["path"])
        if dirty:
            markers[-1] = "!"

        marker_str = "".join(markers)

        branch = e.get("branch") or ""
        head = e.get("head") or ""
        path = rel_display_path(e["path"], git_dir, force_absolute)

        # Truncation to fit terminal
        fixed = marker_width + len(sep) + head_width + len(sep)
        avail = max(term_width - fixed, 20)
        branch_width = min(max_branch, avail // 2)
        path_width = max(avail - branch_width - len(sep), 10)

        def trunc(s, w):
            if len(s) <= w:
                return s.ljust(w)
            if w <= 1:
                return s[:w]
            return s[:max(0, w - 1)] + "…"

        # Truncate BEFORE applying colors
        branch_cell = trunc(branch, branch_width)
        head_cell = head.ljust(head_width)[:head_width]
        path_cell = trunc(path, path_width)

        # Apply colors AFTER truncation
        if enable_color and is_path_current_worktree(e["path"]):
            branch_cell = f"{BOLD}{branch_cell}{RESET}"
        if enable_color:
            path_cell = f"{DIM}{path_cell}{RESET}"

        # Colorize markers
        if enable_color:
            if "!" in marker_str:
                marker_str = marker_str.replace("!", f"{RED}!{RESET}")
            if "L" in marker_str:
                marker_str = marker_str.replace("L", f"{YELLOW}L{RESET}")
            if "P" in marker_str:
                marker_str = marker_str.replace("P", f"{MAGENTA}P{RESET}")

        line = f"{marker_str}{sep}{branch_cell}{sep}{head_cell}{sep}{path_cell}"
        lines.append(line.rstrip())

    return lines


def list_worktrees(
    git_dir,
    branches_only=False,
    raw=False,
    verbose=False,
    no_warn=False,
    show_status=False,
    color=ColorMode.AUTO,
    absolute=False
):
    """
    Pretty list to stderr by default. stdout remains empty unless branches_only is True.
    """
    try:
        if branches_only:
            # For tab completion, suppress warnings and print branch names only to stdout.
            worktrees = get_worktree_list(git_dir, include_main=True, warnings=[])
            for wt in worktrees:
                if wt.get("branch"):
                    print(wt["branch"])
            return

        # Raw mode (legacy): delegate to git and print to stderr
        if raw:
            try:
                res = subprocess.run(
                    ["git", f"--git-dir={git_dir}", "worktree", "list"],
                    check=True, capture_output=True, text=True
                )
                if res.stdout:
                    print(res.stdout, file=sys.stderr, end="")
            except subprocess.CalledProcessError as e:
                print(f"Error listing worktrees: {e}", file=sys.stderr)
                sys.exit(1)
            return

        # Pretty mode path
        # Collect warnings for summary
        warnings = [] if not no_warn else None
        # Check integrity by invoking the existing reconciliation
        _ = get_worktree_list(git_dir, include_main=False, warnings=warnings if warnings is not None else [])

        # Parse porcelain entries (include main)
        entries = parse_worktree_porcelain(git_dir, include_main=True)
        if entries is None:
            entries = parse_worktree_legacy(git_dir, include_main=True)

        if not entries:
            print("No worktrees found", file=sys.stderr)
            if warnings is not None and verbose and warnings:
                print("", file=sys.stderr)
                for w in warnings:
                    print(w, file=sys.stderr)
            return

        lines = format_worktree_rows(
            entries,
            git_dir=git_dir,
            show_status=show_status,
            color_mode=color,
            force_absolute=absolute
        )
        for ln in lines:
            print(ln, file=sys.stderr)

        # Warning summary
        if warnings is not None and warnings:
            if verbose:
                print("", file=sys.stderr)
                print("Notes:", file=sys.stderr)
                for w in warnings:
                    print(w, file=sys.stderr)
            else:
                n = len(warnings)
                print("", file=sys.stderr)
                print(f"Notes: {n} integrity issue{'s' if n != 1 else ''}. Use -v for details.", file=sys.stderr)

    except Exception as e:
        if not branches_only:
            print(f"Error: {e}", file=sys.stderr)
        return


def list_all_branches(git_dir, mode="all"):
    """List branches for tab completion.

    Args:
        mode: "all", "local", "worktrees"
    """
    branches = set()

    # Always include existing worktrees first (higher priority)
    if mode in ["all", "worktrees"]:
        worktrees = get_worktree_list(git_dir, include_main=True, warnings=[])
        for wt in worktrees:
            if wt["branch"]:
                branches.add(wt["branch"])
                if mode == "worktrees":
                    print(wt["branch"])

    if mode == "worktrees":
        return

    # Add local branches
    if mode in ["all", "local"]:
        try:
            result = run_git_command(
                ["for-each-ref", "--format=%(refname:short)", "refs/heads/"],
                git_dir
            )
            for branch in result.stdout.strip().split('\n'):
                if branch:
                    branches.add(branch)
        except:
            pass

    # Add remote branches (without remote prefix for completion)
    if mode == "all":
        try:
            result = run_git_command(
                ["for-each-ref", "--format=%(refname:short)", "refs/remotes/"],
                git_dir
            )
            for ref in result.stdout.strip().split('\n'):
                if ref and '/' in ref:
                    # Extract branch name from remote/branch
                    branch = ref.split('/', 1)[1]
                    branches.add(branch)
        except:
            pass

    # Get branch categories for proper ordering
    worktree_branches = {wt["branch"] for wt in get_worktree_list(git_dir, include_main=True, warnings=[]) if wt.get("branch")}

    # Get local branches
    local_branches = set()
    try:
        result = run_git_command(
            ["for-each-ref", "--format=%(refname:short)", "refs/heads/"],
            git_dir
        )
        for branch in result.stdout.strip().split('\n'):
            if branch:
                local_branches.add(branch)
    except:
        pass

    # Categorize branches
    worktree_list = sorted([b for b in branches if b in worktree_branches])
    local_no_worktree_list = sorted([b for b in branches if b in local_branches and b not in worktree_branches])
    remote_only_list = sorted([b for b in branches if b not in local_branches])

    # Output in order: worktrees, local branches, remote branches
    for branch in worktree_list:
        print(branch)
    for branch in local_no_worktree_list:
        print(branch)
    for branch in remote_only_list:
        print(branch)


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


    # Create a 'repo' subcommand
    repo_parser = subparsers.add_parser("repo", help="Set or show the git directory")
    repo_parser.add_argument("git_dir", nargs="?", help="Path to the git directory (omit to show current)")

    # Create a 'switch' subcommand with 's' as alias
    switch_parser = subparsers.add_parser(
        "switch", aliases=["s"], help="Switch to or create branch worktree"
    )
    switch_parser.add_argument("branch_name", help="Name of the branch to switch to")
    switch_parser.add_argument(
        "-c", "--create", 
        action="store_true",
        help="Create a new branch before switching"
    )
    switch_parser.add_argument(
        "-C", "--force-create",
        action="store_true", 
        help="Create a new branch, resetting if it exists"
    )
    switch_parser.add_argument(
        "--guess", "--no-guess",
        dest="guess",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Guess remote branch names (default: enabled)"
    )

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
        choices=["all", "local", "worktrees"],
        nargs="?",
        const="all",
        help="List branch names for completion (default: all)"
    )
    list_parser.add_argument(
        "--git-dir", help="Explicitly specify the git directory (for tab completion)"
    )

    # New flags
    list_parser.add_argument("--raw", action="store_true", help="Show raw `git worktree list` output")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed warnings (if any)")
    list_parser.add_argument("--no-warn", action="store_true", help="Suppress warnings")
    list_parser.add_argument("--status", action="store_true", help="Show '!' marker for dirty worktrees (slower)")
    list_parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Colorize output: auto (default), always, or never"
    )
    list_parser.add_argument("--absolute", action="store_true", help="Show absolute paths instead of relative")

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
    if args.command == "repo":
        # Just print a message for the shell script to handle
        print(f"GWT_GIT_DIR={args.git_dir}")
    elif args.command in ["switch", "s"]:
        switch_branch(
            args.branch_name, 
            git_dir,
            create=getattr(args, "create", False),
            force_create=getattr(args, "force_create", False),
            guess=getattr(args, "guess", True)
        )
    elif args.command in ["remove", "rm"]:
        remove_worktree(args.branch_name, git_dir)
    elif args.command in ["list", "ls", "l"]:
        if hasattr(args, "branches") and args.branches:
            list_all_branches(git_dir, mode=args.branches)
        else:
            list_worktrees(
                git_dir,
                branches_only=False,
                raw=getattr(args, "raw", False),
                verbose=getattr(args, "verbose", False),
                no_warn=getattr(args, "no_warn", False),
                show_status=getattr(args, "status", False),
                color=getattr(args, "color", "auto"),
                absolute=getattr(args, "absolute", False),
            )


if __name__ == "__main__":
    main()
