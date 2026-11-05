"""ag sessions. Find Claude Code sessions across all projects.

Searches the prompts in ~/.claude/history.jsonl. A session matches when
every term (case-insensitive regex) is found in at least one of its
prompts, so terms may come from different prompts of the session.
"""

import argparse
import json
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
SNIPPETS = 3
SNIPPET_WIDTH = 100


def load_sessions(history):
    """Group the prompts of history.jsonl by session id."""
    sessions = {}
    with history.open(errors="replace") as lines:
        for line in lines:
            try:
                entry = json.loads(line)
                sid = entry["sessionId"]
            except (ValueError, KeyError, TypeError):
                continue
            pasted = entry.get("pastedContents") or {}
            text = " ".join(
                [entry.get("display", "")]
                + [p.get("content", "") for p in pasted.values()]
            )
            session = sessions.setdefault(sid, {"prompts": []})
            session["project"] = entry.get("project", "")
            session["prompts"].append((entry.get("timestamp", 0), text))
    return sessions


def snippet(text):
    """One printable line: pasted text can hold escape sequences."""
    clean = "".join(c if c.isprintable() else " " for c in text)
    return " ".join(clean.split())[:SNIPPET_WIDTH]


def stamp(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")


def report(sid, session, patterns, transcripts):
    """Print one session: date, folder, matches, how to resume it."""
    project = session["project"]
    prompts = session["prompts"]
    hits = [
        p for p in prompts if any(r.search(p[1]) for r in patterns)
    ]
    matching = f", {len(hits)} matching" if patterns else ""
    print(
        f"{stamp(prompts[-1][0])}  {Path(project).name}  "
        f"{len(prompts)} prompts{matching}"
    )
    for ms, text in hits[-SNIPPETS:]:
        print(f"  {stamp(ms)}  {snippet(text)}")
    if sid not in transcripts:
        print(f"  transcript gone, cannot resume: {sid}")
    elif not Path(project).is_dir():
        print(f"  folder gone: {project}, session {sid}")
    else:
        print(f"  cd {shlex.quote(project)} && claude --resume {sid}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="ag sessions", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "terms", nargs="*", help="regex terms; none lists recent sessions"
    )
    parser.add_argument(
        "-n", "--limit", type=int, default=10, help="sessions to show"
    )
    args = parser.parse_args()

    try:
        patterns = [re.compile(t, re.IGNORECASE) for t in args.terms]
    except re.error as err:
        sys.exit(f"error: bad pattern: {err}")
    history = CLAUDE_DIR / "history.jsonl"
    if not history.exists():
        sys.exit(f"error: {history} not found")

    matches = {
        sid: session
        for sid, session in load_sessions(history).items()
        if all(
            any(r.search(text) for _, text in session["prompts"])
            for r in patterns
        )
    }
    if not matches:
        print("no session found")
        return

    transcripts = {
        f.stem for f in (CLAUDE_DIR / "projects").glob("*/*.jsonl")
    }
    recent = sorted(
        matches.items(),
        key=lambda item: item[1]["prompts"][-1][0],
        reverse=True,
    )
    for sid, session in recent[: args.limit]:
        report(sid, session, patterns, transcripts)
    if len(recent) > args.limit:
        print(f"{len(recent) - args.limit} older, raise with -n")


if __name__ == "__main__":
    main()
