# /// script
# requires-python = ">=3.11"
# dependencies = ["sqlite-vec>=0.1.6", "httpx>=0.27", "python-docx>=1.1", "python-pptx>=1.0", "mcp>=2.3,<3"]
# ///
"""ag-rag. Local hybrid search (FTS5 + bge-m3 vectors) over the user's documents.

Commands:
  init                 write a default config to ~/.config/ag-rag/config.toml
  index [--scope S] [--limit N] [--prune]   extract, chunk, keyword-index (incremental, fast)
  embed [--scope S] [--minutes M]           add vectors to chunks that lack them (slow, resumable)
  update               index then embed
  search QUERY [-k 8] [--scope S]           hybrid search from the terminal
  stats                counts per scope and status
  serve                MCP server over stdio (read-only)

Everything runs locally: text extraction with pdftotext/python-docx/python-pptx,
embeddings through the local Ollama server. Nothing leaves the machine.
"""

import argparse
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import httpx
import sqlite_vec

CONFIG = Path(os.environ.get("AG_RAG_CONFIG", "~/.config/ag-rag/config.toml")).expanduser()
DIM = 1024  # bge-m3

# Never indexed, whatever the config says.
HARD_EXCLUDE_DIRS = {"keepass_vault", "ssh_vault", ".ssh", ".gnupg"}
HARD_EXCLUDE_FILES = re.compile(
    r"(recovery[-_]codes|id_rsa|id_ed25519|\.kdbx$|\.pem$|\.key$|^\.env|secret|password|passwd)", re.I
)

DEFAULT_CONFIG = """\
# ag-rag configuration. Paths may use ~.
root = "~/Documents/work_space"
db = "~/.local/share/ag-rag/index.db"
ollama = "http://localhost:11434"
model = "bge-m3"
extensions = ["pdf", "docx", "pptx", "tex", "md"]
max_mb = 60
chunk_chars = 1500
overlap_chars = 200

exclude_dirs = [".git", ".venv", "venv", "node_modules", "__pycache__", "site-packages",
                "build", "out", ".claude", ".obsidian", "_dev_playground",
                "keepass_vault", "ssh_vault"]
exclude_files = ["github-recovery-codes.txt"]

# Paths relative to root. Order matters only for reporting.
[scopes]
my_outputs = ["resources_active/_my_active"]
projects = ["projects_active", "proposals_active", "cross_sync_active"]
libraries = ["resources_active/_pro_library_active", "resources_active/papers_to_read",
             "resources_active/documentary_resources_active", "resources_active/conferences_active"]
"""


def load_config():
    if not CONFIG.exists():
        sys.exit(f"no config at {CONFIG}: run `ag_rag.py init` first")
    c = tomllib.loads(CONFIG.read_text())
    c["root"] = Path(c["root"]).expanduser()
    c["db"] = Path(c["db"]).expanduser()
    return c


def connect(db: Path, readonly=False):
    if readonly:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, check_same_thread=False)
    else:
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db)
        con.execute("pragma journal_mode=wal")
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    if not readonly:
        con.executescript(f"""
        create table if not exists docs(
            id integer primary key, path text unique, scope text, ext text,
            mtime real, size integer, n_chunks integer, status text, indexed_at text);
        create table if not exists chunks(
            id integer primary key, doc_id integer, ord integer, page integer, text text);
        create index if not exists idx_chunks_doc on chunks(doc_id);
        create virtual table if not exists chunks_fts using fts5(
            text, content='chunks', content_rowid='id', tokenize='unicode61 remove_diacritics 2');
        create virtual table if not exists vec_chunks using vec0(
            embedding float[{DIM}] distance_metric=cosine);
        """)
    return con


# ---------- extraction ----------

def extract(path: Path, ext: str):
    """Return a list of (page, text). Page is 1-based, or 0 when not paged."""
    if ext == "pdf":
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-q", str(path), "-"],
                           capture_output=True, timeout=120)
        pages = r.stdout.decode("utf-8", "ignore").split("\f")
        return [(i + 1, p) for i, p in enumerate(pages) if p.strip()]
    if ext == "docx":
        import docx
        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return [(0, "\n".join(parts))]
    if ext == "pptx":
        from pptx import Presentation

        def shape_texts(shapes):
            for sh in shapes:
                try:
                    if getattr(sh, "shapes", None) is not None:  # group
                        yield from shape_texts(sh.shapes)
                    elif getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                        yield sh.text_frame.text
                    elif getattr(sh, "has_table", False) and sh.has_table:
                        yield "\n".join(" | ".join(c.text for c in r.cells) for r in sh.table.rows)
                except Exception:  # one odd shape must not lose the whole deck
                    continue

        out = []
        for i, slide in enumerate(Presentation(str(path)).slides):
            texts = list(shape_texts(slide.shapes))
            try:
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
                    texts.append(slide.notes_slide.notes_text_frame.text)
            except Exception:
                pass
            out.append((i + 1, "\n".join(texts)))
        return out
    return [(0, path.read_text("utf-8", "ignore"))]  # tex, md


