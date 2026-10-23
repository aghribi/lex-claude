---
name: ag-dev-harmonise
description: Organise a research project's `_development` area across code hosts (GitLab, GitHub), compute sites (clusters, EOS, laptops) and data locations - one clone per repo per site, versions as branches and tags, results at the sites with one run index, input provenance per run, a map read_me. Use when the user asks to harmonise, clean up, consolidate or organise a dev project's code and data across machines, or to apply "the FCCee method" to another project.
---

Reference execution: FCCee, Oct 2026 (`projects_active/FCCee/_development/read_me.md`, xsuite_heb `code/build_run_index.py`). Read them before starting: they are the worked example.

Target state:
- Code lives on the code host. Each site holds clones, never copies. One clone per repo per site at a fixed path; a second version is a `git worktree`.
- Versioning: a branch per big evolution (physics model, input set, output schema, breaking CLI), an annotated `vN.M` tag per small one, a version table on `master`. Every run records `code_branch`, `code_version` (`git describe`), `code_commit`.
- Results live at the compute sites, in one primary store per project. The laptop holds only data needed for an analysis, a presentation, a report or a publication.
- One Parquet run index over the primary store, built by a script in the repo.
- Each run records its input files: path, sha256, upstream `repo@branch:commit`.
- `_development/read_me.md` is the map: repositories, compute sites (code and data paths), versions, run index. The project `read_me.md` points to it.

## Phases

Plan first, get approval, then one phase at a time. Report each phase before the next.

**P0 Audit and safety.** Per site: every repo (remote, branch, unpushed commits, dirty files), duplicate clones, folders that are snapshots without `.git`, data folders with sizes, quotas. Push unpushed work first. Deliver the audit as findings grouped by severity; fix only after triage.

**P1 One clone per repo per site.** Before retiring a duplicate clone or folder copy, compare every file to the branches by blob hash (`git hash-object --no-filters <file>` against `git ls-tree -r <branch>`). Map paths correctly (copy `code/vX/` against branch `vX` `code/`). Files found nowhere go into git as commits: one orphan branch `archive/<site>-<year>` with a README, never a tarball. Then the user runs the deletion.

**P2 Snapshots to clones.** For a folder copied from a repo: `git init`, add the remote, fetch, find the commit whose tree matches best, `git reset <commit>` (mixed, files untouched). Local edits go to a branch. No upstream match: record it as not in git in the map.

**P3 Data.** Copy to the primary store with `rsync -a`. Verify with per-file sha256 manifests built the same way on both sides (a small Python `os.walk` + `hashlib` emitting sorted JSON, then compare digests; parsing `sha256sum` output breaks on escaped filenames). Write a `PROVENANCE.md` in each migrated folder (origin, date, file count, verification). Only then delete the source. Build the run index:
- managed rows from the run manager metadata, unmanaged rows from a walk of the store (a run dir has `data/` with output files or is empty), nearest `PROVENANCE.md` for unmanaged rows;
- explicit dtypes, timezone-aware timestamps, units and builder version in the Parquet schema metadata;
- atomic writes (`tempfile.mkstemp` in the target dir, `os.replace`), output paths confined to the store root;
- reconcile stale status: a run marked running whose scheduler job is gone (`squeue`, `sacct`) becomes interrupted, with the final job state logged; `--dry-run` writes nothing; a second pass marks nothing.
Names are not unique keys: check duplicate ids by file hashes (identical, subset, disjoint) before calling anything a duplicate; key the index on path.

**P4 Inputs and docs.** Each run writes its input record into the run metadata and the output file. Placeholder upstream commits (manual placement, dry runs) are resolved by matching the recorded sha256 against the upstream file history, not by re-fetching: a re-fetch can silently change the inputs. Check the upstream HEAD too and report any input that differs (physics values, not only bytes). Fix dead paths in docs. Write the map. Update the master version table and tags, push, pull on every site.

## Rules for this work

- Ask before running jobs on a cluster. A doubtful input or spec stops the run.
- Remote deletions: list the exact paths and their verification, the user runs `! ssh <site> rm ...`. Never work around a denied delete.
- Shared folders: check the owner (`ls -l`, `stat`) before any write. Files owned by someone else are never moved, renamed, edited or deleted; read and index only, and report them to the user.
- Never read credential stores; tokens and keys are used only through the tools that need them (ssh, git), never printed.
- Moves and archives are proposed as a list and executed after confirmation.

## Gotchas

- `git rev-list --objects` overcounts new objects when histories are disjoint (orphan branch): use a set difference against the remote's objects.
- `comm` needs `LC_ALL=C sort` on whole lines.
- zsh does not word-split `$var`: pass arguments explicitly.
- CERN lxplus with many keys in the agent: `PubkeyAuthentication no` in the host block (GSSAPI or password plus OTP).
- `du` on network filesystems reports block overhead; size data with `os.stat().st_size` sums.
- A folder synced by CERNBox or similar: deleting locally deletes on the sync service too.
