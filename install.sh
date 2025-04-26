#!/bin/bash

set -e

# Default paths
BIN_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

# Copy scripts to bin directory
cp "$SCRIPT_DIR/gwt.py" "$BIN_DIR/gwt.py"
cp "$SCRIPT_DIR/gwt.sh" "$BIN_DIR/gwt.sh"
chmod +x "$BIN_DIR/gwt.py"
chmod +x "$BIN_DIR/gwt.sh"

# Ask for default GWT_GIT_DIR
echo "Enter default GWT_GIT_DIR (optional, press Enter to skip):"
read -r default_git_dir

# Check if .bashrc already has gwt setup
if grep -q "source.*gwt.sh" ~/.bashrc; then
  echo "gwt already appears to be set up in .bashrc"
else
  echo -e "\n# GWT setup" >> ~/.bashrc
  echo "source \"$BIN_DIR/gwt.sh\"" >> ~/.bashrc
  
  # Add default GWT_GIT_DIR if provided
  if [ -n "$default_git_dir" ]; then
    echo "export GWT_GIT_DIR=\"$default_git_dir\"" >> ~/.bashrc
  fi
fi

echo -e "\nInstallation complete!"
echo "Please run 'source ~/.bashrc' or start a new terminal to use gwt."

if [ -n "$default_git_dir" ]; then
  echo "Default GWT_GIT_DIR has been set to: $default_git_dir"
else
  echo "Remember to set GWT_GIT_DIR before using gwt:"
  echo "  gwt --set-git-dir /path/to/your/repo.git"
fi