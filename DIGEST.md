# Rules digest
<!-- Condensed by hand from RULES.md. When RULES.md changes, keep this in step.
     Injected periodically by digest.sh (UserPromptSubmit) to keep the rules
     salient in long sessions. Target: under 15 lines, imperatives only. -->

- Do only what was asked. Reuse what exists. No bloat.
- Read the context before touching anything. No blind edits, no fix-on-assumption.
- Never hardcode, never mock. Spot any, remove them.
- Production gets SOTA, not 80/20. 80/20 is for prototypes and throwaways only.
- Scope by situation: code, fix and say so (loudly if results change); own text, fix typos, list the rest; others' docs, suggest small edits, comment big ones; doubtful experiment spec, ask before running; audits, report all then triage.
- No sycophancy, no flattery, no trailing diff summaries.
- KISS > LoB > DRY > SOLID. Remove more code than you add. Small incremental changes.
- Full iteration over layered rebuilds: build a surface once at final shape; if the plan splits it, flag and ask before the throwaway layer.
- On naming/api issues, broad-search the codebase first. The issue is usually elsewhere too.
- Comment only the non-obvious why (workaround, invariant, edge case). No line-by-line narration.
- Integration tests > unit tests. CLI debugging > prints. Bounded active polling > passive waits.
- Resources owning threads/pools/connections are lifecycle-owned by the runtime, never static/global.
- All writing (docs, comments, commits, PRs, chat): short, no history unless asked, no em dashes, no "not X, it's Y", no boosters, no consultant speak (never play the client's words back, no "you/your" at them). Anti-LLM pass always.
- PRs/tickets/comments: title + a few bullets, concise. Never write in the user's first person; attribute to yourself. One key end to end (ticket, branch, PR/MR, WP/task, deliverable ID); reports cite evidence.
- Research: design and success criteria before results. Spec change after results = new, documented analysis.
- Never invent a citation, DOI, number or derivation: verify it or mark `[UNVERIFIED]` with everything known.
- Own numbers are observations until reproduced (seeds, instrument, magnitude check). Paper numbers come from code via `\input{}`.
- Competing hypotheses in an evidence matrix; seek the discriminating experiment; conclusions go to the user for review.
- Tools: uv for Python; latexmk into `out/`; no code or data in the Overleaf `paper/` folder.
- Accelerator codes: read the installed API, one validated conversion per code handoff. Control systems read-only unless approved. Data FAIR: Parquet/HDF5, units and metadata travel with it, nothing dropped silently.
