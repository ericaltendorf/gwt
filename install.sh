#!/bin/bash

set -e

# Default paths
BIN_DIR="${HOME}/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Create bin directory if it doesn't exist
mkdir -p "$BIN_DIR"

# Check for required Python packages
echo "Checking for required Python packages..."
HAS_TOML=0
if python3 -c "import tomli, tomli_w" 2>/dev/null; then
  HAS_TOML=1
else
  echo "Warning: Required Python packages 'tomli' and 'tomli-w' are not installed."
  echo "For full functionality, please install them:"
  echo "  pip install tomli tomli-w"
  echo "GWT will still work without these packages, but configuration features"
  echo "like default repository and post-create commands will be disabled."
  echo
fi

# Create config directory and file if they don't exist
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/gwt"
CONFIG_FILE="$CONFIG_DIR/config.toml"

if [ $HAS_TOML -eq 1 ]; then
  echo "Setting up configuration directory at $CONFIG_DIR"
  mkdir -p "$CONFIG_DIR"
  
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default config file at $CONFIG_FILE"
    cat > "$CONFIG_FILE" << EOL
# GWT Configuration

# Default repository to use if GWT_GIT_DIR env var isn't set
# default_repo = "/path/to/your/repo.git"

# Example repository-specific configurations
# [repos."/path/to/your/repo.git"]
# post_create_commands = [
#   "npm install",
#   "echo 'Worktree setup complete!'"
# ]
EOL
  fi
fi

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
    
    # Also update the config file if we have TOML support
    if [ $HAS_TOML -eq 1 ] && [ -f "$CONFIG_FILE" ]; then
      echo "Adding default repository to config file..."
      # Use Python to update the config file properly
      python3 -c "
import tomli, tomli_w
with open('$CONFIG_FILE', 'rb') as f:
  config = tomli.load(f)
config['default_repo'] = '$default_git_dir'
with open('$CONFIG_FILE', 'wb') as f:
  tomli_w.dump(config, f)
" 2>/dev/null || {
        # If Python fails, just modify the file directly (less robust but better than nothing)
        sed -i "s|# default_repo.*|default_repo = \"$default_git_dir\"|" "$CONFIG_FILE"
      }
    fi
  fi
fi

echo -e "\nInstallation complete!"
echo "Please run 'source ~/.bashrc' or start a new terminal to use gwt."

if [ -n "$default_git_dir" ]; then
  echo "Default GWT_GIT_DIR has been set to: $default_git_dir"
else
  echo "Remember to set GWT_GIT_DIR before using gwt:"
  echo "  gwt --repo /path/to/your/repo.git"
fi