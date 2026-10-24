---
name: ag-workspace
description: Organise the user's local work_space (PARA layout - projects, proposals, areas, resources, archives) - decide where a file or folder belongs, create projects, proposals, presentations, posters, conferences, publications, reviews, supervisions, trainings and applications from their templates, apply naming conventions, and move items through their lifecycle (proposal to project to archive). Use when the user asks where to put something, to create or scaffold a new project/proposal/talk/paper/event, to tidy or reorganise folders, to archive finished work, or when saving any new document into the workspace.
---

The workspace root is `$AG_WORKSPACE` (default `~/Documents/work_space`). Every item folder has a `read_me.md` (name, type, status, dates, people, IDs, purpose, folder map): **read it first** before working in a folder, and keep its status line current.

## Layout (PARA)

| Level | Folder | Holds |
|---|---|---|
| Projects | `projects_active/<NAME>` | Funded or running work. Template `template_project`; `_journal/` added by `ag journal init` |
| Proposals | `proposals_active/<YYYY>_<CALL-OR-NAME>` | Applications for funding in preparation. Template `template_proposal` |
| Shared spaces | `cross_sync_active/<PROJECT>` | Folders synced with partners (WPs, deliverables, correspondence, public, www) |
| Areas | `areas_active/<area>` | Ongoing duties without an end date (expertise, reviewing) |
| Resources | `resources_active/<x>_active` | Libraries, templates, administration, software, conferences material, and `_my_active` (personal outputs) |
| Archives | `archives/<level>_inactive/<YYYY>[_<YYYY>]_<NAME>` | Finished items, year-prefixed, never deleted |

Personal outputs live in `resources_active/_my_active/my_<kind>_active/` (publications, presentations, posters, conferences, reviews, tutoring, training, qualifications, applications, clusters, cv) and age into `_my_active/oh_my_archive/my_<kind>_inactive/`.

## Where does it go

1. Is it for a funding application not yet decided? `proposals_active/<YYYY>_<call>/`, in the matching `_` folder (`_part_b`, `_budget`, `_wp_descriptions`, ...).
2. Is it for running funded work? `projects_active/<project>/` (official documents, meetings, events, development, resources); code and data across machines in `_development/` follow `ag-dev-harmonise`. If partners must see it, the project's `cross_sync_active/` space.
3. Is it something the user produced (talk, poster, paper, review, supervision, training, application)? The `_my_active/my_<kind>_active/` folder, created from its template.
4. Is it reference material by others? `resources_active/` (`_pro_library_active`, `papers_to_read`, `documentary_resources_active`, `conferences_active`), or the project's `_resources/_documents/`.
5. Templates and institutional charters: `resources_active/templates_active/`.
6. Unsure between two places: put it in one, link it from the other's `read_me.md` (Related folders). Never duplicate files.

## Create from a template

`scripts/new_item.sh <type> <name> [--date YYYYMMDD] [--category DIR] [--dry-run]`: copies the template, fills name and date in `read_me.md`, refuses to overwrite. Types: `project proposal presentation poster conference publication review-article review-call supervision training application`. Run `--dry-run` first and show the destination.

Missions: the `mission` command (on PATH, from `lex-claude/bin/mission`). Bare `mission` is an interactive questionnaire for the user's terminal; from Claude always pass `mission <YYYYMMDD> <project> [--to YYYYMMDD] [--objet ..] [--lieu ..] [--transport train|avion|location|service] [--depart ..] [--retour ..] [--imputation ..] [--frais avec|sans] [--charge ganil|sans|cea] [--avance oui|non] [--dry-run]`. It creates `work_administration_active/missions/mis_<date>_<project>/{_demande,_om,_reservations,_invoices}` and fills `_demande/DEMANDE-MISSION_<date>_<project>.docx` from `templates_active/missions/DEMANDE-MISSION.docx` (Word form fields). `--help` lists every field. Accepts an existing empty folder, refuses a non-empty one.

## Naming

- Dated items (presentations, posters, conferences, trainings, meetings, events): `YYYYMMDD_<name>` (start date), inside the year folder where one exists. Older `YYYY_MM_name` folders stay as they are.
- Proposals and applications: `<YYYY>_<call-or-body>`. Archives: `<YYYY>[_<YYYY>]_<NAME>`.
- Publications: `<venue>_<topic>_<YYYY>`; in `ongoing/` until published, then in the year folder.
- Lowercase and underscores for new names; no spaces, no accents. Structural subfolders start with `_`.
- Versions in file names (`_v1_2`, `_YYYYMMDD`), not `final_final`.

## Lifecycle

- Proposal funded: create the project from `template_project`, link the proposal folder in its `read_me.md`, set the proposal status to funded. The proposal folder moves to `archives/proposals_inactive/` when the project starts.
- Proposal rejected: status rejected, keep the evaluation report in `_administration`, move to `archives/proposals_inactive/`.
- Project finished: status closing, then move to `archives/projects_inactive/<YYYY>_<YYYY>_<NAME>`.
- Publication published: move from `ongoing/` to the year folder; record the DOI in `read_me.md`.

**Every move, rename or archive is proposed as a list of operations and executed only after the user confirms.** Never delete: superseded material goes to the item's `_archive`.

## Hard exclusions

Never read, index, copy, upload or summarise: `my_vaults_active/keepass_vault`, `my_vaults_active/ssh_vault`, `my_vaults_active/github-recovery-codes.txt`, and any file that looks like a key, token or password store. The rest of `my_vaults_active` (Obsidian vaults, notes) is normal content.

## Care in shared and synced folders

`cross_sync_active/` and `_sync_exchange/` are seen by partners: other people's documents follow the "someone else's document" scope rule (suggested edits and comments, no rewrites). Do not create clutter there (build output, scratch files).

## Tidy pass (on request)

Report all findings first (audit-before-fix): items missing a `read_me.md`, names off-convention, build artifacts in source folders, duplicates, finished items still in `_active`. Group by severity, then fix only what the user triages.
