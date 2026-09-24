#!/usr/bin/env bash

# TPM sources plugin entry points as shell scripts.
PLUGIN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
NOTIFY_SCRIPT="$PLUGIN_DIR/scripts/codex_tmux_notify.py"

python3 "$NOTIFY_SCRIPT" install "$PLUGIN_DIR"
