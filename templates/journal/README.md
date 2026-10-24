# Project journal

Work state of this project, for the people and the agents working on it. Read at the start of every Claude session opened inside this project (STATUS.md only, capped). Nothing here is loaded outside the project.

| File | Content | Rule |
|---|---|---|
| `STATUS.md` | Now, Next, Waiting on, Issues, Recent results, Last sessions | Rewritten, never appended. Kept under the line cap (`ag journal check`). |
| `RESULTS.md` | One entry per result, with its evidence | Append-only. A correction is a new entry that names the one it replaces. |
| `sessions/<YYYY-MM-DD>_<identity>_<id8>.md` | One note per session | Written at close or handoff, never edited after. |

## When to update

- Task done, result obtained, decision taken, issue found: update `STATUS.md` then, not only at the end. A session that dies loses little.
- Close (`ag-close`) or handoff (`ag-succession`): write the session note, rewrite `STATUS.md` (move finished items out of Now, add the session to Last sessions, drop the oldest beyond five).

## STATUS.md

What IS, not what was tried. One line per item, a pointer for detail (commit, file, issue, result id). Dates absolute. No machine state that changes by itself (queue contents, "running now"): name the job id and where to check it.

## RESULTS.md entry (example)

```
## R-0007 · 2026-10-24 · Microwave threshold vs RF frequency
- value: N_th = 3.04e10 (600 MHz), 3.11e10 (650 MHz), 3.22e10 (800 MHz) [particles per bunch]
- method: sigma_delta ratio crosses 1.05, last 20 % of turns (studies/v22_microwave_scan.yaml)
- code: xsuite_heb v22.10, image fccee_sim-a3159ab22c7b
- runs: 18 runs, 1 seed per point, cc
- evidence: /sps/m4cast/FCCee/_results/views/v22_microwave_scan/thresholds.parquet
- status: observation (not reproduced)
```

Status: `observation` until reproduced (other seed, site or method), then `reproduced`. A replaced entry gets `status: superseded by R-xxxx`.

## Session note

```
# 2026-10-24 · nolen · 492d3e42
Transcript: claude --resume <full session id>
## Asked
## Done        (commits, tags, jobs with ids)
## Results     (R-ids)
## Issues      (found, fixed or open)
## Left open
```
