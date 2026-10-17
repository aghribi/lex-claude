#!/usr/bin/env bash
# FileChanged/SessionStart helper for lex-claude. Companion to hook.sh.
#   SessionStart: emits watchPaths for the loaded global config (active identity
#                 symlink + its resolved target + the lang file).
#   FileChanged:  emits a staleness systemMessage. Claude Code does NOT re-inject
#                 additionalContext on FileChanged (verified against the binary:
#                 the FileChanged handler only forwards watchPaths + systemMessages),
#                 so the honest ceiling is a "your loaded rules are stale, reload" nudge.
# Watched surface is deliberately narrow: only config that changes on an explicit
# `ag identity` / `ag rules sync` / `ag lang`. Project CLAUDE.md and docs are edited
# constantly; nudging on every save would be noise.
# Kill switch: LEX_CLAUDE_DISABLE=1 → silent no-op. Needs jq; no-op without it.

[ "${LEX_CLAUDE_DISABLE:-}" = "1" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
event=$(printf '%s' "$input" | jq -r '.hook_event_name // empty' 2>/dev/null)

case "$event" in
  SessionStart)
    paths=()
    link="$HOME/.claude/CLAUDE.md"
    [ -e "$link" ] && paths+=("$link")
    tgt=$(readlink "$link" 2>/dev/null || true)
    [ -n "$tgt" ] && [ -e "$tgt" ] && [ "$tgt" != "$link" ] && paths+=("$tgt")
    lang="$HOME/.claude/lex-claude/.lang"
    [ -f "$lang" ] && paths+=("$lang")
    [ ${#paths[@]} -eq 0 ] && exit 0
    printf '%s\n' "${paths[@]}" | jq -R . \
      | jq -s '{hookSpecificOutput:{hookEventName:"SessionStart",watchPaths:.}}'
    ;;
  FileChanged)
    fp=$(printf '%s' "$input" | jq -r '.file_path // empty' 2>/dev/null)
    name=$(basename "${fp:-a lex-claude config file}")
    jq -n --arg f "$name" \
      '{systemMessage:("lex-claude: " + $f + " changed. The identity/rules loaded in this session are now stale; run /clear or restart to reload them.")}'
    ;;
esac
