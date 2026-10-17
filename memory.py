#!/usr/bin/env python3
"""lex-claude persistent project memory: forget-by-use + write-time supersession.

The deterministic HANDOFF (handoff.sh) is pure extraction of the CURRENT session
(touched files, last asks, last paragraph). It does not accumulate what mattered
across sessions, never forgets, never supersedes stale state. This adds a small
persistent per-project memory of durable items (decisions, facts, open threads,
preferences) that survives across sessions under three rules validated in the
elastic-substrat probe:

  1. forget by use: items not reaffirmed decay and are pruned (bounded, self-clean)
  2. write-time supersession: at session close an LLM marks which stored items a
     session makes outdated, soft-deleting them (recoverable, never hard-lost)
  3. recall by salience: session start injects the live subset, not the whole file

No embeddings, stdlib only, no spawned model. The judgment (what is durable, what
is superseded) is produced by the NORMAL Claude session, piloted by the
`/ag-handoff` close ritual: the live assistant already holds the full session
context and persona, so it writes the memory delta and this module only does the
deterministic bookkeeping (dedup, soft-supersede, decay, cap, persist). Fail-open:
any error leaves the store and the handoff untouched.

Subcommands:
  recall <slug> [n]   print live memory for SessionStart injection (salience-ranked)
  list <slug>         print live items as id<TAB>type<TAB>text (for the model to
                      reference ids when deciding supersession)
  apply <slug>        read a JSON delta on stdin from the piloted session and apply
                      the three rules: {"new":[{type,text}],"supersede":[ids],
                      "reaffirm":[ids]}
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE = Path.home() / ".claude" / "lex-claude" / "state"
MAX_ITEMS = 60                 # hard cap on live items per project
PRUNE_STALE_DAYS = 45          # superseded or unused items older than this are dropped
RECALL_N = 12
TYPES = ("decision", "fact", "thread", "preference")


def store_path(slug):
    return STATE / slug / "memory.jsonl"


def load(slug):
    p = store_path(slug)
    if not p.exists():
        return []
    items = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def save(slug, items):
    p = store_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items))
    tmp.replace(p)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def age_days(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return 0


def salience(it):
    # recent + reaffirmed items rank first; superseded sink
    s = it.get("uses", 1) - 0.15 * age_days(it.get("last", now_iso()))
    if it.get("superseded"):
        s -= 100
    return s


# ---- recall (fast, stdlib only, no LLM) ----------------------------------
def recall(slug, n=RECALL_N):
    items = [it for it in load(slug) if not it.get("superseded")]
    if not items:
        return
    items.sort(key=salience, reverse=True)
    by_type = {t: [] for t in TYPES}
    for it in items[:n]:
        by_type.setdefault(it.get("type", "fact"), []).append(it)
    out = ["===== project memory (lex-claude) ====="]
    for t in TYPES:
        rows = by_type.get(t) or []
        if rows:
            out.append(f"{t}s:")
            for it in rows:
                out.append(f"  - {it['text']}")
    total_live = len(items)
    out.append(f"({total_live} live memories; forgets the unused, supersedes the outdated)")
    print("\n".join(out))


# ---- list (numbered live items, so the piloted model can reference ids) ---
def list_items(slug):
    for it in [x for x in load(slug) if not x.get("superseded")]:
        print(f"{it['id']}\t{it.get('type','fact')}\t{it['text']}")


# ---- apply (deterministic bookkeeping on a delta from the piloted session) --
def apply(slug):
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return  # fail-open: malformed delta leaves the store untouched
    existing = load(slug)
    by_id = {it["id"]: it for it in existing}
    today = now_iso()

    for iid in data.get("supersede", []) or []:      # soft-delete: recoverable
        if iid in by_id:
            by_id[iid]["superseded"] = True
            by_id[iid]["last"] = today
    for iid in data.get("reaffirm", []) or []:
        if iid in by_id:
            by_id[iid]["uses"] = by_id[iid].get("uses", 1) + 1
            by_id[iid]["last"] = today
            by_id[iid]["superseded"] = False          # confirmed -> restore if soft-deleted

    for ni in data.get("new", []) or []:
        text = " ".join(str(ni.get("text", "")).split())
        typ = ni.get("type", "fact")
        if not text or typ not in TYPES:
            continue
        iid = hashlib.md5(text.lower().encode()).hexdigest()[:10]
        if iid in by_id:
            by_id[iid]["uses"] = by_id[iid].get("uses", 1) + 1
            by_id[iid]["last"] = today
            by_id[iid]["superseded"] = False
        else:
            it = dict(id=iid, type=typ, text=text, added=today, last=today, uses=1, superseded=False)
            existing.append(it); by_id[iid] = it

    # forget: drop items superseded-or-unused and stale, then enforce the cap
    kept = [it for it in existing
            if not ((it.get("superseded") or it.get("uses", 1) <= 1)
                    and age_days(it.get("last", today)) > PRUNE_STALE_DAYS)]
    live_kept = [it for it in kept if not it.get("superseded")]
    if len(live_kept) > MAX_ITEMS:
        live_kept.sort(key=salience, reverse=True)
        keep_ids = {it["id"] for it in live_kept[:MAX_ITEMS]}
        kept = [it for it in kept if it.get("superseded") or it["id"] in keep_ids]
    save(slug, kept)
    print(f"memory updated: {len([x for x in kept if not x.get('superseded')])} live items")


def main():
    if len(sys.argv) < 3:
        return
    cmd, slug = sys.argv[1], sys.argv[2]
    try:
        if cmd == "recall":
            n = int(sys.argv[3]) if len(sys.argv) > 3 else RECALL_N
            recall(slug, n)
        elif cmd == "list":
            list_items(slug)
        elif cmd == "apply":
            apply(slug)
    except Exception:
        return  # fail-open everywhere


if __name__ == "__main__":
    main()
