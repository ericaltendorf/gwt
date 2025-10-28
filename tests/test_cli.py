import os
import subprocess
import sys
from pathlib import Path


def _run_cli(tmp_path, args, env=None, input_bytes=None):
    cmd = [sys.executable, "gwt.py"] + args
    e = os.environ.copy()
    e["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    if env:
        e.update(env)
    return subprocess.run(cmd, env=e, input=input_bytes, capture_output=True, text=True)


def _init_repo(repo: Path):
    subprocess.run(
        ["git", "init", str(repo)], check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test User"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_cli_repo_sets_env_line(tmp_path):
    # Provide any dir; tool will echo GWT_GIT_DIR=...
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    res = _run_cli(tmp_path, ["repo", str(repo)])
    assert res.returncode == 0
    assert "GWT_GIT_DIR=" in res.stdout


def test_cli_list_branches_only_local(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    env = {"GWT_GIT_DIR": str(repo / ".git")}
    # Create a branch
    subprocess.run(["git", "-C", str(repo), "branch", "feature"], check=True)
    res = _run_cli(tmp_path, ["list", "--branches", "local"], env=env)
    assert res.returncode == 0
    # stdout prints branches
    out = res.stdout.strip().splitlines()
    # At minimum, expect current branch and feature
    assert "feature" in out


def test_cli_switch_no_guess_missing_branch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    env = {"GWT_GIT_DIR": str(repo / ".git")}
    # No such branch, and --no-guess
    res = _run_cli(tmp_path, ["switch", "--no-guess", "does-not-exist"], env=env)
    assert res.returncode != 0
    assert "invalid reference" in res.stderr


def test_cli_remove_flow(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    env = {"GWT_GIT_DIR": str(repo / ".git")}
    # Create branch & worktree using the CLI path
    subprocess.run(["git", "-C", str(repo), "branch", "feature"], check=True)
    # Use the module function to add the worktree to keep this faster
    import gwt as g

    wt_base = g.get_worktree_base(env["GWT_GIT_DIR"])
    wt_path = os.path.join(wt_base, "feature")
    g.create_worktree_for_branch("feature", env["GWT_GIT_DIR"], wt_path)

    # Remove via CLI and decline branch deletion
    res = _run_cli(tmp_path, ["remove", "feature"], env=env, input_bytes="n\n")
    assert res.returncode == 0
    assert "removed" in res.stdout or "removed" in res.stderr
