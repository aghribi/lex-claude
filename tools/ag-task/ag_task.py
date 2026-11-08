# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""ag task. One Markdown note per task in the Obsidian work vault.

Tasks live in $AG_VAULT/05_tasks/ (vault default under $AG_WORKSPACE).
Each note has frontmatter: type, status, project, tags, created, due,
source, session, cwd, email. 05_tasks/projects.yaml maps project keys
to workspace folders, so a task added from a session gets its project
from the folder the session runs in.
"""

import argparse
import os
import re
import shlex
import sys
from datetime import date
from pathlib import Path

import yaml

WS = Path(
    os.environ.get("AG_WORKSPACE", Path.home() / "Documents/work_space")
)
VAULT = Path(
    os.environ.get(
        "AG_VAULT",
        WS / "resources_active/_my_active/my_vaults_active/obsidian_work",
    )
)
TASKS = VAULT / "05_tasks"
REGISTRY = TASKS / "projects.yaml"
STATUSES = ("open", "waiting", "done")
FRONT = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


def load_registry():
    """Project key -> {paths, aliases, vault}; empty if no file."""
    if not REGISTRY.exists():
        return {}
    return yaml.safe_load(REGISTRY.read_text()) or {}


def resolve_project(name, registry):
    """Registry key for a key or an alias; unknown names pass through."""
    low = name.lower()
    for key, entry in registry.items():
        if low == key or low in (entry or {}).get("aliases", []):
            return key
    return low


def detect_project(cwd, registry):
    """Project of a folder: longest registry path, then the item
    folder under the workspace (<area>/<item>/...)."""
    cwd = Path(cwd).resolve()
    best, depth = None, -1
    for key, entry in registry.items():
        for rel in (entry or {}).get("paths", []):
            root = (WS / rel).resolve()
            if cwd.is_relative_to(root) and len(root.parts) > depth:
                best, depth = key, len(root.parts)
    if best:
        return best
    try:
        parts = cwd.relative_to(WS.resolve()).parts
    except ValueError:
        return None
    return parts[1].strip().lower() if len(parts) > 1 else None


def read(path):
    """(frontmatter dict, body) of a task note."""
    m = FRONT.match(path.read_text())
    if not m:
        return {}, path.read_text()
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def write(path, meta, body):
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{front}---\n{body}")


def tasks():
    """All task notes as (path, meta), oldest first."""
    if not TASKS.is_dir():
        return []
    out = []
    for path in sorted(TASKS.glob("*.md")):
        meta, _ = read(path)
        if meta.get("type") == "task":
            out.append((path, meta))
    return out


def find(ref):
    """The one task whose file name contains `ref`."""
    hits = [(p, m) for p, m in tasks() if ref.lower() in p.stem.lower()]
    if len(hits) != 1:
        names = ", ".join(p.stem for p, _ in hits) or "none"
        sys.exit(f"error: '{ref}' matches {len(hits)} tasks: {names}")
    return hits[0]


def slugify(text):
    words = re.sub(r"[^\w\s-]", "", text.lower()).split()
    return "-".join(words[:6])[:50] or "task"


def resume_line(meta):
    if not meta.get("session"):
        return None
    cwd = shlex.quote(meta.get("cwd") or ".")
    return f"cd {cwd} && claude --resume {meta['session']}"


def cmd_add(args, registry):
    text = " ".join(args.text)
    tags = args.tag + re.findall(r"(?<!\S)#([\w/-]+)", text)
    named = re.findall(r"(?<!\S)@([\w@.-]+)", text)
    title = " ".join(
        w for w in text.split() if not re.match(r"[#@][\w/@.-]+$", w)
    )
    if not title:
        sys.exit("error: empty task")
    if args.email and any(
        m.get("email") == args.email for _, m in tasks()
    ):
        print(f"skip: a task already links email {args.email}")
        return

    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    project = args.project or (named[0] if named else None)
    project = (
        resolve_project(project, registry)
        if project
        else detect_project(cwd, registry)
    )
    if project and registry and project not in registry:
        print(f"note: project '{project}' is not in {REGISTRY.name}")

    meta = {
        "type": "task",
        "status": "open",
        "project": project,
        "tags": sorted(set(tags)),
        "created": date.today(),
    }
    if args.due:
        meta["due"] = args.due
    meta["source"] = args.source or (
        "email" if args.email else "session" if session else "manual"
    )
    if session and meta["source"] == "session":
        meta["session"] = session
        meta["cwd"] = cwd
    if args.email:
        meta["email"] = args.email

    TASKS.mkdir(parents=True, exist_ok=True)
    stem = f"{date.today():%Y%m%d}-{slugify(title)}"
    path, n = TASKS / f"{stem}.md", 2
    while path.exists():
        path, n = TASKS / f"{stem}-{n}.md", n + 1
    body = f"# {title}\n"
    if args.note:
        body += f"\n{args.note}\n"
    if resume_line(meta):
        body += f"\nResume: `{resume_line(meta)}`\n"
    write(path, meta, body)
    print(f"added {path.stem} [{project or 'no project'}]")


def cmd_list(args, registry):
    project = None
    if args.here:
        cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        project = detect_project(cwd, registry)
        if not project:
            return
    elif args.project:
        project = resolve_project(args.project, registry)
    wanted = STATUSES if args.status == "all" else (args.status,)
    if args.status == "open":
        wanted = ("open", "waiting")

    rows = [
        (p, m)
        for p, m in tasks()
        if m.get("status") in wanted
        and (project is None or m.get("project") == project)
        and all(t in (m.get("tags") or []) for t in args.tag)
    ]
    rows.sort(key=lambda r: (str(r[1].get("due") or "9999"), r[0].stem))
    if args.brief:
        if not rows:
            return
        print(f"\n===== open tasks: {project} ({TASKS}) =====")
    shown = rows[: args.brief] if args.brief else rows
    for path, meta in shown:
        _, body = read(path)
        title = next(
            (ln[2:] for ln in body.splitlines() if ln.startswith("# ")),
            path.stem,
        )
        flags = [meta["status"]] if meta["status"] != "open" else []
        if meta.get("due"):
            flags.append(f"due {meta['due']}")
        flags += [f"#{t}" for t in meta.get("tags") or []]
        where = "" if project else f"[{meta.get('project') or '-'}] "
        extra = f"  ({', '.join(flags)})" if flags else ""
        print(f"- {path.stem}: {where}{title}{extra}")
    if args.brief and len(rows) > args.brief:
        print(f"{len(rows) - args.brief} more: ag task list -p {project}")
    if not rows and not args.brief:
        print("no task")


def cmd_status(ref, status):
    path, meta = find(ref)
    _, body = read(path)
    meta["status"] = status
    if status == "done":
        meta["done"] = date.today()
    else:
        meta.pop("done", None)
    write(path, meta, body)
    print(f"{path.stem}: {status}")


def cmd_show(ref):
    path, meta = find(ref)
    print(path)
    print(path.read_text(), end="")


def main():
    parser = argparse.ArgumentParser(
        prog="ag task", description=__doc__.split("\n")[0]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="add a task (#tag, @project in text)")
    p.add_argument("text", nargs="+")
    p.add_argument("-p", "--project")
    p.add_argument("-t", "--tag", action="append", default=[])
    p.add_argument("--due", type=date.fromisoformat,
                   help="YYYY-MM-DD")
    p.add_argument("--note", help="extra line under the title")
    p.add_argument("--source", choices=("session", "email", "manual"))
    p.add_argument("--email", help="Message-ID of the linked email")

    p = sub.add_parser("list", help="list tasks")
    p.add_argument("-p", "--project")
    p.add_argument("--here", action="store_true",
                   help="project of the current folder")
    p.add_argument("-t", "--tag", action="append", default=[])
    p.add_argument("-s", "--status", default="open",
                   choices=("open", "waiting", "done", "all"),
                   help="open includes waiting (default)")
    p.add_argument("--brief", type=int, default=0, metavar="N",
                   help="hook format, at most N lines")

    p = sub.add_parser("done", help="mark a task done")
    p.add_argument("ref", help="part of the task file name")
    p = sub.add_parser("status", help="set open, waiting or done")
    p.add_argument("ref")
    p.add_argument("value", choices=STATUSES)
    p = sub.add_parser("show", help="print a task note")
    p.add_argument("ref")

    args = parser.parse_args()
    registry = load_registry()
    if args.cmd == "add":
        cmd_add(args, registry)
    elif args.cmd == "list":
        cmd_list(args, registry)
    elif args.cmd == "done":
        cmd_status(args.ref, "done")
    elif args.cmd == "status":
        cmd_status(args.ref, args.value)
    else:
        cmd_show(args.ref)


if __name__ == "__main__":
    main()
