#!/usr/bin/env bash
# UserPromptSubmit hook — re-inject a condensed rules digest every N prompts.
# The full rules land once at SessionStart and lose attention weight as the
# context grows; this keeps them salient without re-paying the full bundle
# (~15 lines every Nth prompt). stdout on UserPromptSubmit is appended to
# context by Claude Code.
#   Cadence: LEX_CLAUDE_DIGEST_EVERY (default 5, 0 = off).
#   Text:    DIGEST.md next to this script (hand-condensed from RULES.md).
#   State:   ~/.claude/lex-claude/.digest/<session_id> (prompt counter,
#            pruned after 7 days).
# Needs jq (session_id from hook stdin); silent no-op without.
# Kill switch: LEX_CLAUDE_DISABLE=1.

[ "${LEX_CLAUDE_DISABLE:-}" = "1" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

EVERY="${LEX_CLAUDE_DIGEST_EVERY:-5}"
case "$EVERY" in *[!0-9]*|"") exit 0 ;; esac
[ "$EVERY" -eq 0 ] && exit 0

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
DIGEST="$SELF_DIR/DIGEST.md"
[ -f "$DIGEST" ] || exit 0

input=$(cat)
# Prompts direct.sh runs never reach the model: they do not count.
printf '%s' "$input" | jq -r '.prompt // empty' 2>/dev/null | bash "$SELF_DIR/direct.sh" owns && exit 0

session=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
session=${session//[^A-Za-z0-9._-]/}
[ -n "$session" ] || exit 0

STATE_DIR="$HOME/.claude/lex-claude/.digest"
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
find "$STATE_DIR" -type f -mtime +7 -delete 2>/dev/null || true

state="$STATE_DIR/$session"
count=$(cat "$state" 2>/dev/null || echo 0)
case "$count" in *[!0-9]*|"") count=0 ;; esac
count=$((count + 1))
printf '%s\n' "$count" > "$state" 2>/dev/null || true

[ $((count % EVERY)) -eq 0 ] || exit 0

printf '===== lex-claude rules digest (periodic recall; full rules were loaded at session start) =====\n'
sed '/<!--/,/-->/d' "$DIGEST"   # strip the maintenance comment, no need to re-pay it every injection
