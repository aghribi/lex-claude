---
name: ag-close
description: Close a work slice cleanly. Verify commit/push state, check docs are in step, and update the narrow persistent project memory. Use when the user says "on ferme", "wrap up", "c'est bon pour aujourd'hui", "close the session", or before stepping away from a work slice. This is the manual close ritual; it does not spawn a successor (that is ag-succession, for the context-full handoff).
---

Closing a slice by hand. Three steps.

1. **Commit check.** `git status` + `git log origin/HEAD..HEAD --oneline`. If work
   from this session is uncommitted or unpushed, say so and propose the
   commit/push now (do not fire it without the nod). Clean tree: say so in a line.

2. **Doc check.** Did this session change behaviour, surface, or scope that
   `docs/` or the README describe? If yes, update them now, same breath. If
   nothing applies, skip silently.

3. **Update project memory (narrow, repo-specific, anti-stale).** You are the
   live session with full context, so you judge the delta; `memory.py` only does
   the deterministic bookkeeping (dedup, soft-supersede, decay, cap, persist).

   Memory is for durable facts **specific to this repository** that will still be
   true and useful months from now, on a different machine. The bar is high:
   - STORE: an architectural decision, a stable structural fact about the code, a
     genuine open thread/next step, a confirmed preference for this repo.
   - NEVER STORE: environment or machine state (dev-box paths, "currently running
     X", a live branch name, cluster/server state, transient config), or anything
     that changes when the machine or the day changes. It goes stale silently and
     is worse than no memory. When in doubt, do not store. Zero items beats a
     stale one.

   Mechanics:
   - `slug` = the cwd with every `/`, `.` and space replaced by `-`.
   - See what is stored: `python3 ~/.claude/lex-claude/memory.py list <slug>`
     (prints `id<TAB>type<TAB>text`).
   - Pipe the delta as JSON to `python3 ~/.claude/lex-claude/memory.py apply <slug>`:
     - `new`: items this session established, `{"type": one of
       [decision,fact,thread,preference], "text": one concise sentence}`.
     - `supersede`: `id`s this session made outdated. Strict test, all three:
       same entity, same attribute, and this session established a DIFFERENT
       value. Sharing a topic is not enough; when unsure, do not supersede.
     - `reaffirm`: `id`s this session confirmed still true.
   - Example:
     ```
     echo '{"new":[{"type":"decision","text":"Auth tokens are JWT."}],
            "supersede":["a1b2c3d4e5"],"reaffirm":["f6g7h8i9j0"]}' \
       | python3 ~/.claude/lex-claude/memory.py apply <slug>
     ```
   - If nothing durable changed, skip. Never invent items to fill.

Report: three lines max. State, anything left hanging. No session recap.
