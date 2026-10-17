---
name: ag-rag
description: Search the user's own local documents (publications, presentations, proposals and Part Bs, projects, reviews, HDR, libraries of papers, Obsidian notes) with the local hybrid index - French and English, keyword plus semantic. Use before answering anything that depends on the user's past work ("what did I write about X", "find my slides on Y", "which proposal had this WP", "reuse my text on Z"), before drafting text that should build on their documents, and to maintain the index (build, update, stats).
---

Local retrieval over `work_space`. Everything stays on the machine: text extraction with pdftotext / python-docx / python-pptx, embeddings with `bge-m3` through the local Ollama, index in SQLite (FTS5 + sqlite-vec) at `~/.local/share/ag-rag/index.db`. Config: `~/.config/ag-rag/config.toml` (scopes, exclusions).

## Searching

Prefer the MCP tools when the `ag-rag` server is connected:
- `search_documents(query, k=8, scope=None)`: hybrid ranking (BM25 + vectors, reciprocal rank fusion). Scopes: `my_outputs`, `projects`, `libraries`.
- `read_document(path, page=None)`: full indexed text of a hit, or one page. Only indexed documents are readable.
- `index_stats()`: counts and freshness.

Without MCP: `uv run ~/.claude/lex-claude/tools/ag-rag/ag_rag.py search "query" -k 8 --scope projects`.

Good practice:
- Query in the document's language, or run the query in both French and English: bge-m3 is multilingual, but keyword matching is not.
- Exact identifiers (call IDs, WP numbers, machine names, acronyms) work best as short keyword queries; concepts work best as a sentence.
- Cite hits by relative path and page. Results are excerpts: open the document (`read_document`) before quoting or reusing.
- The index is a snapshot: check `index_stats` freshness when recency matters, and say when a result may be stale.
- Text reused from the user's past documents is still subject to the rules: verify numbers and references, and never copy confidential material (reviews of other people's manuscripts or proposals, `_to_review_proposals`) into new documents.

## Maintaining the index

```bash
R=~/.claude/lex-claude/tools/ag-rag/ag_rag.py
uv run $R update                    # index (fast) then embed (slow); both incremental
uv run $R index                     # extract + keyword index only: only new or changed files
uv run $R index --scope my_outputs  # one scope
uv run $R index --prune             # also drop documents deleted from disk
uv run $R embed --minutes 60       # add missing vectors, resumable (about 5 chunks/s on an M3)
uv run $R stats                     # includes the share of chunks that have vectors
```
One index run at a time (lock file next to the index). Nightly: `tools/ag-rag/nightly.sh` (launchd, 02:00) runs `update --prune` with a 4-hour embedding budget and logs to `~/.local/share/ag-rag/nightly.log`.
Vectors are filled scope by scope (my_outputs, projects, libraries), most recent documents first. Until a chunk has its vector it is found by keywords only.
Unchanged files (same mtime and size) are skipped. Files with almost no extractable text are recorded as `empty` (usually scanned PDFs; OCR is not enabled yet).

## Never indexed

`keepass_vault`, `ssh_vault`, recovery codes, keys and `.env` files are excluded in the config and again in code. `.git`, virtual envs, `node_modules`, `build`, `out`, `.claude`, `.obsidian` are skipped. Never point the indexer at a credential store, even if asked to "index everything".