def chunk(pages, size, overlap):
    """Paragraph-aware chunks that keep the page of their first character."""
    out, buf, buf_page = [], "", None
    for page, text in pages:
        for para in re.split(r"\n\s*\n", text):
            para = re.sub(r"[ \t]+", " ", para).strip()
            if not para:
                continue
            if buf_page is None:
                buf_page = page
            if len(buf) + len(para) + 1 > size and buf:
                out.append((buf_page, buf))
                buf = buf[-overlap:] + "\n" + para
                buf_page = page
            else:
                buf = f"{buf}\n{para}" if buf else para
            while len(buf) > size * 1.5:  # very long paragraph
                out.append((buf_page, buf[:size]))
                buf = buf[size - overlap:]
    if buf.strip():
        out.append((buf_page or 0, buf))
    return out


# ---------- embeddings ----------

def embed(client, cfg, texts):
    r = client.post(f"{cfg['ollama']}/api/embed",
                    json={"model": cfg["model"], "input": [t[:6000] for t in texts]}, timeout=600)
    r.raise_for_status()
    return r.json()["embeddings"]


def pack(v):
    return struct.pack(f"{len(v)}f", *v)


# ---------- indexing ----------

def walk(cfg, scope_filter=None):
    exts = {e.lower() for e in cfg["extensions"]}
    ex_dirs = set(cfg["exclude_dirs"]) | HARD_EXCLUDE_DIRS
    ex_files = set(cfg["exclude_files"])
    max_bytes = cfg["max_mb"] * 1024 * 1024
    for scope, rels in cfg["scopes"].items():
        if scope_filter and scope != scope_filter:
            continue
        for rel in rels:
            base = cfg["root"] / rel
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in ex_dirs and not d.startswith(".")]
                for f in filenames:
                    ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
                    if ext not in exts or f in ex_files or HARD_EXCLUDE_FILES.search(f) or f.startswith("~$"):
                        continue
                    p = Path(dirpath) / f
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    if 0 < st.st_size <= max_bytes:
                        yield scope, p, ext, st


def delete_doc(con, doc_id):
    ids = [r[0] for r in con.execute("select id from chunks where doc_id=?", (doc_id,))]
    for cid in ids:
        con.execute("insert into chunks_fts(chunks_fts, rowid, text) select 'delete', id, text from chunks where id=?", (cid,))
        con.execute("delete from vec_chunks where rowid=?", (cid,))
    con.execute("delete from chunks where doc_id=?", (doc_id,))


def cmd_index(args):
    cfg = load_config()
    con = connect(cfg["db"])
    seen, done, t0 = set(), 0, time.time()
    stats = {"new": 0, "updated": 0, "unchanged": 0, "empty": 0, "error": 0, "chunks": 0}
    for scope, p, ext, st in walk(cfg, args.scope):
        sp = str(p)
        seen.add(sp)
        row = con.execute("select id, mtime, size, status from docs where path=?", (sp,)).fetchone()
        if row and row[1] == st.st_mtime and row[2] == st.st_size and row[3] in ("ok", "empty"):
            stats["unchanged"] += 1
            continue
        try:
            pieces = chunk(extract(p, ext), cfg["chunk_chars"], cfg["overlap_chars"])
        except Exception as e:  # unreadable file: record and move on
            pieces, status = [], f"error: {type(e).__name__}"
        else:
            status = "ok" if sum(len(t) for _, t in pieces) >= 200 else "empty"
        if row:
            delete_doc(con, row[0])
            con.execute("delete from docs where id=?", (row[0],))
        cur = con.execute(
            "insert into docs(path, scope, ext, mtime, size, n_chunks, status, indexed_at) values(?,?,?,?,?,?,?,datetime('now'))",
            (sp, scope, ext, st.st_mtime, st.st_size, len(pieces) if status == "ok" else 0, status))
        doc_id = cur.lastrowid
        if status == "ok":
            for j, (page, text) in enumerate(pieces):
                cid = con.execute("insert into chunks(doc_id, ord, page, text) values(?,?,?,?)",
                                  (doc_id, j, page, text)).lastrowid
                con.execute("insert into chunks_fts(rowid, text) values(?,?)", (cid, text))
            stats["chunks"] += len(pieces)
        stats["updated" if row else "new"] += 1 if status == "ok" else 0
        if status == "empty":
            stats["empty"] += 1
        elif status.startswith("error"):
            stats["error"] += 1
        con.commit()
        done += 1
        if done % 250 == 0:
            el = time.time() - t0
            print(f"[{el/60:6.1f} min] {done} docs, {stats['chunks']} chunks, {stats['chunks']/max(el,1):.1f} chunks/s  last: {p.name[:60]}", flush=True)
        if args.limit and done >= args.limit:
            break
    if args.prune and not args.limit:
        scopes = [args.scope] if args.scope else list(cfg["scopes"])
        gone = [(i, pth) for i, pth, sc in con.execute("select id, path, scope from docs")
                if sc in scopes and pth not in seen]
        for i, _ in gone:
            delete_doc(con, i)
            con.execute("delete from docs where id=?", (i,))
        con.commit()
        stats["pruned"] = len(gone)
    print(json.dumps(stats))


