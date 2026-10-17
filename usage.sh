#!/usr/bin/env bash
# usage.sh — record which lex-claude capabilities actually get used, so dead
# commands and skills can be cut with data instead of a guess. Three modes:
#   log <source> <name>   append one event (called by the ag + pkgdev dispatchers)
#   hook                  PreToolUse stdin → log the Skill that fired
#   report                tally the log, flag the never-used surface
# Log is append-only at ~/.claude/lex-claude/usage.log (override LEX_CLAUDE_USAGE_LOG).
# Kill switch: LEX_CLAUDE_DISABLE=1 or LEX_CLAUDE_NO_USAGE=1 → silent no-op.
# Best-effort throughout: a logging failure must never break the calling command.
set -uo pipefail

LOG="${LEX_CLAUDE_USAGE_LOG:-$HOME/.claude/lex-claude/usage.log}"
INSTALL_DIR="$HOME/.claude/lex-claude"

# Canonical surface. Kept in step with the dispatchers and the skills dir.
CLI_CMDS="install update identity rules model lang skip github-login awake codex doctor version usage"
PKG_CMDS="run quick status release"

disabled() { [ "${LEX_CLAUDE_DISABLE:-}" = "1" ] || [ "${LEX_CLAUDE_NO_USAGE:-}" = "1" ]; }

human_date() {
  # epoch -> YYYY-MM-DD, BSD (date -r) and GNU (date -d @) both.
  date -r "$1" +%Y-%m-%d 2>/dev/null || date -d "@$1" +%Y-%m-%d 2>/dev/null || echo '?'
}

append() {
  disabled && return 0
  local src="${1:-}" name="${2:-}"
  [ -n "$src" ] && [ -n "$name" ] || return 0
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || return 0
  printf '%s\t%s\t%s\n' "$(date +%s)" "$src" "$name" >> "$LOG" 2>/dev/null || true
}

mode_hook() {
  # PreToolUse for the Skill tool. stdin is the hook JSON; pull the skill name.
  disabled && exit 0
  command -v jq >/dev/null 2>&1 || exit 0
  local input name
  input=$(cat)
  name=$(printf '%s' "$input" | jq -r '.tool_input.skill // .tool_input.command // empty' 2>/dev/null)
  [ -n "$name" ] && append skill "$name"
  exit 0
}

known_skills() {
  local d
  for d in "$INSTALL_DIR"/skills/*/; do
    [ -d "$d" ] || continue
    basename "$d"
  done | tr '\n' ' '
}

report_section() {
  local src="$1" title="$2" known="$3"
  echo
  echo "$title"
  local counts
  counts=$(awk -F'\t' -v s="$src" '$2==s{c[$3]++} END{for(k in c) printf "%6d  %s\n", c[k], k}' "$LOG" 2>/dev/null | sort -rn)
  if [ -n "$counts" ]; then
    echo "  used:"
    printf '%s\n' "$counts" | sed 's/^/  /'
  else
    echo "  used: (none yet)"
  fi
  local seen never="" k
  seen=$(awk -F'\t' -v s="$src" '$2==s{print $3}' "$LOG" 2>/dev/null | sort -u)
  for k in $known; do
    printf '%s\n' "$seen" | grep -qx "$k" || never="$never $k"
  done
  if [ -n "$never" ]; then
    echo "  never used (debloat candidates):"
    for k in $never; do echo "    $k"; done
  fi
}

mode_report() {
  if [ ! -s "$LOG" ]; then
    echo "usage: no events logged yet ($LOG)"
    echo "events accrue as you run ag/pkgdev commands and invoke skills."
    return 0
  fi
  local total first
  total=$(wc -l < "$LOG" | tr -d ' ')
  first=$(head -1 "$LOG" | cut -f1)
  echo "usage since $(human_date "$first") ($total events) — $LOG"
  report_section cli     "cli commands" "$CLI_CMDS"
  report_section pkgdev "pkgdev"        "$PKG_CMDS"
  report_section skill   "skills"       "$(known_skills)"
}

case "${1:-}" in
  log)    shift; append "$@" ;;
  hook)   mode_hook ;;
  report) mode_report ;;
  *)      echo "usage.sh: log <source> <name> | hook | report" >&2; exit 1 ;;
esac
