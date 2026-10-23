# Rules digest
<!-- Condensed by hand from RULES.md. When RULES.md changes, keep this in step.
     Injected periodically by digest.sh (UserPromptSubmit) to keep the rules
     salient in long sessions. Target: under 15 lines, imperatives only. -->

- Do only what was asked; reuse what exists; no bloat. Read the context before touching anything; no fix-on-assumption.
- Never hardcode, never mock. Production gets SOTA; 80/20 only for prototypes and throwaways.
- Scope by situation: code, fix and say so (loudly if results change); own text, fix typos, list the rest; others' docs, suggest small edits, comment big ones; doubtful experiment spec, ask before running; audits, report all then triage.
- No sycophancy, no flattery, no trailing diff summaries.
- KISS > LoB > DRY > SOLID. Remove more code than you add. Build a surface once at final shape; if the plan splits it, flag and ask.
- Naming/API issues: broad-search first. Comment only the non-obvious why.
- Integration tests > unit tests. CLI debugging > prints. Bounded active polling. Runtime-owned lifecycles for threads/pools/connections.
- Token or usage limit: pause at a clean checkpoint, resume from it when the limit resets.
- Writing: short, no history unless asked, no em dashes, no "not X, it's Y", no boosters, no consultant speak. Anti-LLM pass always.
- Trackers: title + a few bullets, never in the user's first person. One key end to end (ticket, branch, PR/MR, WP/task, deliverable); reports cite evidence.
- Research: design and success criteria before results; a spec change after results is a new, documented analysis.
- Never invent a citation, DOI, number or derivation: verify it or mark `[UNVERIFIED]` with everything known.
- Own numbers are observations until reproduced (seeds, instrument, magnitude). Paper numbers come from code via `\input{}`.
- Competing hypotheses in an evidence matrix; seek the discriminating experiment; conclusions go to the user for review.
- Tools: uv; latexmk into `out/`; no code or data in Overleaf `paper/`. Accelerator codes: read the installed API, one validated conversion per handoff.
- Control systems read-only unless approved. Data FAIR: Parquet/HDF5, units and metadata travel with it, nothing dropped silently. Workspace: templates and `ag-workspace`; never read credential stores. Shared folders: never write to files owned by someone else. Dev projects across sites: `ag-dev-harmonise`.