def cmd_embed(args):
    """Fill missing vectors, scope by scope in config order, most recent documents first."""
    cfg = load_config()
    con = connect(cfg["db"])
    client = httpx.Client()
    embed(client, cfg, ["warm up"])  # fails fast if Ollama or the model is missing
    deadline = time.time() + args.minutes * 60 if args.minutes else None
    scopes = [args.scope] if args.scope else list(cfg["scopes"])
    total, t0 = 0, time.time()
    for scope in scopes:
        while True:
            rows = con.execute(
                "select c.id, c.text from chunks c join docs d on d.id=c.doc_id "
                "left join vec_chunks v on v.rowid=c.id "
                "where d.scope=? and v.rowid is null order by d.mtime desc, c.id limit 256", (scope,)).fetchall()
            if not rows:
                break
            for b in range(0, len(rows), 32):
                batch = rows[b:b + 32]
                for (cid, _), v in zip(batch, embed(client, cfg, [t for _, t in batch])):
                    con.execute("insert into vec_chunks(rowid, embedding) values(?,?)", (cid, pack(v)))
                con.commit()
                total += len(batch)
            el = time.time() - t0
            left = con.execute("select count(*) from chunks c join docs d on d.id=c.doc_id left join vec_chunks v on v.rowid=c.id where v.rowid is null").fetchone()[0]
            print(f"[{el/60:6.1f} min] {scope}: +{total} vectors, {total/max(el,1):.1f}/s, {left} left (~{left/max(total/max(el,1),0.1)/3600:.1f} h)", flush=True)
            if deadline and time.time() > deadline:
                print("time budget reached; rerun to continue"); return
    print(f"done: {total} vectors in {(time.time()-t0)/60:.1f} min")


# ---------- search ----------

def fts_query(q):
    words = re.findall(r"[\w@.-]+", q, re.UNICODE)
    return " OR ".join(f'"{w}"' for w in words if len(w) > 1)


def search(con, cfg, client, query, k=8, scope=None, pool=60):
    scope_sql = " and d.scope=?" if scope else ""
    params = (scope,) if scope else ()
    ranks = {}
    fq = fts_query(query)
    if fq:
        rows = con.execute(
            f"select c.id from chunks_fts f join chunks c on c.id=f.rowid join docs d on d.id=c.doc_id "
            f"where chunks_fts match ?{scope_sql} order by bm25(chunks_fts) limit ?", (fq, *params, pool)).fetchall()
        for r, (cid,) in enumerate(rows):
            ranks.setdefault(cid, 0.0)
            ranks[cid] += 1 / (60 + r)
    v = embed(client, cfg, [query])[0]
    rows = con.execute(
        "select rowid, distance from vec_chunks where embedding match ? and k = ?", (pack(v), pool * 3)).fetchall()
    r = 0
    for cid, _ in rows:
        if scope and con.execute("select d.scope from chunks c join docs d on d.id=c.doc_id where c.id=?", (cid,)).fetchone()[0] != scope:
            continue
        ranks.setdefault(cid, 0.0)
        ranks[cid] += 1 / (60 + r)
        r += 1
        if r >= pool:
            break
    out = []
    for cid, score in sorted(ranks.items(), key=lambda x: -x[1])[:k]:
        path, sc, page, text = con.execute(
            "select d.path, d.scope, c.page, c.text from chunks c join docs d on d.id=c.doc_id where c.id=?", (cid,)).fetchone()
        out.append({"path": path, "scope": sc, "page": page, "score": round(score, 4), "text": text})
    return out


