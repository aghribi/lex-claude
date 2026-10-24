#!/usr/bin/env bash
# journal.sh: per-project work journal, <project>/_journal/ (STATUS.md, RESULTS.md,
# sessions/). Local to the project: the SessionStart hook injects STATUS.md only
# when the session runs inside a project that has a journal; nothing otherwise.
#
#   journal.sh start          SessionStart hook: STATUS.md (capped) + last session notes
#   journal.sh root [dir]     print the project folder holding _journal/ (nearest ancestor)
#   journal.sh init [dir]     create <dir>/_journal from the template (dir: default cwd)
#   journal.sh show           print STATUS.md of the current project
#   journal.sh check          line cap, last update, results without evidence
#   journal.sh all [root]     one line per journaled project under root
#                             (default $AG_WORKSPACE or ~/Documents/work_space)
#
# Cap: LEX_CLAUDE_JOURNAL_LINES (default 120 lines of STATUS.md injected).
# Kill switch: LEX_CLAUDE_DISABLE=1.

[ "${LEX_CLAUDE_DISABLE:-}" = "1" ] && exit 0

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SELF_DIR/templates/journal"
CAP="${LEX_CLAUDE_JOURNAL_LINES:-120}"
case "$CAP" in *[!0-9]*|"") CAP=120 ;; esac

die() { echo "journal: $*" >&2; exit 1; }

# Nearest ancestor of $1 (inclusive) with _journal/STATUS.md, stopping at $HOME and /.
root_of() {
  local d; d=$(cd "${1:-.}" 2>/dev/null && pwd) || return 1
  while [ -n "$d" ] && [ "$d" != "/" ] && [ "$d" != "$HOME" ]; do
    [ -f "$d/_journal/STATUS.md" ] && { printf '%s\n' "$d"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

last_sessions() {   # $1 = journal dir, $2 = count
  ls -1 "$1/sessions" 2>/dev/null | grep '\.md$' | sort | tail -n "$2"
}

case "${1:-}" in
  start)
    r=$(root_of "${CLAUDE_PROJECT_DIR:-$PWD}") || exit 0
    j="$r/_journal"; n=$(wc -l < "$j/STATUS.md" | tr -d ' ')
    printf '\n===== project journal: %s (%s/_journal) =====\n' "$(basename "$r")" "$r"
    head -n "$CAP" "$j/STATUS.md"
    [ "$n" -gt "$CAP" ] && printf '\n[STATUS.md has %s lines, over the %s-line cap: shown cut. Trim it at the next close.]\n' "$n" "$CAP"
    s=$(last_sessions "$j" 3)
    [ -n "$s" ] && printf '\nLast session notes (sessions/, read on demand):\n%s\n' "$(printf '%s\n' "$s" | sed 's/^/- /')"
    printf '\nThis project keeps a journal: update STATUS.md when a task ends, a result or a decision lands, or an issue appears; results go to RESULTS.md with their evidence; write a session note at close or handoff. Rules: _journal/README.md.\n'
    ;;

  root)
    root_of "${2:-$PWD}" || die "no _journal/ above ${2:-$PWD}"
    ;;

  init)
    d=$(cd "${2:-.}" 2>/dev/null && pwd) || die "no such folder: ${2:-.}"
    [ -e "$d/_journal" ] && die "$d/_journal already exists"
    [ -d "$TEMPLATE" ] || die "template missing: $TEMPLATE"
    mkdir -p "$d/_journal/sessions"
    cp "$TEMPLATE/README.md" "$TEMPLATE/RESULTS.md" "$d/_journal/"
    sed -e "s/^# PROJECT status/# $(basename "$d") status/" -e "s/YYYY-MM-DD/$(date +%F)/" "$TEMPLATE/STATUS.md" > "$d/_journal/STATUS.md"
    echo "created $d/_journal (STATUS.md, RESULTS.md, README.md, sessions/)"
    ;;

  show)
    r=$(root_of "$PWD") || die "no _journal/ above $PWD"
    cat "$r/_journal/STATUS.md"
    ;;

  check)
    r=$(root_of "${2:-$PWD}") || die "no _journal/ above ${2:-$PWD}"
    j="$r/_journal"; rc=0
    n=$(wc -l < "$j/STATUS.md" | tr -d ' ')
    if [ "$n" -gt "$CAP" ]; then echo "warn  STATUS.md: $n lines, cap $CAP"; rc=1; else echo "ok    STATUS.md: $n lines (cap $CAP)"; fi
    upd=$(grep -m1 -o '^Updated: [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' "$j/STATUS.md" | cut -c10-)
    if [ -z "$upd" ]; then echo "warn  STATUS.md: no 'Updated: YYYY-MM-DD' line"; rc=1
    else
      age=$(( ( $(date +%s) - $(date -j -f %F "$upd" +%s 2>/dev/null || date -d "$upd" +%s) ) / 86400 ))
      [ "$age" -gt 14 ] && { echo "warn  STATUS.md: updated $upd ($age days ago)"; rc=1; } || echo "ok    STATUS.md: updated $upd"
    fi
    # Each "## R-" entry needs a non-empty "- evidence:" line before the next entry.
    missing=$(awk '/^## R-/{if(id!="" && !ev) print id; id=$2; ev=0; next}
                   /^- evidence: *[^ ]/{ev=1}
                   END{if(id!="" && !ev) print id}' "$j/RESULTS.md" 2>/dev/null)
    total=$(grep -c '^## R-' "$j/RESULTS.md" 2>/dev/null)
    if [ -n "$missing" ]; then echo "warn  RESULTS.md: no evidence for $(echo $missing)"; rc=1
    else echo "ok    RESULTS.md: ${total:-0} entries, all with evidence"; fi
    echo "      sessions/: $(last_sessions "$j" 1000 | wc -l | tr -d ' ') notes"
    exit $rc
    ;;

  all)
    base="${2:-${AG_WORKSPACE:-$HOME/Documents/work_space}}"
    find "$base" -maxdepth 4 -path '*/_journal/STATUS.md' 2>/dev/null | sort | while read -r f; do
      p=$(dirname "$(dirname "$f")")
      upd=$(grep -m1 -o '^Updated: [0-9-]*' "$f" | cut -c10-)
      now=$(awk '/^## Now/{f=1; next} /^## /{f=0} f && /^- ./{sub(/^- /,""); print; exit}' "$f")
      printf '%-28s %-10s %s\n' "$(basename "$p")" "${upd:--}" "${now:-(nothing in Now)}" | cut -c1-160
    done
    ;;

  *)
    echo "usage: journal.sh start | root [dir] | init [dir] | show | check [dir] | all [root]" >&2
    exit 2
    ;;
esac
