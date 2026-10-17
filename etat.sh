#!/usr/bin/env bash
# etat.sh — the SessionStart floor: active identity (as a verifiable fact, from
# the symlink) + live git state. This is the état the opener reports and the
# master verifies against.
#
#   etat.sh start   inject the identity + git readout at SessionStart.
# Kill switch: LEX_CLAUDE_DISABLE=1.

[ "${LEX_CLAUDE_DISABLE:-}" = "1" ] && exit 0

# Memory slug = cwd with every "/", "." and space collapsed to "-" (same shape
# memory.py and the ag-close skill use).
slug_of() { printf '%s' "$1" | sed -e 's#[/. ]#-#g'; }

# Active identity as a fact, not an assertion: resolve the ~/.claude/CLAUDE.md
# symlink (same source as the statusline) so the opener can verify who it is —
# and so a broken/hand-written/mispointed link gets caught on turn one.
identity_state() {
  local link="$HOME/.claude/CLAUDE.md" tgt name
  if [ -L "$link" ]; then
    tgt=$(readlink "$link" 2>/dev/null)
    name=$(basename "$tgt" .md 2>/dev/null)
    if [ ! -e "$link" ]; then
      echo "identity: ${name:-?} (BROKEN symlink → $tgt)"
    elif [ -n "$name" ]; then
      echo "identity: $name"
    else
      echo "identity: ? (unreadable symlink → $tgt)"
    fi
  elif [ -f "$link" ]; then
    echo "identity: unmanaged (CLAUDE.md is a real file, not an ag symlink)"
  else
    echo "identity: none (no ~/.claude/CLAUDE.md)"
  fi
}

git_state() {
  local d="$1"
  git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "not a git repo"; return 0; }
  local br sha dirty ahead last
  br=$(git -C "$d" branch --show-current 2>/dev/null); [ -n "$br" ] || br="(detached)"
  sha=$(git -C "$d" rev-parse --short HEAD 2>/dev/null || echo "?")
  dirty=$(git -C "$d" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  ahead=$(git -C "$d" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "?")
  last=$(git -C "$d" log -1 --format='%s (%cr)' 2>/dev/null || echo "none")
  echo "branch: $br @ $sha | dirty: $dirty | unpushed: $ahead | last commit: $last"
}

case "${1:-}" in
  start)
    d="${CLAUDE_PROJECT_DIR:-$PWD}"
    printf '\n===== état (live) =====\n%s\n%s\n' "$(identity_state)" "$(git_state "$d")"
    # Persistent project memory recall (live subset, salience-ranked). Fast, no
    # LLM, no embeddings: pure ranking over the stored items. Fail-open.
    MEM="$HOME/.claude/lex-claude/memory.py"
    if [ "${LEX_CLAUDE_MEMORY_DISABLE:-}" != "1" ] && command -v python3 >/dev/null 2>&1 && [ -f "$MEM" ]; then
      mem=$(python3 "$MEM" recall "$(slug_of "$d")" 2>/dev/null || true)
      [ -n "$mem" ] && printf '\n%s\n' "$mem"
    fi
    ;;
  *)
    echo "usage: etat.sh start" >&2
    exit 1
    ;;
esac
