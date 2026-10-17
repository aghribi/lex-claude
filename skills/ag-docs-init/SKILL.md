---
name: ag-docs-init
description: Scaffold the lex-claude doc layout (PHILOSOPHY, CONTEXT, PRINCIPLES, INVARIANTS, OPS, TODO) in $PWD/docs/. Creates only missing files with minimal headers, never overwrites. Use when bootstrapping documentation in a new or undocumented project, or when the user says "scaffold our docs", "set up the docs structure", "we need docs in this project", or "give me a docs skeleton".
---

Create the standard doc layout in `$PWD/docs/`. **Never overwrite** — only create files that are missing. Do not fill content beyond the header — that's the user's job, this skill only scaffolds.

If `docs/` does not exist, create it. If `CLAUDE.md` is missing at project root, do **not** create one — that's a project-defining decision the user must drive.

Files and headers (today's date in `TODO.md` only):

- `docs/PHILOSOPHY.md`
  ```
  # Philosophy

  What we're building, in one sentence.

  Why it exists. Who it's for. What it explicitly is not.
  ```

- `docs/CONTEXT.md`
  ```
  # Project Glossary

  Shared language for this project. The agent (and new humans) read this to decode jargon consistently. Add a term when it appears in conversation more than twice.

  ## Terms

  **<Term>**
  What it is, in one or two sentences.
  _Avoid_: alternative names that should not be used here.

  ## Relationships

  - A **<Term A>** holds many **<Term B>**.
  - A **<Term B>** belongs to one **<Term A>**.

  ## Flagged ambiguities

  Terms that were used inconsistently and have been resolved. Keep entries so future readers see the resolution.
  ```

- `docs/PRINCIPLES.md`
  ```
  # Engineering Principles

  Non-negotiable rules. If a PR violates one, it does not merge.
  ```

- `docs/INVARIANTS.md`
  ```
  # Invariants

  Architectural contracts. Verify before merging any significant change. Each item: PASS/FAIL evidence, not aspiration.
  ```

- `docs/OPS.md`
  ```
  # Operations Runbook

  Production access, deploy, troubleshooting. Not architecture — what you need when things break.

  ## Access

  ## Deploy

  ## Troubleshooting
  ```

- `docs/TODO.md`
  ```
  # TODO

  Last updated: <YYYY-MM-DD today>.

  ## Shipped

  ## In progress

  ## Next
  ```

After scaffolding, list what was created vs skipped, one line each. Stop. Do not propose to fill the content — point the user at `ag-docs-cleanup` later when they want to audit it.
