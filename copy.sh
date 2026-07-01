#!/bin/bash
# Copies a paste-ready embed fragment to the macOS clipboard.
#   ./copy.sh            -> flat single-column layout (embed.html)
#   ./copy.sh sections   -> US / Global sectioned layout (embed_sections.html)
set -euo pipefail
DIR="/Users/filitti/Downloads/jew-hatred-today"

case "${1:-flat}" in
  sections|split|us-global) FILE="embed_sections.html" ;;
  *)                        FILE="embed.html" ;;
esac

pbcopy < "$DIR/public/$FILE"
echo "Copied public/$FILE to the clipboard."
echo "Now paste it into your Squarespace Code Block and Save."
