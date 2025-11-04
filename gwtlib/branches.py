# gwtlib/branches.py
from gwtlib.git_ops import run_git_command, run_git_quiet


def get_main_branch_name(git_dir):
    """Extract the main branch name from git worktree list."""
    try:
        result = run_git_command(["worktree", "list"], git_dir)
        lines = result.stdout.splitlines()
        if lines:
            parts = lines[0].split()
            if len(parts) >= 3:
                return parts[2].strip("[]")
    except Exception:
        pass
    return None


def branch_exists_locally(branch_name, git_dir):
    """Check if a branch exists locally via git rev-parse."""
    try:
        run_git_quiet(["rev-parse", "--verify", f"refs/heads/{branch_name}"], git_dir)
        return True
    except Exception:
        return False


def find_remote_branch(branch_name, git_dir):
    """Search for remote branches matching given name, preferring origin."""
    run_git_command(["remote", "update"], git_dir)
    result = run_git_command(
        ["for-each-ref", "--format=%(refname:short)", f"refs/remotes/*/{branch_name}"],
        git_dir,
    )
    refs = [r for r in result.stdout.strip().split("\n") if r]
    if len(refs) == 1:
        return refs[0]
    elif len(refs) > 1:
        for ref in refs:
            if ref.startswith("origin/"):
                return ref
        return refs[0]
    return None
