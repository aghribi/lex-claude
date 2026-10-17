# lex-claude

Fork of [MagicLex/lex-claude](https://github.com/MagicLex/lex-claude) with a co-scientist layer: research rules in `RULES.md` ("Co-scientist", "Research tools"), the `ag-co-scientist` skill, and vendored science skills (see `THIRD_PARTY.md`).

LEXClaude Code config: identities (with canonical shared rules), `SessionStart` hook, personal skills, and a `ag` CLI to deploy / maintain / sync everything.

> ## ⚠️ Heads up: this is **my** personal config
>
> `ag install` is **destructive** to your existing Claude Code setup. If you run it as-is:
>
> - **`~/.claude/CLAUDE.md`**: if you have one, it gets backed up to `CLAUDE.md.bak.<ts>` and **replaced** by a symlink to the first identity found in `identities/` (alphabetical order: `betatron` in this fork). Your global instructions stop being loaded until you restore them.
> - **`~/.claude/settings.json`**: backed up to `settings.json.bak.<ts>`, then any prior `lex-claude` `SessionStart` hook (and legacy `JeanJean` hooks from earlier versions) is stripped and replaced. Other hooks are preserved, but you're trusting `jq` + my filter logic.
> - **`~/.claude/skills/`**: every folder in `skills/` is symlinked there. An existing skill with the same name is left untouched and reported (`warn: ... left untouched`).
> - **`~/.codex/skills/ag*`**: a Codex skill with one of those names is left untouched and reported as a conflict. Rename or remove it, then run `ag update` to deploy the lex-claude skill.
> - **`~/.local/bin/lex-claude` and `~/.local/bin/ag`**: created/replaced as symlinks. If you already have a binary called `ag`, it gets shadowed.
>
> This repo is published openly because the structure is reusable, **not** because you should run `ag install` blindly. If you want the same setup with your own persona and rules: fork it, replace the file(s) in `identities/` and edit `RULES.md` to match your conventions, then install from your fork (`LEX_CLAUDE_REPO=https://github.com/<you>/lex-claude.git ag install`).

## Credits

Built on Lex's work ([MagicLex/lex-claude](https://github.com/MagicLex/lex-claude)): the CLI, identity architecture and synced rules, hooks (SessionStart, digest, style, usage), master judge, cold start, succession, project memory, the original `lc-*` skills (renamed `ag-*` here), the `lc-voice` anti-LLM checklist behind `ag-voice`, `hopsdev` behind `pkgdev`, and the personas Grug, JeanJean and Joss behind Nolen, Lattice and Gantt. Vendored science skills and their licenses: `THIRD_PARTY.md`.

## Bootstrap (new machine or new user)

```bash
curl -fsSL https://raw.githubusercontent.com/aghribi/lex-claude/main/bin/lex-claude | bash -s install
```

Clones the repo into `~/.claude/lex-claude`, syncs the rules into every identity, symlinks `~/.claude/CLAUDE.md` to the active identity, deploys the skills, wires the hook into `settings.json`, and installs the CLI on `PATH` (`~/.local/bin/lex-claude` + alias `ag`).

> Requirements: `git`, `bash`, `jq` (to patch `settings.json` cleanly).

## Plugin install (skills only, no identities or hook)

If you only want the skills and don't want the identity/hook machinery, the repo is also a Claude Code plugin. Either:

```bash
claude --plugin-dir /path/to/lex-claude
```

…or install it through the marketplace (`/plugin` inside Claude Code, point it at this repo). Plugin-installed skills are namespaced as `/lex-claude:ag-invariants`, `/lex-claude:ag-exploration`, etc. The standalone `ag install` path keeps short names (`/ag-invariants`).

## Codex bridge

Install/update/identity-switch symlinks the active identity to Codex's global instructions file, `~/.codex/AGENTS.md`, and each bundled skill to `~/.codex/skills/`. Codex therefore picks up the same rules and `ag-*` skills without the wrapper. A hand-written `~/.codex/AGENTS.md` is backed up, not clobbered; an existing conflicting skill is left untouched and reported. `ag doctor` checks both links. This covers Codex globally; Cursor/Amp and friends read `AGENTS.md` at project root, which is per-repo and out of scope for the global installer.

For richer, project-aware context (docs bundle, `ag` reference), `ag codex` still acts as a wrapper: it renders the same context bundle as `hook.sh` and passes it as Codex's initial prompt.

Modes:

- `ag codex --full` loads:
- the active global identity from `~/.claude/CLAUDE.md`
- the current project's `CLAUDE.md` if present
- `docs/PHILOSOPHY.md`, `docs/CONTEXT.md`, `docs/PRINCIPLES.md`, `docs/INVARIANTS.md`, `docs/OPS.md`, `docs/TODO.md` if present
- the `ag` command reference
- the active `ag lang` setting

- `ag codex --lite` loads:
- the active global identity from `~/.claude/CLAUDE.md`
- the current project's `CLAUDE.md` if present
- the `ag` command reference
- the active `ag lang` setting

Examples:

```bash
ag codex --lite
ag codex --full "review this repo and tell me the main risks"
ag codex --print --lite
```

## CLI

```
ag install [--yes]                                 # bootstrap (idempotent). Prompts before overwriting existing files.
ag install --pkg-only                              # install only the pkgdev binary + PATH (no identity/rules/skills/hook)
ag update                                          # git pull + sync rules + redeploy
ag version                                         # print install version (v<commit-count> + date)
ag identity                                        # list, active marked *
ag identity <name>                                 # switch (global)
ag identity new --name <n> --desc "<persona>"      # create identity (persona + shared rules)
ag identity new --name <n> --empty                 # create identity without shared rules
ag rules sync                                      # re-inject RULES.md into every managed identity
ag lang [en|fr|off]                                # set / clear Claude reply language (hook injects, statusline shows)
ag skip on|off|status                              # toggle aliases: Claude skips permissions, Codex bypasses approvals and sandboxing
ag codex [--lite|--full] [prompt]                  # launch Codex with lex-claude context preloaded
ag codex --print [--lite|--full] [prompt]          # inspect the generated Codex prompt without launching
ag usage                                           # report which commands + skills get used; never-used = debloat candidates
ag doctor                                          # check symlinks, hook, skills, PATH (auto-fixes ~/.zshrc / ~/.bashrc)
ag -help | -h | --help | help                      # all variants
```

### pkgdev

Sibling binary deployed alongside `ag` (full install, or `ag install --pkg-only`). Points a Python package in the active env at a git branch, to test a fix or a feature branch of Xsuite, Cheetah or any other package without hand-running clone + `uv pip install`.

```
pkgdev <pkg>@<branch>            # clone the branch into $PKGDEV_HOME, uv pip install -e, show status
pkgdev <owner/repo>@<branch>     # any GitHub repo (or a full https/ssh git URL)
pkgdev --quick <spec>            # no clone: uv pip install --force-reinstall git+...@branch
pkgdev --release <pkg>           # back to the PyPI release
pkgdev --status <pkg>            # installed version, location, editable source
```

Short names: `xtrack`, `xpart`, `xobjects`, `xfields`, `xdeps`, `xwakes`, `xcoll` (github.com/xsuite), `cheetah` (github.com/desy-ml/cheetah, PyPI `cheetah-accelerator`). Run inside the env to modify (uv targets the activated venv or `./.venv`). Clone base: `$TMPDIR/pkgdev`, override with `PKGDEV_HOME`.

### agent-browser-bg

Stock agent-browser (up to v0.38.2) calls `Page.bringToFront` when it creates or switches tabs, so `--auto-connect` pulls Chrome over whatever app you are in. Upstream issue [#1247](https://github.com/vercel-labs/agent-browser/issues/1247), fix in PR [#1880](https://github.com/vercel-labs/agent-browser/pull/1880), not merged yet. Until it ships, build v0.38.2 plus that PR as a separate binary and pin brew to the same base:

```
brew install rust
git clone https://github.com/vercel-labs/agent-browser.git && cd agent-browser
git checkout -b bg v0.38.2
git fetch origin pull/1880/head:pr-1880 && git cherry-pick pr-1880
cd cli && cargo build --release
ln -sf "$PWD/target/release/agent-browser" ~/.local/bin/agent-browser-bg
brew upgrade agent-browser && brew pin agent-browser   # stock stays at the same base
```

Check: `agent-browser-bg --auto-connect tab new https://example.com` opens a tab and your terminal keeps focus. Background tabs cannot be screenshotted; run `agent-browser-bg bringtofront` first. Once upstream ships the fix: `brew unpin agent-browser && brew upgrade agent-browser`, delete the clone and the symlink, and drop the `agent-browser-bg` line from `RULES.md`.

## Kill switches (env vars)

Three escape hatches if you want to neutralise a piece without uninstalling.

- `LEX_CLAUDE_DISABLE=1`: hook.sh exits early; nothing gets injected at SessionStart. Useful when debugging context bloat or comparing with/without the hook.
- `LEX_CLAUDE_NO_AUTO_UPDATE=1`: disables the daily `git pull` + re-exec on `ag <cmd>`. Use when you want frozen behaviour (CI runs, shared machines, long-running scripts).
- `LEX_CLAUDE_YES=1`: equivalent to `ag install --yes`; skips the destructive-overwrite prompt. Use only when you've read the warning above and accept it.
- `LEX_CLAUDE_NO_USAGE=1`: turns off usage logging (`ag usage` keeps reading the existing log but records nothing new). `LEX_CLAUDE_DISABLE=1` also stops it.
- `LEX_CLAUDE_DIGEST_EVERY=0`: turns off the periodic rules digest (any other value sets the cadence in prompts, default 5). `LEX_CLAUDE_DISABLE=1` also stops it, along with the style hook.
- `LEX_CLAUDE_HANDOFF_DISABLE=1`: turns off the token-triggered succession (the `Stop` hook fires nothing near the limit). `LEX_CLAUDE_DISABLE=1` also stops it.
- `LEX_CLAUDE_COLDSTART_DISABLE=1`: turns off the `ag claude` pre-flight; the launcher hands over the seat without verifying identity/rules load first.
- `LEX_CLAUDE_HANDOFF_TOKENS` (default 600000): context-token threshold at which succession fires. `LEX_CLAUDE_SUCCESSION_MAX` (default 3): reroll cap. `LEX_CLAUDE_WATCH_TURNS` (default 3): how many of the successor's first turns the master judges after the handover (0 = no watch). `LEX_CLAUDE_MASTER_MODEL` (default haiku): the drift-judge model.
- `LEX_CLAUDE_MEMORY_DISABLE=1`: turns off persistent project memory (`memory.py` recall at SessionStart; write is piloted via `/ag-close` and `/ag-succession`). `LEX_CLAUDE_DISABLE=1` also stops it.

Heartbeat: hook.sh writes `~/.claude/lex-claude/.last-hook` (epoch seconds) on each successful run. `stat -f %m ~/.claude/lex-claude/.last-hook` (macOS) or `stat -c %Y` (Linux) tells you when the hook last fired.

## Usage trace (debloat aid)

`usage.sh` records what actually gets used so dead surface gets cut with data, not a guess. Three feeds, one append-only log at `~/.claude/lex-claude/usage.log` (`epoch<TAB>source<TAB>name`):

- **CLI**: the `ag` and `pkgdev` dispatchers log the top-level command (best-effort, never blocks the command).
- **Skills**: a `PreToolUse` hook matching the `Skill` tool logs each skill Claude invokes.

`ag usage` tallies the log and lists, per source, what's used and what's **never used** (the debloat candidates). Off via `LEX_CLAUDE_NO_USAGE=1`. The log is local only, never synced.

## Identity architecture

Every identity shares the **same canonical rules**, because Claude reads multiple files badly. Everything must live in a single self-contained file.

- `RULES.md` is the canonical source for shared rules.
- Each `identities/<name>.md` contains:
  - a personal prelude (the "you are X, ..." that defines the character)
  - a managed block between `<!-- LC_RULES_BEGIN -->` and `<!-- LC_RULES_END -->`, rewritten on every `ag update` / `ag rules sync` from `RULES.md`
- `ag identity new` splices the prelude + the rules automatically
- `ag identity new --empty` only creates the prelude, no markers, no sync (for special cases)

When you edit `RULES.md` and push, every identity on every machine picks up the update on the next `ag <anything>` (auto-update).

## Auto commit/push on `identity new`

When creating an identity, the CLI:
- `git add identities/<name>.md`
- `git commit -m "add identity: <name>"`
- `git push` (to the configured remote: fork or upstream depending on the clone)

If push fails (no rights, offline, etc.) the identity stays committed locally with an explicit message; push it later yourself.

## Tree loaded by the hook

On every session, `hook.sh` injects into context:

```
$CLAUDE_PROJECT_DIR/
├── CLAUDE.md                ← project-specific rules (optional)
└── docs/
    ├── PHILOSOPHY.md
    ├── CONTEXT.md
    ├── PRINCIPLES.md
    ├── INVARIANTS.md
    ├── OPS.md
    └── TODO.md
```

All optional. Only what exists is loaded.

The active identity at `~/.claude/CLAUDE.md` (symlink → `identities/<name>.md`, rules inlined) is loaded natively by Claude Code, so `hook.sh` does not re-inject it. Codex gets the same identity through the `~/.codex/AGENTS.md` symlink and the bundled skills through `~/.codex/skills/` (see Codex bridge above).

## Rules stickiness

Rules injected once at SessionStart lose attention weight as the context grows. Two hooks compensate:

- **`digest.sh`** (`UserPromptSubmit`): re-injects `DIGEST.md`, a hand-condensed ~15-line digest of `RULES.md`, every Nth prompt. Cadence via `LEX_CLAUDE_DIGEST_EVERY` (default 5, `0` = off). State: a per-session prompt counter in `~/.claude/lex-claude/.digest/`, pruned after 7 days. Compaction and resume are already covered: the SessionStart hook re-fires on both and reloads the full rules.
- **`style.sh`** (`PostToolUse` on `Write|Edit|MultiEdit`): greps written `.md`/`.mdx` files for em dashes and feeds hits back to Claude. Deterministic enforcement of the writing-style rule instead of hoping the model remembers it. Skips model-facing config (`CLAUDE.md`, `RULES.md`, `DIGEST.md`, `SKILL.md`, `MEMORY.md`, anything under `.claude/`, `identities/`, `memory/`).

When you edit `RULES.md`, keep `DIGEST.md` in step. It is a manual condensation, not generated.

## Session flow

Identity and rules loading is verified live by a judge. Work near the context limit is handed to a fresh, verified successor. Nothing is persisted between sessions except the project memory below.

- **Master** (`master.sh`). A neutral judge spawned on demand with `claude -p` and the identity hook disabled, so it does not judge itself. Ground truth is the resolved `~/.claude/CLAUDE.md`, plus the briefing for the project phases. Three phases: `identity` (did the subject load the identity and rules), `project` (did it understand the briefed work), `trajectory` (is a finished turn still on the briefed track). Verdict is strict JSON. Anything unparseable fails.
- **Cold start** (`ag claude`). The launcher runs the identity self-report as turn 1 of a fresh session and has the master judge it before handing over the seat. On failure it repairs the identity symlink and rerolls, up to `LEX_CLAUDE_SUCCESSION_MAX` times, then launches anyway with a warning. Skip with `LEX_CLAUDE_COLDSTART_DISABLE=1`.
- **Succession** (`succeed.sh` + `/ag-succession`). The `Stop` hook reads the context size from the transcript. Past `LEX_CLAUDE_HANDOFF_TOKENS` it blocks once and invokes the skill. The skill writes a briefing from the live context, then `succeed.sh run` spawns a successor, has the master check its identity and then its first move on the work, and rerolls on failure. On pass it prints `claude --resume <id>`, plus a kickoff prompt in continue mode so the successor starts working without a nudge. With `--open` it opens the resume in a new cmux workspace, iTerm window, or Terminal window, through `ag claude`, so both sessions share the same model and permission mode. On pass it also records the lineage (`state/lineage/<id>`: generation and predecessor id), which the statusline shows as `genN ←<id>`. On exhaustion it stops and native compaction takes over.
- **Watch** (same `Stop` hook). In continue mode the handover stores the briefing and a countdown under `~/.claude/lex-claude/state/.succession/watch/<id>.*`. For the successor's first `LEX_CLAUDE_WATCH_TURNS` turns the master judges each finished turn against the briefing. Off track, the hook blocks once with the reason. It never blocks twice in a row. An explicit user instruction always counts as on track.
- **Tutelle** (`/ag-succession` step 4). The predecessor keeps its full context and watches too. `succeed.sh run --from <peer>` tells the successor to message the predecessor by its `ListAgents` name once resumed. That message only gives the predecessor its address. The predecessor runs `Monitor` on `succeed.sh peek <id>`, which reads the successor's transcript and emits one line per finished turn, reads each one with `succeed.sh turn <id>`, and messages a correction when needed. The successor is never pinged for status. After the watched turns it stands down and its window can be closed.

`etat.sh` at `SessionStart` injects the active identity and the live git line. That is the état the opener reports and the master verifies against.

The flow lives at the harness level, so every identity gets it. Codex has no hooks, so no succession there.

Kill switch: `LEX_CLAUDE_HANDOFF_DISABLE=1` disables the trigger, the watch and the succession. `git revert` + `ag update` removes the wiring.

## Project memory (persistent across sessions)

The `etat.sh` SessionStart readout is pure live state (active identity + git); it does not accumulate what mattered across sessions. `memory.py` adds a small, deliberately narrow per-project memory of durable, repo-specific items (decisions, facts, open threads, preferences) under three rules, ported from the `elastic-substrat` probe. Narrow on purpose: no environment or machine state (paths, live branch, cluster/server state, transient config), which goes stale silently and is worse than no memory.

1. **Forget by use.** Items not reaffirmed decay and are pruned (bounded store, self-cleaning), so old noise does not accumulate.
2. **Write-time supersession.** When a session makes a stored item outdated (a decision reversed, a value changed, a thread closed), it is soft-deleted, not destroyed. Soft, so a wrong supersession is recoverable: the item is restored if a later session reaffirms it.
3. **Recall by salience.** Session start injects the live subset (salience-ranked), not the whole file.

The judgment (what is durable, what is superseded) is written by the live Claude session, piloted by the `/ag-close` and `/ag-succession` rituals, not by a spawned model. The live assistant already holds the full session context and persona, so its extraction beats a cold side-process, and there is no second model to pay for and no recursion risk. `memory.py` does only the deterministic bookkeeping and never calls a model. Both touchpoints fail-open (any error leaves the store and the session untouched):

- **Write (`/ag-close` and `/ag-succession` skills):** the live session runs `memory.py list <slug>` to see the current items with their ids, then pipes a JSON delta to `memory.py apply <slug>`: `new` durable items, `supersede` the ids this session made outdated, `reaffirm` the ids confirmed still true. Voluntary: forgetting to close costs that session's delta, nothing breaks. Kept narrow and repo-specific by the skills' guidance, never environment/machine state.
- **Recall (`etat.sh`, SessionStart):** appends `memory.py recall <slug>`, a fast pure-ranking read (no model, no embeddings) of the live items, grouped by type.

State: `~/.claude/lex-claude/state/<slug>/memory.jsonl` (one JSON item per line). Stdlib only, no model spawned, no embeddings. Kill switch: `LEX_CLAUDE_MEMORY_DISABLE=1` (and `LEX_CLAUDE_DISABLE=1` also stops it). The design and its validation (why forget-by-use plus recoverable supersession beats keep-all and LRU, and why the read-time variant failed) live in `~/Documents/magiclex/elastic-substrat/HANDOFF.md`.

## Skills included

All custom skills are prefixed `ag-` to avoid drowning in native skills or other plugins. Exception: `ag` itself, which is also the name of the `/ag` slash command.

- `ag`: surface the current lex-claude state (active identity, installed skills, doctor, version). Invoke via `/ag`.
- `ag-invariants`: audit a project against 15 universal invariants (errors, tenant isolation, secrets, mutation feedback, migrations, containers, mocks, deploy, billing, public tokens, upstream-failure handling, stabilised patterns, lifecycle-owned resources) plus a conditional kill-switch check for host-injected components. Use during dev or before merge.
- `ag-review-project`: read project docs (CLAUDE.md, PHILOSOPHY, CONTEXT, PRINCIPLES, INVARIANTS, OPS, TODO) and produce a sharp summary of state and next actions.
- `ag-exploration`: explore an unfamiliar topic, codebase, or domain as a senior practitioner. Outputs five fixed sections (load-bearing concepts, common misconceptions, stable vs hype, where to dig, first concrete move).
- `ag-docs-init`: scaffold the standard `docs/` layout (PHILOSOPHY, CONTEXT, PRINCIPLES, INVARIANTS, OPS, TODO) with empty headers. Skips existing files. Use to bootstrap a project.
- `ag-docs-cleanup`: audit the project's docs for staleness, archives, dead refs, and duplicates. Reports a punch list, never edits.
- `ag-succession`: hand this session's work to a fresh, verified successor near the context limit. Persists narrow memory, composes a live briefing, then drives `succeed.sh run` to spawn a successor, have the master verify identity + project understanding, reroll on failure, and stand down once one passes. Triggered automatically by the `Stop` hook past the token threshold; also invokable by hand.
- `ag-close`: close a work slice by hand (no successor spawned). Commit/push check, docs-in-step check, and a narrow, repo-specific project-memory update. Use on "on ferme", "wrap up", "c'est bon pour aujourd'hui".
- `ag-co-scientist`: run a co-scientist loop on a research goal (generate, critique, pairwise-debate ranking, evolve, meta-review) with subagents. Delivers an evidence matrix, ranked hypotheses and discriminating experiments for the user to review.
- `ag-cheetah`: Cheetah 0.8 conventions, gotchas and RL environment pattern, with `scripts/cheetah_xsuite_check.py` (Cheetah vs Xsuite agree to 1.6e-7 with `drift_kick_drift`).
- `ag-xsuite`: Xsuite (xtrack 0.95) coordinates, Environment/twiss/match/MAD-X workflow verified by `scripts/xsuite_smoke.py`.
- `ag-fair-data`: formats (Parquet, HDF5, openPMD, NeXus, Zarr, NetCDF), loaders, time series, ML pipelines, metadata, releases.
- `ag-workspace`: PARA work_space organisation, templates for every item type, `scripts/new_item.sh` scaffolding, naming, lifecycle, hard exclusions for credential stores.
- `ag-voice`: write in the user's voice. One DNA (physics does the arguing, causal chains, candid on setbacks, parentheses for precision), four registers: paper, EU proposal, French institutional, email. Calibrated on the user's corpus (`Voice.md`), which stays on their machine.

### Vendored science skills

27 skills from K-Dense-AI/scientific-agent-skills, flonat/flonat-research and obra/superpowers: scientific reasoning (critical thinking, hypotheses, brainstorming, experimental design, statistics, units), literature and writing (literature review, citations, paper lookup, writing, peer review, visualization, review response, proofread), ML/RL/optimization (stable-baselines3, pufferlib, pymoo, pytorch-lightning, scikit-learn, shap, pymc), engineering (systematic debugging, verification before completion). They keep their upstream names (no `ag-` prefix). Pinned commits, patches and licenses: `THIRD_PARTY.md`. Update with `./vendor.sh`, never by editing in place.

## Repo structure

```
lex-claude/
├── .claude-plugin/
│   └── plugin.json              ← Claude Code plugin manifest
├── bin/lex-claude               ← CLI
├── bin/pkgdev                   ← Python package branch switcher (deployed alongside ag)
├── hook.sh                      ← SessionStart hook
├── etat.sh                      ← SessionStart état: active identity + live git + memory recall
├── master.sh                    ← drift authority: judges identity/rules/project load
├── succeed.sh                   ← Stop-hook token trigger + successor watch + succession reroll loop
├── memory.py                    ← persistent project memory: forget-by-use + write-time supersession
├── watch.sh                     ← SessionStart watchPaths + FileChanged staleness nudge
├── digest.sh                    ← UserPromptSubmit rules-digest re-injection
├── style.sh                     ← PostToolUse em-dash check on user-facing md
├── usage.sh                     ← usage logger + `ag usage` report (debloat aid)
├── statusline-command.sh        ← managed statusline
├── RULES.md                     ← canonical shared rules
├── THIRD_PARTY.md               ← vendored skill sources, commits, patches
├── vendor.sh                    ← re-vendor third-party skills at pinned commits
├── licenses/                    ← upstream license texts
├── DIGEST.md                    ← condensed rules digest (kept in step with RULES.md by hand)
├── identities/
│   ├── betatron.md              ← default: accelerator physics + RL co-scientist
│   ├── gantt.md                 ← EU project manager and proposal writer
│   ├── lattice.md               ← research software engineer (pipelines, HPC, CI)
│   └── nolen.md                 ← grug-style simplicity checker
├── skills/
│   ├── ag/SKILL.md
│   ├── ag-invariants/SKILL.md
│   ├── ag-review-project/SKILL.md
│   ├── ag-exploration/SKILL.md
│   ├── ag-docs-init/SKILL.md
│   └── ag-docs-cleanup/SKILL.md
└── README.md
```

## Adding an identity (manual or CLI)

CLI: `ag identity new --name pierre --desc "senior security engineer, 20 years in infosec, dry humour"` → file created, rules inlined, commit + push auto.

Manual: create `identities/<name>.md` with a prelude + the `<!-- LC_RULES_BEGIN --> <!-- LC_RULES_END -->` markers, then `ag rules sync` to inject the content.

## Editing the shared rules

Edit `RULES.md`, commit, push. On your machines: `ag update` (or wait for auto-update within 24h). Every identity is resynced automatically. If the edit changes a load-bearing rule, condense it into `DIGEST.md` in the same commit.
