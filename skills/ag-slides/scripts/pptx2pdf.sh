#!/bin/sh
# pptx -> pdf with Microsoft PowerPoint. `open -a` hands the sandboxed app access to the file;
# AppleScript `open` on a path outside its container fails silently.
set -eu
in=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
out=${2:-${in%.pptx}.pdf}
case "$out" in /*) ;; *) out=$PWD/$out ;; esac
name=$(basename "$in")
open -a "Microsoft PowerPoint" "$in"
i=0
until osascript -e 'tell application "Microsoft PowerPoint" to get name of presentations' 2>/dev/null | grep -qF "$name"; do
  i=$((i + 1)); [ $i -gt 60 ] && { echo "PowerPoint did not open $name within 60 s" >&2; exit 1; }; sleep 1
done
# names reach AppleScript as arguments, never as script text: a quote in a partner's file name stays data
osascript - "$name" "$out" <<'OSA'
on run argv
  with timeout of 300 seconds
    tell application "Microsoft PowerPoint"
      set d to presentation (item 1 of argv)
      save d in (POSIX file (item 2 of argv)) as save as PDF
      close d saving no
    end tell
  end timeout
end run
OSA
test -s "$out" || { echo "PowerPoint wrote no PDF for $name" >&2; exit 1; }
echo "$out"
