---
name: ag
description: Surface current lex-claude state. Active identity, install health (doctor), version, CLI surface.
disable-model-invocation: true
---

Report this state in a few lines: active identity, version, every `fail` or `warn` line from doctor. Nothing else.

```!
ag identity
ag doctor
```

With the direct hook wired, `/ag` never reaches this skill: the hook runs `ag doctor` without a model turn. This skill serves when the hook is off (`LEX_CLAUDE_DIRECT_DISABLE=1`). Full command list: `ag init claude`.
