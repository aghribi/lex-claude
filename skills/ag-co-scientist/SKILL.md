---
name: ag-co-scientist
description: Run a co-scientist loop on a research goal - generate competing hypotheses, critique them, rank them by pairwise debate, evolve the best, and deliver a reviewable research overview with an evidence matrix and discriminating experiments. Use when the user asks for hypotheses, explanations for an observation, research directions, "what could explain X", "why does the agent/beam/model do Y", or says "co-scientist" or "brainstorm hypotheses rigorously".
---

Co-scientist loop, after Google's AI co-scientist (Gottweis et al., Nature 2026: Generation, Reflection, Ranking, Evolution, Meta-review) with Causaly's output format (evidence matrix, falsification first, human review gate). Runs on Claude Code subagents, no external service.

The Co-scientist rules in the active identity apply throughout: no invented citation or number, `[UNVERIFIED]` with its dossier, claim strength stays honest.

## Step 1. Frame (mandatory)

Restate in at most five lines and get confirmation before spending compute:

- **Goal.** The question, as one sentence.
- **Observations.** What is known and from where (files, runs, papers the user gave). Read them now.
- **Constraints.** What can actually be tested (simulator, beam time, compute, data at hand).
- **Budget.** Default: 6 hypotheses, 1 evolution round. User can raise it.
- **Output path.** Default `docs/co-scientist/<YYYY-MM-DD>-<slug>.md`.

## Step 2. Generate (parallel)

Launch 3 subagents in one message, each with the framing and a different angle:

1. **Literature-grounded.** Search the literature (`paper-lookup`, arXiv, INSPIRE for accelerator physics) and propose hypotheses supported by prior work. Every reference verified before it is cited.
2. **Mechanistic / first principles.** Derive hypotheses from the physics, math or algorithm involved. Derivations shown, not asserted.
3. **Contrarian.** Assume the obvious explanation is wrong. Propose artefact, bug, measurement and confounder explanations.

Each returns 2 to 3 hypotheses: statement, mechanism, testable prediction, what would falsify it, supporting refs or derivation.

## Step 3. Reflect

One subagent reviews every hypothesis on: correctness against the observations, novelty, testability with the stated constraints, hidden assumptions. It lists each hypothesis's load-bearing assumption and whether it is checked. Drop hypotheses already contradicted by an observation; keep them in an "eliminated" list with the reason.

## Step 4. Rank by pairwise debate

Compare survivors in pairs (round robin up to 6, otherwise top pairs by reflection score). For each pair, a short debate: which one better explains all observations with fewer unchecked assumptions, and which is cheaper to test decisively. Tally wins. Report the ranking with the one-line reason per match.

## Step 5. Evolve (one round by default)

For the top 2 to 3: combine compatible ones, simplify, make more testable within constraints, or reframe out of the box. New variants go through Steps 3 and 4 once. Stop when the ranking is stable or the budget is spent; say which.

## Step 6. Meta-review and deliver

Write the output file, then present a summary in chat. The file has:

- **Goal and observations** (with sources).
- **Evidence matrix.** Rows: observations. Columns: surviving hypotheses. Cells: supports / contradicts / neutral / unknown.
- **Ranked hypotheses.** For each: statement, mechanism, what supports it, what contradicts it, claim strength (consistent with < associated with < predicts < causes).
- **Discriminating experiments.** For the top hypotheses, the cheapest experiment or simulation whose result would change the ranking, and the expected outcome under each hypothesis. Hand off to `experimental-design` or `computational-experiments` if the user wants to run it.
- **Eliminated hypotheses** with the reason.
- **Why the search stopped** and what missing evidence could change the conclusion.
- **Unverified items** with their dossiers.

End by asking the user which hypotheses to pursue. Do not start experiments on your own.
