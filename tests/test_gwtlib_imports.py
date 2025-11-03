def test_gwtlib_imports():
    """Ensure gwtlib modules import without circular dependencies."""
    import gwtlib.config
    import gwtlib.git_ops
    import gwtlib.paths
    import gwtlib.branches
    import gwtlib.parsing
    import gwtlib.display
    import gwtlib.worktrees
    import gwtlib.resolution
    import gwtlib.cli
    assert True
