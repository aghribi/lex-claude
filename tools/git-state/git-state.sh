#!/bin/bash
# git-state: make every git clone in the workspace restorable from a sync copy (CERNBox).
#
# The sync client skips hidden files, so .git never leaves the machine. For each clone
# this writes, at the repo root and visible to the sync client:
#   GIT_STATE.md      remotes, branch, HEAD, upstream status, restore commands
#   GIT_STATE.patch   uncommitted changes to tracked files (git diff HEAD --binary)
#   GIT_STATE.bundle  commits on local branches that no remote has
# Files are rewritten only when the state changes, and removed when empty.
# The three names are added to the global git excludes, so no repo tracks them.
#
# Usage:
#   git-state.sh [ROOT ...]     scan ROOTs (default: $AG_WORKSPACE or ~/Documents/work_space)
#   git-state.sh --install      hourly launchd job + global git excludes
#   git-state.sh --uninstall    remove the launchd job
set -u

LABEL="com.aghribi.git-state"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
# macOS privacy rules keep launchd jobs out of ~/Documents. The job runs inside this small app,
# so access is granted to it alone (one prompt on first run), not to every bash script.
APP="$HOME/Applications/GitState.app"
LOG_DIR="$HOME/.local/share/git-state"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
NAMES="GIT_STATE.md GIT_STATE.patch GIT_STATE.bundle"

global_excludes() {
  local f
  f="$(git config --global core.excludesFile)"
  if [ -z "$f" ]; then
    f="$HOME/.config/git/ignore"
    git config --global core.excludesFile "$f"
  fi
  f="${f/#\~/$HOME}"
  mkdir -p "$(dirname "$f")"
  touch "$f"
  for n in $NAMES; do grep -qxF "$n" "$f" || echo "$n" >> "$f"; done
  echo "global excludes: $f"
}

install() {
  global_excludes
  mkdir -p "$LOG_DIR" "$(dirname "$PLIST")" "$(dirname "$APP")"
  rm -rf "$APP"
  osacompile -o "$APP" -e "do shell script \"/bin/bash '$SELF' >> '$LOG_DIR/git-state.log' 2>&1\"" || return 1
  /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$APP/Contents/Info.plist"
  codesign --force -s - "$APP"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$APP/Contents/MacOS/applet</string></array>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>LowPriorityIO</key><true/>
  <key>Nice</key><integer>10</integer>
  <key>StandardErrorPath</key><string>$LOG_DIR/launchd.err</string>
</dict>
</plist>
EOF
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
  launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "launchd: $LABEL every hour, log $LOG_DIR/git-state.log"
}

uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
  rm -rf "$PLIST" "$APP" && echo "removed $PLIST and $APP"
}

# Replace $2 with $1 only when the content differs; the temp name is hidden so the sync client ignores it.
put() {
  local tmp="$1" dst="$2"
  if [ -s "$tmp" ]; then
    if cmp -s "$tmp" "$dst"; then rm -f "$tmp"; else mv -f "$tmp" "$dst"; echo "wrote $dst"; fi
  else
    rm -f "$tmp"
    [ -e "$dst" ] && rm -f "$dst" && echo "removed $dst"
  fi
  return 0
}

snapshot() {
  local repo="$1" g branch head describe upstream counts
  g=(git -C "$repo")
  "${g[@]}" rev-parse --verify -q HEAD >/dev/null || return 0   # no commit yet

  # Uncommitted changes to tracked files, staged and unstaged.
  "${g[@]}" diff HEAD --binary > "$repo/.GIT_STATE.patch.tmp"
  put "$repo/.GIT_STATE.patch.tmp" "$repo/GIT_STATE.patch"

  # Local commits no remote has. Bundle bytes are not stable, so a new bundle replaces the old one only when its refs differ.
  local unpushed
  unpushed="$("${g[@]}" rev-list --branches --not --remotes 2>/dev/null | wc -l | tr -d ' ')"
  rm -f "$repo/.GIT_STATE.bundle.tmp"
  [ "$unpushed" -gt 0 ] && "${g[@]}" bundle create -q "$repo/.GIT_STATE.bundle.tmp" --branches --not --remotes 2>/dev/null
  if [ -s "$repo/.GIT_STATE.bundle.tmp" ] && [ "$(git bundle list-heads "$repo/.GIT_STATE.bundle.tmp")" = "$(git bundle list-heads "$repo/GIT_STATE.bundle" 2>/dev/null)" ]; then
    rm -f "$repo/.GIT_STATE.bundle.tmp"
  else
    put "$repo/.GIT_STATE.bundle.tmp" "$repo/GIT_STATE.bundle"
  fi

  branch="$("${g[@]}" symbolic-ref -q --short HEAD || echo "(detached)")"
  head="$("${g[@]}" rev-parse HEAD)"
  describe="$("${g[@]}" describe --tags --always --dirty 2>/dev/null)"
  upstream="$("${g[@]}" rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 2>/dev/null)" || upstream=none
  counts=""
  [ "$upstream" != none ] && counts="$("${g[@]}" rev-list --left-right --count "HEAD...@{upstream}" | awk '{print $1" ahead, "$2" behind"}')"

  {
    echo "# Git state"
    echo
    echo "Written by lex-claude tools/git-state from $(hostname -s). Restores this clone from a copy without .git."
    echo
    echo "- Branch: \`$branch\`"
    echo "- HEAD: \`$head\` (\`$describe\`)"
    echo "- Upstream: \`$upstream\`${counts:+, $counts}"
    echo "- Commits on local branches no remote has: $unpushed"
    echo "- Stash entries (not saved): $("${g[@]}" stash list | wc -l | tr -d ' ')"
    echo
    echo "## Remotes"
    echo
    "${g[@]}" remote -v | awk '$3=="(fetch)"{print "- `"$1"` "$2}'
    echo
    echo "## Local branches"
    echo
    "${g[@]}" for-each-ref --format='- `%(refname:short)` %(objectname:short) %(upstream:short) %(upstream:track)' refs/heads
    echo
    echo "## Restore"
    echo
    echo '```bash'
    echo "git clone $("${g[@]}" remote get-url origin 2>/dev/null || echo '<remote>') restored && cd restored"
    [ -e "$repo/GIT_STATE.bundle" ] && echo "git fetch /path/to/GIT_STATE.bundle 'refs/heads/*:refs/remotes/bundle/*'"
    echo "git checkout $head"
    [ -e "$repo/GIT_STATE.patch" ] && echo "git apply --binary /path/to/GIT_STATE.patch"
    echo '```'
    echo
    echo "Untracked files are in the sync copy as plain files: copy them over the restored clone."
  } > "$repo/.GIT_STATE.md.tmp"
  put "$repo/.GIT_STATE.md.tmp" "$repo/GIT_STATE.md"
}

case "${1:-}" in
  --install) install; exit ;;
  --uninstall) uninstall; exit ;;
  -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit ;;
esac

[ $# -eq 0 ] && set -- "${AG_WORKSPACE:-$HOME/Documents/work_space}"
echo "== $(date '+%Y-%m-%dT%H:%M:%S%z') git-state"
for root in "$@"; do
  # .git is a directory in a clone and a file in a worktree or submodule.
  # Partner-synced spaces are skipped: no files of ours in folders others see.
  find "$root" \( -name node_modules -o -name .venv -o -name __pycache__ -o -name cross_sync_active -o -name _sync_exchange \) -prune -o -name .git -print -prune |
    while IFS= read -r dotgit; do snapshot "$(dirname "$dotgit")"; done
done
