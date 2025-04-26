# Git Worktree Wrapper (gwt)

A simple Python wrapper for managing git worktrees with a Bash integration for directory changing.

## Configuration

Before using gwt, you need to set the `GWT_GIT_DIR` environment variable to point to your git repository:

```bash
# Method 1: Set it directly in the shell
export GWT_GIT_DIR=/path/to/your/repo.git

# Method 2: Use the built-in command
gwt --set-git-dir /path/to/your/repo.git
```

## Installation

### Automatic Installation

Run the installation script:

```bash
./install.sh
```

This will:
1. Copy the scripts to your `~/.local/bin/` directory
2. Ask for an optional default GWT_GIT_DIR
3. Add the necessary lines to your `~/.bashrc`

Then reload your shell:
```bash
source ~/.bashrc
```

### Manual Installation

If you prefer to install manually:

1. Make sure Python 3.6+ is installed on your system

2. Copy the scripts to a directory in your PATH:
   ```bash
   mkdir -p ~/.local/bin
   cp gwt.py gwt.sh ~/.local/bin/
   chmod +x ~/.local/bin/gwt.py ~/.local/bin/gwt.sh
   ```

3. Add to your `~/.bashrc`:
   ```bash
   # GWT setup
   source ~/.local/bin/gwt.sh
   export GWT_GIT_DIR=/path/to/your/repo.git  # Optional default
   ```

4. Reload your shell:
   ```bash
   source ~/.bashrc
   ```

## Usage

List all worktrees:
```
gwt
```

Create a new branch and worktree:
```
gwt -a new-branch-name
```

Switch to an existing worktree:
```
gwt branch-name
```

Set the git directory for future commands:
```
gwt --set-git-dir /path/to/another/repo.git
```

## How it works

The installation combines a Python script (`gwt.py`) that handles the git operations with a Bash script (`gwt.sh`) that handles directory changing and tab completion. This approach minimizes what needs to be added to `.bashrc` while maintaining full functionality.