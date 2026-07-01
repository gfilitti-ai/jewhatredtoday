#!/bin/bash
# Generates the page. Called by launchd every 4 hours (and runnable by hand).
set -euo pipefail

DIR="/Users/filitti/Downloads/jew-hatred-today"
cd "$DIR"

# Load ANTHROPIC_API_KEY (and anything else) from .env if present.
if [ -f "$DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$DIR/.env"
  set +a
fi

echo "===== $(date) ====="
"$DIR/venv/bin/python" generate.py
echo "done"
