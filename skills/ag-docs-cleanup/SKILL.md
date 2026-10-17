---
name: ag-docs-cleanup
description: Audit the project's docs/ for staleness, archive sections, dead references, duplicates, and marketing drift. Reports a punch list grouped by DELETE / MERGE / REFRESH / TRIM, never edits without explicit user confirmation. Use periodically to keep docs lean, or when the user says "are our docs stale", "clean up the documentation", "audit the docs", or "the docs/ folder feels heavy".
---

Pass the project's docs under these checks. For each finding, report `file:line` + one-line action. Do **not** edit anything — output is a punch list, the user picks what to act on.

We don't keep archives. Docs reflect current state. Anything else is dead weight that confuses the next reader (human or LLM).

Scope: `$PWD/CLAUDE.md` + every `*.md` under `$PWD/docs/`.

## Checks

1. **Stale dates** — find every `Last updated: YYYY-MM-DD` / `Updated:` / `As of YYYY-MM-DD`. Flag any older than 90 days from today.
2. **Archive sections** — flag any heading whose name contains `archive`, `old`, `deprecated`, `legacy`, `pre-launch`, `v0.x`, `done`, `history`. Flag whole sections marked `<!-- archive -->` or similar.
3. **Shipped graveyard** — in `TODO.md`, if "Shipped" / "Done" outweighs "In progress" + "Next" combined by more than 3:1, flag for trimming. The shipped list is not a changelog — git log is.
4. **Dead references** — extract referenced symbols from each doc: file paths, function names, env vars (`SCREAMING_SNAKE`), table/column names, API routes, container names. For each, run `rg -q '<symbol>'` in the project. Flag what no longer exists.
5. **Duplicates / overlaps** — two files covering the same topic (e.g. PHILOSOPHY + PITCH; INVARIANTS + PRINCIPLES bleeding into each other; OPS + DEPLOY.md). Flag with file refs and which one should absorb the other.
6. **Empty / placeholder** — file has only headers and < 5 lines of real content. Flag as "delete or fill".
7. **Internal-only links** — links to Linear, Notion, Slack, internal Grafana, JIRA, GitHub issues. Flag with note that future readers (new hire, LLM, you in 6 months) may not have access.
8. **Marketing drift in engineering docs** — PHILOSOPHY may be marketing-toned; PRINCIPLES / INVARIANTS / OPS must not be. Flag promotional language ("revolutionize", "best-in-class", "seamless") in non-PHILOSOPHY files.

## Output format

End with a punch list grouped by action:

```
DELETE
  - docs/OLD_PLAN.md — superseded by ROADMAP.md (overlap §2)
  - docs/TODO.md §"Shipped (2024)" — git log is the changelog

MERGE
  - docs/PITCH.md → docs/PHILOSOPHY.md — same content, different tone

REFRESH
  - docs/OPS.md:42 — references `legacy_worker` container, no longer in compose
  - docs/TODO.md:1 — last updated 2025-08-12 (>90d)

TRIM
  - docs/PRINCIPLES.md §"Marketing voice" — drop, belongs in PHILOSOPHY
```

Then **stop**. Wait for user to pick. No autonomous edits, no "while I'm here" cleanups.
