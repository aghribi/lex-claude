"""ag lineage. Succession lines of Claude Code sessions, as trees.

Reads the lineage records under ~/.claude/lex-claude/state/lineage/:
one file per session, named by its id, holding
"gen<TAB>parent-id[<TAB>link]". succeed.sh writes them on a verified
handover; `ag lineage link` writes them, marked "link", for a session
started by hand that continues an earlier one. A session with no
record is the root of its line, generation 1.
"""

import argparse
import os
import shlex
import sys
from datetime import datetime
from pathlib import Path

from ag_sessions import CLAUDE_DIR, load_sessions, snippet

LINEAGE_DIR = CLAUDE_DIR / "lex-claude" / "state" / "lineage"


def transcripts():
    """Map lower-case session id to its transcript."""
    return {
        f.stem.lower(): f for f in (CLAUDE_DIR / "projects").glob("*/*.jsonl")
    }


def read_records():
    """Map lower-case child id to (gen, lower-case parent id, kind)."""
    records = {}
    for f in LINEAGE_DIR.glob("*"):
        fields = f.read_text(errors="replace").strip().split("\t")
        if len(fields) < 2 or not fields[0].isdigit():
            continue
        kind = fields[2] if len(fields) > 2 else "succession"
        records[f.name.lower()] = (int(fields[0]), fields[1].lower(), kind)
    return records


def resolve(ref, known):
    """Full session id from an id or a prefix of one."""
    ref = ref.lower()
    hits = sorted(sid for sid in known if sid.startswith(ref))
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"error: no session transcript matches {ref}")
    shown = ", ".join(h[:8] for h in hits[:5])
    sys.exit(f"error: {ref} matches {len(hits)} sessions ({shown}, ...)")


def folder(sid, history, files):
    """Working folder of a session, from history or its transcript."""
    if sid in history:
        return history[sid]["project"]
    # A session started with `claude -p` is not in history.jsonl.
    with files[sid].open(errors="replace") as lines:
        for line in lines:
            if '"cwd":"' in line:
                return line.split('"cwd":"', 1)[1].split('"', 1)[0]
    return ""


def describe(sid, record, history, files, here):
    """Two or three lines for one node of a tree."""
    gen, _, kind = record or (1, None, "root")
    last = "transcript gone"
    if sid in files:
        mtime = files[sid].stat().st_mtime
        last = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    project = folder(sid, history, files) if sid in files else ""
    prompts = history.get(sid, {}).get("prompts", [])
    mark = "  <- this session" if sid == here else ""
    name = Path(project).name or "?"
    lines = [
        f"gen{gen} {sid[:8]}  {kind}  last {last}  {name}  "
        + f"{len(prompts)} prompts{mark}"
    ]
    if prompts:
        lines.append(f"  last prompt: {snippet(prompts[-1][1])}")
    return lines, project


def show(args, records, history, files, here):
    """Print every line (tree) touching the folder, newest first."""
    children = {}
    for child, (_, parent, _) in records.items():
        children.setdefault(parent, []).append(child)

    def root_of(sid):
        seen = set()
        while sid in records and sid not in seen:
            seen.add(sid)
            sid = records[sid][1]
        return sid

    def members(root):
        out, todo = [], [root]
        while todo:
            sid = todo.pop()
            out.append(sid)
            todo.extend(children.get(sid, []))
        return out

    def mtime(sid):
        return files[sid].stat().st_mtime if sid in files else 0

    roots = {root_of(sid) for sid in records}
    where = Path(args.folder).resolve()

    def touches(root):
        # Only folders at or below `where`: a line rooted in $HOME
        # would otherwise touch every folder.
        for sid in members(root):
            if sid not in files:
                continue
            p = Path(folder(sid, history, files))
            if p == where or where in p.parents:
                return True
        return False

    shown = [r for r in roots if args.all or touches(r)]
    if not shown:
        print(f"no succession line touches {where}")
        return
    shown.sort(key=lambda r: max(map(mtime, members(r))), reverse=True)

    def walk(sid, depth):
        lines, project = describe(
            sid, records.get(sid), history, files, here
        )
        pad = "    " * depth
        for line in lines:
            print(pad + line)
        kids = sorted(children.get(sid, []), key=mtime)
        if not kids and sid in files and Path(project).is_dir():
            print(
                f"{pad}  tip: cd {shlex.quote(project)} && "
                f"claude --resume {files[sid].stem}"
            )
        for kid in kids:
            walk(kid, depth + 1)

    for root in shown:
        walk(root, 0)
        print()


def link(args, records, files, here):
    """Record a hand-started session as the next generation."""
    child_ref = args.child or here
    if not child_ref:
        sys.exit("error: no session id: pass --child or run inside Claude")
    child = resolve(child_ref, files)
    parent = resolve(args.parent, files)
    if child == parent:
        sys.exit("error: a session cannot be its own parent")
    if child in records:
        gen, old, kind = records[child]
        sys.exit(
            f"error: {child[:8]} already has a record (gen{gen} <- "
            f"{old[:8]}, {kind}). Remove {LINEAGE_DIR / files[child].stem} "
            "first to change it."
        )
    ancestor, seen = parent, set()
    while ancestor in records and ancestor not in seen:
        seen.add(ancestor)
        ancestor = records[ancestor][1]
        if ancestor == child:
            sys.exit(f"error: {child[:8]} is an ancestor of {parent[:8]}")
    gen = records.get(parent, (1,))[0] + 1
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)
    (LINEAGE_DIR / files[child].stem).write_text(
        f"{gen}\t{files[parent].stem}\tlink\n"
    )
    print(f"linked {child[:8]} as gen{gen} <- {parent[:8]}")


def main():
    parser = argparse.ArgumentParser(
        prog="ag lineage", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--all", action="store_true", help="every line, not only this folder"
    )
    parser.add_argument(
        "--folder", default=os.getcwd(), help="folder the lines must touch"
    )
    sub = parser.add_subparsers(dest="cmd")
    p_link = sub.add_parser(
        "link", help="attach a hand-started session to a line"
    )
    p_link.add_argument(
        "--parent", required=True, help="id or prefix of the parent"
    )
    p_link.add_argument(
        "--child", help="id or prefix; default: the current session"
    )
    args = parser.parse_args()

    files = transcripts()
    records = read_records()
    here = os.environ.get("CLAUDE_CODE_SESSION_ID", "").lower()
    if args.cmd == "link":
        link(args, records, files, here)
        return
    history_file = CLAUDE_DIR / "history.jsonl"
    history = {}
    if history_file.exists():
        history = {
            sid.lower(): s for sid, s in load_sessions(history_file).items()
        }
    show(args, records, history, files, here)


if __name__ == "__main__":
    main()
