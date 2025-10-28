import contextlib
import os
from pathlib import Path

import gwt


def test_get_worktree_base_nonbare_creates_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    git_dir = str(repo / ".git")

    base = gwt.get_worktree_base(git_dir)
    assert base.endswith(".gwt")
    base_path = Path(base)
    assert base_path.exists()
    assert (base_path / "README.md").exists()


def test_rel_display_path_main_vs_gwt(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    git_dir = str(repo / ".git")

    # main path should be absolute
    main_path = gwt.get_main_worktree_path(git_dir)
    assert main_path is not None
    abs_disp = gwt.rel_display_path(main_path, git_dir, force_absolute=False)
    assert abs_disp == os.path.abspath(main_path)

    # gwt path should be relative when inside base
    base = gwt.get_worktree_base(git_dir)
    wt = Path(base) / "feature"
    wt.mkdir(parents=True)
    rel_disp = gwt.rel_display_path(str(wt), git_dir, force_absolute=False)
    # Relative to parent of base
    assert not rel_disp.startswith(str(tmp_path))


def test_is_path_current_worktree(tmp_path, monkeypatch):
    target = tmp_path / "here"
    target.mkdir()
    with contextlib.ExitStack() as stack:
        stack.enter_context(monkeypatch.context())
        monkeypatch.chdir(target)
        assert gwt.is_path_current_worktree(str(target))
        assert not gwt.is_path_current_worktree(str(tmp_path / "other"))
