---
name: ag-review-project
description: Read project docs (CLAUDE.md + docs/PHILOSOPHY, PRINCIPLES, INVARIANTS, OPS, TODO) and produce a sharp summary of state and next actions in under 25 lines. Use when the user asks "where are we on this project", "give me a status", "catch me up", "what's the state", comes back to a project after time away, or wants a fast read of project context before diving in.
disable-model-invocation: true
---

Read these files in `$PWD` (skip missing): `CLAUDE.md`, `docs/PHILOSOPHY.md`, `docs/CONTEXT.md`, `docs/PRINCIPLES.md`, `docs/INVARIANTS.md`, `docs/OPS.md`, `docs/TODO.md`.

Then produce, under 25 lines:

- **Project**: 1-line purpose.
- **Non-obvious rules**: hard constraints worth flagging.
- **State**: what's done, in progress, blocked.
- **Next**: top 3 priorities.

No paraphrasing of files. Signal only.
