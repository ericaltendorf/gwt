# gwtlib/api.py
from gwtlib.paths import (
    get_worktree_base,
    get_main_worktree_path,
    is_path_current_worktree,
    rel_display_path,
)
from gwtlib.worktrees import create_worktree_for_branch
from gwtlib.branches import branch_exists_locally
from gwtlib.parsing import (
    parse_worktree_porcelain,
    parse_worktree_legacy,
    get_worktree_list,
)
from gwtlib.resolution import auto_detect_git_dir
from gwtlib.display import ColorMode

__all__ = [
    # paths
    "get_worktree_base",
    "get_main_worktree_path",
    "is_path_current_worktree",
    "rel_display_path",
    # worktrees
    "create_worktree_for_branch",
    # branches
    "branch_exists_locally",
    # parsing
    "parse_worktree_porcelain",
    "parse_worktree_legacy",
    "get_worktree_list",
    # resolution
    "auto_detect_git_dir",
    # display
    "ColorMode",
]
