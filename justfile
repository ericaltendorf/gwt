# Use bash with strict flags
set shell := ["bash", "-euo", "pipefail", "-c"]

# Always route commands through the OUTPUT_MODE-aware wrapper
WRAP := "tools/agent-wrap.sh"

# Default recipe
default: help

alias c := check
alias t := test
alias f := fmt
alias fc := fmt-check
alias l := lint
alias tc := type-check
alias b := build
alias i := install-local

help:
  @echo "gwt tooling commands:"
  @echo "  just check         # fmt-check, lint, type-check, test"
  @echo "  just fmt           # ruff format"
  @echo "  just fmt-check     # ruff format --check"
  @echo "  just lint          # ruff check (E,F,I)"
  @echo "  just type-check    # ty on gwt.py"
  @echo "  just test          # pytest"
  @echo "  just build         # create dist/gwt"
  @echo "  just install-local # symlink dist/gwt -> ~/.local/bin/gwt"
  @echo "  just clean         # remove build/test artifacts"
  @echo ""
  @echo "OUTPUT_MODE: minimal | json | normal | verbose"

# Formatting
fmt:
  {{WRAP}} uvx ruff format gwt.py

fmt-check:
  {{WRAP}} uvx ruff format --check gwt.py

# Linting with pragmatic rules (configured in pyproject)
lint:
  {{WRAP}} uvx ruff check gwt.py

# Type checking (Ty is alpha; only check main module)
# Using --exit-zero to tolerate errors since ty is alpha
type-check:
  {{WRAP}} uvx ty check gwt.py --exit-zero

# Test suite
test:
  {{WRAP}} uvx pytest

# Aggregate check
check:
  just fmt-check
  just lint
  just type-check
  just test

# Build single-file executable (uv shebang is already in gwt.py)
build:
  rm -rf dist
  mkdir -p dist
  cp gwt.py dist/gwt
  chmod +x dist/gwt
  @echo "Built dist/gwt"

# Install to ~/.local/bin (common on Linux/macOS)
install-local: build
  mkdir -p "$$HOME/.local/bin"
  ln -sfn "$(pwd)/dist/gwt" "$$HOME/.local/bin/gwt"
  @echo "Installed to $$HOME/.local/bin/gwt (symlink). Ensure $$HOME/.local/bin is in PATH."

# Clean artifacts
clean:
  rm -rf dist .pytest_cache __pycache__ **/__pycache__
