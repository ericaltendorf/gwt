def test_public_api_re_exports():
    """Validate gwt.py re-exports all test-used functions."""
    import gwt
    assert callable(gwt.get_worktree_base)
    assert callable(gwt.get_main_worktree_path)
    assert callable(gwt.is_path_current_worktree)
    assert callable(gwt.rel_display_path)
    assert callable(gwt.create_worktree_for_branch)
    assert callable(gwt.branch_exists_locally)
    assert callable(gwt.parse_worktree_porcelain)
    assert callable(gwt.parse_worktree_legacy)
    assert callable(gwt.get_worktree_list)
    assert callable(gwt.auto_detect_git_dir)
    assert hasattr(gwt, "ColorMode")