def cmd_search(args):
    cfg = load_config()
    con = connect(cfg["db"], readonly=True)
    for i, h in enumerate(search(con, cfg, httpx.Client(), args.query, args.k, args.scope), 1):
        rel = os.path.relpath(h["path"], cfg["root"])
        print(f"\n{i}. {rel}" + (f"  (p. {h['page']})" if h["page"] else "") + f"  [{h['scope']}, {h['score']}]")
        print("   " + re.sub(r"\s+", " ", h["text"])[:300])


def cmd_stats(args):
    cfg = load_config()
    con = connect(cfg["db"], readonly=True)
    for scope, status, n, ch in con.execute(
            "select scope, case when status like 'error%' then 'error' else status end s, count(*), sum(n_chunks) from docs group by scope, s order by scope"):
        print(f"{scope:12} {status:6} {n:7} docs {ch or 0:9} chunks")
    nv = con.execute("select count(*) from vec_chunks").fetchone()[0]
    nc = con.execute("select count(*) from chunks").fetchone()[0]
    print(f"vectors: {nv}/{nc} chunks ({100*nv/max(nc,1):.0f}%)")
    print(f"db size: {cfg['db'].stat().st_size / 1e9:.2f} GB")


# ---------- MCP server ----------

def cmd_serve(args):
    from mcp.server.mcpserver import MCPServer
    from mcp.types import ToolAnnotations
    cfg = load_config()
    con = connect(cfg["db"], readonly=True)
    client = httpx.Client()
    mcp = MCPServer("ag-rag", instructions="Read-only search over the user's local work documents.")
    ro = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

    @mcp.tool(annotations=ro)
    def search_documents(query: str, k: int = 8, scope: str | None = None) -> list[dict]:
        """Hybrid (keyword + semantic, French and English) search over the user's indexed
        work documents: publications, presentations, proposals, projects, libraries, notes.
        scope: one of the configured scopes (my_outputs, projects, libraries) or None for all.
        Returns path, page, scope, score and the matching passage."""
        return search(con, cfg, client, query, min(max(k, 1), 30), scope)

    @mcp.tool(annotations=ro)
    def read_document(path: str, page: int | None = None, max_chars: int = 12000) -> str:
        """Read the indexed text of one document returned by search_documents (optionally one
        page). Only indexed documents can be read."""
        row = con.execute("select id from docs where path=? and status='ok'", (path,)).fetchone()
        if not row:
            return "not an indexed document"
        q = "select page, text from chunks where doc_id=?" + (" and page=?" if page else "") + " order by id"
        parts = con.execute(q, (row[0], page) if page else (row[0],)).fetchall()
        return "\n\n".join(f"[p. {p}] {t}" if p else t for p, t in parts)[:max_chars]

    @mcp.tool(annotations=ro)
    def index_stats() -> dict:
        """Number of indexed documents and chunks per scope, and index freshness."""
        rows = con.execute("select scope, count(*), sum(n_chunks), max(indexed_at) from docs where status='ok' group by scope").fetchall()
        out = {s: {"docs": n, "chunks": c, "last_indexed": t} for s, n, c, t in rows}
        out["_vectors"] = con.execute("select count(*) from vec_chunks").fetchone()[0]
        return out

    mcp.run()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p = sub.add_parser("index"); p.add_argument("--scope"); p.add_argument("--limit", type=int); p.add_argument("--prune", action="store_true")
    p = sub.add_parser("embed"); p.add_argument("--scope"); p.add_argument("--minutes", type=float)
    p = sub.add_parser("update"); p.add_argument("--scope"); p.add_argument("--limit", type=int); p.add_argument("--prune", action="store_true"); p.add_argument("--minutes", type=float)
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("-k", type=int, default=8); p.add_argument("--scope")
    sub.add_parser("stats")
    sub.add_parser("serve")
    a = ap.parse_args()
    if a.cmd == "init":
        if CONFIG.exists():
            sys.exit(f"config exists: {CONFIG}")
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(DEFAULT_CONFIG)
        print(f"wrote {CONFIG}")
    else:
        {"index": cmd_index, "embed": cmd_embed, "update": lambda x: (cmd_index(x), cmd_embed(x)),
         "search": cmd_search, "stats": cmd_stats, "serve": cmd_serve}[a.cmd](a)


if __name__ == "__main__":
    main()
