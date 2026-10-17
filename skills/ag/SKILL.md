---
name: ag
description: Surface current lex-claude state. Active identity, installed skills, install health (doctor), CLI surface, version. Use when the user types /ag, asks what's loaded globally, asks which lex-claude version is running, or wants a sanity check that the install is healthy.
---

Run these and report concisely:

- `ag identity` — list identities, mark active.
- `ag doctor` — install health (CLAUDE.md, AGENTS.md, hooks, skills, CLI on PATH).
- `ls -1 ~/.claude/skills/` and `ls -1 ~/.codex/skills/` — globally installed skills.

Then echo the CLI surface in one line:

```
ag install | update | identity [<name>] | identity new --name <n> --desc "<d>" [--empty] | rules sync | doctor
```

If `ag` is missing from PATH, suggest: `~/.claude/lex-claude/bin/lex-claude install`.
