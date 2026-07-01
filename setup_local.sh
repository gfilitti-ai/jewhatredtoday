#!/bin/bash
# One-time local setup: create the venv, install deps, make scripts executable.
set -euo pipefail

DIR="/Users/filitti/Downloads/jew-hatred-today"
cd "$DIR"

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
chmod +x run.sh copy.sh

echo
echo "Setup complete."
echo "Next: put your key in .env  ->  echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env"
echo "Then test:  ./run.sh"
