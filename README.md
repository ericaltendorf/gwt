# Git Worktree Tool (gwt)

(this is very new untested code -- please report bugs)

An opinionated tool for rapidly working in git worktrees.  `gwt` makes
it fast and easy to:

- See all existing branch+worktrees in the current repo

  `gwt` or `gwt list` or `gwt ls`

- Change directory to a branch+worktree [in the current repo]

  `gwt switch branch-name` or `gwt s branch-name` 
  
  (supports tab completion of existing branch+worktrees)

- Create a new branch+worktree [in the current repo]

  `gwt new branch-name`

- Remove a worktree and optionally its branch

  `gwt remove branch-name` or `gwt rm branch-name`

- Switch to a different repo

  `gwt repo /some/other/repo.git`

The "current repo" is stored in `$GWT_GIT_DIR` and a default value
can be initialized in your `.bashrc`.

### TODO

- Allow registration of setup scripts for new worktrees (e.g.,
  create `.env` files, install `node`, etc.)

## Background: bare repositories

`gwt` is designed to work with bare repositories and follows a convention for directory
layout to make worktree management easier:

- If your repo is at `/path/to/repo.git` (bare repo)
- Worktrees are stored at `/path/to/repo.gwt/branch-name`

This separation keeps Git's internal data (`.git`) separate from your working files
while maintaining a clear relationship between repositories and their worktrees.

Bare repos are the cleanest way to use worktrees. Clone with `--bare`, then 
set up remote tracking: `cd` into the repo, and run the following
([further reading](https://morgan.cugerone.com/blog/workarounds-to-git-worktree-using-bare-repository-and-cannot-fetch-remote-branches/)).

```bash
git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
```

managing git worktrees with a Bash integration for directory changing.

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

## Configuration

Setup allowed you to set a default `GWT_GIT_DIR` so that new
shells will automatically know where your repo lives.  You
can re-set that dir manually or using `gwt` itself:

```bash
# Method 1: Set it directly in the shell
export GWT_GIT_DIR=/path/to/your/repo.git

# Method 2: Use the built-in command
gwt repo /path/to/your/repo.git
```


## Usage

List all worktrees:
```
gwt
gwt list
gwt ls
```

Create a new branch and worktree:
```
gwt new branch-name
```

Switch to an existing worktree:
```
gwt switch branch-name
gwt s branch-name
```

Set the git directory for future commands:
```
gwt repo /path/to/another/repo.git
```

Remove a worktree and optionally its branch:
```
gwt remove branch-name
gwt rm branch-name
```

## How it works

The installation combines a Python script (`gwt.py`) that handles the git operations with a Bash script (`gwt.sh`) that handles directory changing and tab completion. This approach minimizes what needs to be added to `.bashrc` while maintaining full functionality.