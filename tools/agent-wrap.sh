#!/usr/bin/env bash
set -euo pipefail

MODE="${OUTPUT_MODE:-normal}"

# Build argument array so we can tweak flags per tool
args=("$@")

# Determine base command (uvx passthrough)
cmd="${args[0]}"
subcmd=""
if [[ "$cmd" == "uvx" && ${#args[@]} -ge 2 ]]; then
  subcmd="${args[1]}"
fi

# Adjust flags for pytest and ruff based on OUTPUT_MODE
maybe_adjust_args() {
  if [[ "$subcmd" == "pytest" || "$cmd" == "pytest" ]]; then
    if [[ "$MODE" == "minimal" || "$MODE" == "json" ]]; then
      args+=("-q")
    elif [[ "$MODE" == "verbose" ]]; then
      args+=("-vv")
    fi
  fi

  # ruff check can emit json; leave ruff format alone
  if [[ "$subcmd" == "ruff" || "$cmd" == "ruff" ]]; then
    if [[ "$MODE" == "json" ]]; then
      # Only add JSON for the 'check' subcommand if not already present
      for i in "${!args[@]}"; do
        if [[ "${args[$i]}" == "check" ]]; then
          # ensure no duplicate flag
          if ! printf '%s\0' "${args[@]}" | grep -z -- "--output-format" >/dev/null 2>&1; then
            args+=("--output-format" "json")
          fi
        fi
      done
    fi
  fi
}

maybe_adjust_args

if [[ "$MODE" == "minimal" ]]; then
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  if "${args[@]}" >"$tmp" 2>&1; then
    # Success: stay quiet for token efficiency
    exit 0
  else
    # Failure: show only the tail to keep output concise
    tail -n 200 "$tmp" || true
    exit 1
  fi
else
  # normal/json/verbose: passthrough
  exec "${args[@]}"
fi
