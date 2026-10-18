#!/usr/bin/env bash
# SessionStart hook — loads global identity + project docs into context.
# Wire it via ~/.claude/settings.json (see README).
# Kill switch: LEX_CLAUDE_DISABLE=1 → exit early without touching context.
# Heartbeat: writes ~/.claude/lex-claude/.last-hook (epoch) on successful run, for outside observability.

[ "${LEX_CLAUDE_DISABLE:-}" = "1" ] && exit 0

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
LEX_CLAUDE_CONTEXT_MODE="${LEX_CLAUDE_CONTEXT_MODE:-full}"

# Global ~/.claude/CLAUDE.md is auto-loaded into context by Claude Code itself
# (the `claudeMd` system-reminder). Re-dumping it here only inflated the hook
# output past the truncation limit, which cut off the acknowledgement
# instruction at the bottom. Skip it; just name it so the ack can reference it.
printf '\n===== global identity =====\nGlobal ~/.claude/CLAUDE.md is already loaded in context (no need to re-read).\n'

# Session état: active identity (verifiable fact) + live git. Injected before the
# docs so a truncated bundle still carries the state. Succession happens live
# near the token limit (succeed.sh).
ETAT_SH="$SELF_DIR/etat.sh"
[ -f "$ETAT_SH" ] && bash "$ETAT_SH" start

project_files="CLAUDE.md"
if [ "$LEX_CLAUDE_CONTEXT_MODE" != "lite" ]; then
  project_files="$project_files docs/PHILOSOPHY.md docs/CONTEXT.md docs/PRINCIPLES.md docs/INVARIANTS.md docs/OPS.md docs/TODO.md"
fi

for f in $project_files; do
  p="${CLAUDE_PROJECT_DIR:-$PWD}/$f"
  if [ -f "$p" ]; then
    printf '\n===== %s =====\n' "$f"
    cat "$p"
  fi
done

# A pointer, not the reference itself: the full list costs ~1.4k tokens every
# session and is rarely needed.
printf '\n===== lex-claude commands (ag) =====\n`ag` (alias of `lex-claude`) manages identities, rules, hooks, skills, model, lang and the ag-rag index. Run `ag init claude` for the command reference before using it. A prompt that is exactly `ag <args>` or `/ag <args>` runs in a hook and never reaches you.\n'

LEX_CLAUDE_LANG_FILE="$HOME/.claude/lex-claude/.lang"
if [ -f "$LEX_CLAUDE_LANG_FILE" ]; then
  lang=$(cat "$LEX_CLAUDE_LANG_FILE" 2>/dev/null | tr -d '[:space:]')
  case "$lang" in
    en) printf '\n===== language =====\nRespond in English.\n' ;;
    fr) printf '\n===== language =====\nRespond in French.\n' ;;
  esac
fi

# The ack is an état readout the user can falsify at a glance, not ceremony.
# identity/rules loading is verified live (the master + the
# `ag claude` pre-flight), and work is handed to a fresh, verified successor near
# the token limit rather than persisted to a drift-prone file.
printf '\n---\nRules and docs above are loaded; do not recite them and do not list them back. Open with the état instead: name the active identity from the live block (flag it if it reads BROKEN / unmanaged / none) and the live git line, then the next step you propose, 3 lines max.\n'

sh -c 'date +%s > "$1"' sh "$HOME/.claude/lex-claude/.last-hook" 2>/dev/null || true
