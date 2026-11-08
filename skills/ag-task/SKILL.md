---
name: ag-task
description: Set, list or close a task in the user's task store (one note per task in the Obsidian vault, 05_tasks/), linked to the project, tags and this session. Use when the user says "/ag-task", "add a task", "put it on my todo list", "remind me to", "what are my tasks", or closes one ("done with X").
argument-hint: "<text> [#tag] [@project] [due YYYY-MM-DD] | list | done <ref>"
---

Tasks go through `ag task`. It records the project (from the folder), the session id and the resume command. Never write task notes by hand.

Request: $ARGUMENTS

- **Add** (default): `ag task add "<text> [#tag ...] [@project]" [--due YYYY-MM-DD] [--note "<line>"]` (tags and project inside the quotes: an unquoted `#` starts a shell comment). Keep the user's wording for the text. Add a tag or a due date only when the user gave one. A task for another project takes `@<project>` (a key or alias from `05_tasks/projects.yaml`).
- **List**: `ag task list` (all projects), `ag task list --here`, `-p <project>`, `-t <tag>`, `-s waiting|done|all`.
- **Close or park**: `ag task done <ref>`, `ag task status <ref> waiting`. `<ref>` is part of the file name from `list`; if it matches several, show them and ask.

Report the command's output line, nothing more. If the project printed is wrong, say so and, once the user confirms, edit the `project:` field of the note (`ag task show <ref>` prints its path).
