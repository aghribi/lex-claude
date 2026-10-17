---
name: ag-succession
description: Hand this session's work to a fresh, verified successor when the context nears its limit. The Stop hook triggers this automatically past the token threshold (default 600k); it is also invokable by hand ("hand off", "succeed this session", "spawn a successor"). Composes a live briefing, spawns a fresh Claude Code session, has the master verify it loaded identity + rules AND understood the project, rerolls a fresh one on any failure, and stands down once a successor passes.
---

The context is near full (or you were asked to hand off). Spawn a fresh successor
and hand off live. The mechanics (spawn, interrogate, reroll, verify) are in
`succeed.sh`; your only job is the briefing and the judgment around it.

Steps, in order:

1. **Persist durable memory first (narrow, repo-specific, anti-stale).** So the
   successor recalls it at its SessionStart. You judge the delta; `memory.py` does
   the bookkeeping. Bar is high: store only architectural decisions, stable
   structural facts, real open threads, or repo preferences that will still hold
   months from now on another machine. NEVER store environment/machine state
   (paths, "currently running X", live branch, cluster/server state, transient
   config) — it goes stale silently. When in doubt, store nothing.
   - `slug` = cwd with every `/`, `.` and space replaced by `-`.
   - `python3 ~/.claude/lex-claude/memory.py list <slug>` to see what is stored.
   - Pipe the delta to `python3 ~/.claude/lex-claude/memory.py apply <slug>`:
     `{"new":[{"type":"decision|fact|thread|preference","text":"..."}],
       "supersede":["<id>"],"reaffirm":["<id>"]}`. Supersede only on the strict
     test (same entity + attribute + a different value this session established).
     If nothing durable changed, skip.

2. **Decide the mode: clean start vs continue working.**
   - **No live work to continue** (the slice is done, tree clean, nothing in
     flight): skip the briefing. The successor just needs to be a fresh, verified
     session. Go to step 3 with no `--briefing`.
   - **Work in flight** (a task the successor must take over): compose a briefing
     from your own context (not a file). Write a temp file with, tersely: what
     this project is (one line); the task actually in flight and its true state
     (what IS, not what was tried); decisions made this session not yet obvious
     from git; any trap (server-side state, a pending choice, a gotcha). Keep it
     to what a fresh agent needs to continue without re-deriving. Do not restate
     rules/identity — the successor loads those and the master verifies them.

3. **Run the succession.**
   - Clean start: `bash ~/.claude/lex-claude/succeed.sh run --open`
   - Continue working: first call `ListAgents` and note this session's own peer
     name (the line "This session is <name>"), then
     `bash ~/.claude/lex-claude/succeed.sh run --open --briefing <file> --from <name>`
   In continue mode the master does not check a restatement; it has the successor
   make its concrete first move on the work and judges whether that move is
   competent and on-track (rerolls if not), then arms a watch: the successor's
   own Stop hook has the master judge its first turns (`LEX_CLAUDE_WATCH_TURNS`,
   default 3) against the briefing and blocks once with the reason if a turn
   drifts off track. `--from` tells the successor to message you by name once it
   is resumed, which gives you its address for corrections (step 4). `--open` pops the
   verified successor in a new terminal window with a kickoff prompt, so it starts
   the work on its own (macOS: cmux workspace / iTerm / Terminal.app;
   other terminals fall back to the printed resume line; an open failure prints
   its cause). Progress on stderr; outcome on stdout.

4. **Relay the outcome, then tutelle (continue mode) or stand down.**
   - `SUCCESSOR_OK <id>`, clean start → a new window opened on the successor (or,
     if it could not, give the user the verbatim resume line printed by `succeed.sh`
     and the printed cause). Say the successor is verified, this session is done,
     and they can close it. Then stop.
   - `SUCCESSOR_OK <id>`, continue mode → same relay, plus: tell the user this
     session stays open in tutelle for the successor's first turns
     (`LEX_CLAUDE_WATCH_TURNS`, default 3) and must not be closed yet. Then peek:
     start `Monitor` on `bash ~/.claude/lex-claude/succeed.sh peek <id>`. It reads
     the successor's transcript and emits one line per finished turn, then exits
     after the watched turns. Never ping the successor to learn its state; no
     `notify_when_idle` subscription (idle notices duplicate and misfire on
     background waits). The successor's handshake (`<cross-session-message
     from="<peer>">`) only gives you its address: note it, do not reply.
     Each peek event = one finished turn: run
     `bash ~/.claude/lex-claude/succeed.sh turn <id>` and judge that turn with
     your full context (you know the traps the briefing could not carry; the
     master's haiku verdict is appended for reference, not as the answer). On
     track → nothing. Off track → one `SendMessage` to the successor: what is
     wrong, what to do instead, concrete, one paragraph. When peek reports done,
     send one last message ("standing down, you are on your own") and tell the
     user this session can be closed. Stop.
     If the user asks you something meanwhile, answer, then resume waiting.
   - No peek event ever arriving means the successor never ran a turn (window
     closed, or not resumed); that is fine, stay idle. Nothing to work on here.
   - `SUCCESSION_FAILED` → tell the user succession failed the bounded retries,
     which means identity/rules loading is likely structurally broken (worth
     investigating, not retrying blindly). Fall back to native compaction: do
     nothing further, just stop.

Note: the successor is a persisted, resumable session. Closing this one does not
close it, and if the window did not open the user resumes it by hand with the
printed line.
