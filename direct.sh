#!/usr/bin/env bash
# UserPromptSubmit hook: a prompt that is exactly `ag <args>` on one line runs
# the CLI here, and the output is shown to the user. The prompt is blocked, so
# the model is never called and nothing enters the context (the `reason` of a
# blocked prompt is shown to the user, not added to context).
#   direct.sh        hook mode (stdin = hook JSON)
#   direct.sh owns   exit 0 if the prompt on stdin is one this hook takes
#                    (digest.sh skips those, they never reach the model)
# Commands that need a terminal (prompts, sudo, a new seat) are not run: the
# hook says to run them in a shell. Long ag-rag runs go to the background.
# Needs jq; silent no-op without. Kill switches: LEX_CLAUDE_DISABLE=1,
# LEX_CLAUDE_DIRECT_DISABLE=1.

if [ "${LEX_CLAUDE_DISABLE:-}" = "1" ] || [ "${LEX_CLAUDE_DIRECT_DISABLE:-}" = "1" ]; then
  [ "${1:-}" = "owns" ] && exit 1
  exit 0
fi

# One line: `ag [args]` or `/ag [args]` (the hook sees slash prompts before the
# skill expands; bare `/ag` means doctor, like the ag skill). Prints the command
# line to run. Leading/trailing blanks are ignored.
owns() {
  local p="$1"
  case "$p" in *$'\n'*) return 1 ;; esac
  p="${p#"${p%%[![:space:]]*}"}"; p="${p%"${p##*[![:space:]]}"}"
  case "$p" in
    /ag) printf 'ag doctor' ;;
    ag|"ag "*) printf '%s' "$p" ;;
    "/ag "*) printf '%s' "${p#/}" ;;
    *) return 1 ;;
  esac
}

if [ "${1:-}" = "owns" ]; then
  owns "$(cat)" >/dev/null
  exit
fi

command -v jq >/dev/null 2>&1 || exit 0
prompt=$(jq -r '.prompt // empty' 2>/dev/null)
line=$(owns "$prompt") || exit 0

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
AG="$SELF_DIR/bin/lex-claude"

block() {
  jq -n --arg r "$1" \
    '{decision:"block",reason:$r,hookSpecificOutput:{hookEventName:"UserPromptSubmit",suppressOriginalPrompt:true}}'
  exit 0
}

[ -x "$AG" ] || block "ag: $AG not found. Run 'lex-claude install'."

# xargs splits like a shell (quotes kept together) without eval. The prompt is
# one line, so one argument per output line is lossless.
args=()
rest="${line#ag}"
if [ -n "$rest" ]; then
  list=$(printf '%s' "$rest" | xargs -n1 printf '%s\n' 2>/dev/null) \
    || block "ag: cannot parse the arguments (unbalanced quote?)."
  while IFS= read -r a; do args+=("$a"); done <<< "$list"
fi

terminal() { block "ag ${args[*]}: needs a terminal. Run it in a shell."; }
case "${args[0]:-}" in
  install|claude|github-login) terminal ;;
  codex) [[ " ${args[*]} " == *" --print "* ]] || terminal ;;
  model) [ "${args[1]:-}" = "list" ] && terminal ;;
  awake) [[ " ${args[*]} " == *" --lid "* ]] && terminal ;;
  rag)
    case "${args[1]:-}" in
      update|index|embed)
        log="$HOME/.claude/lex-claude/state/direct/rag-$(date +%Y%m%dT%H%M%S).log"
        mkdir -p "$(dirname "$log")" 2>/dev/null || block "ag rag: cannot create $(dirname "$log")"
        nohup "$AG" "${args[@]}" </dev/null >"$log" 2>&1 &
        block "ag ${args[*]}: running in the background (pid $!). Log: $log"
        ;;
      serve) terminal ;;
    esac
    ;;
esac

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || true
out=$("$AG" ${args[@]+"${args[@]}"} </dev/null 2>&1); rc=$?
[ $rc -eq 0 ] || out="$out
(exit $rc)"
block "$out"
