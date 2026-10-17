#!/usr/bin/env bash
# Nightly incremental ag-rag update, run by launchd. Skips if an indexer is already running.
set -uo pipefail
LOG="$HOME/.local/share/ag-rag/nightly.log"
mkdir -p "$(dirname "$LOG")"
UV="$(command -v uv || echo /opt/homebrew/bin/uv)"
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') nightly update"
  if pgrep -f 'ag_rag.py (update|embed|index)' >/dev/null; then
    echo "an index run is already active; skipping"
    exit 0
  fi
  if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "ollama not reachable; keyword index only"
    /usr/bin/caffeinate -i "$UV" run -q "$(dirname "$0")/ag_rag.py" index --prune
  else
    /usr/bin/caffeinate -i "$UV" run -q "$(dirname "$0")/ag_rag.py" update --prune --minutes 240
  fi
  echo "=== exit $?"
} >> "$LOG" 2>&1
