# Third-party content

Vendored skills are copied by `vendor.sh` at the pinned commits below, then patched. Never edit them in place: change `vendor.sh` and re-run it. License texts are in `licenses/`.

| Source | Commit | License | Skills |
|---|---|---|---|
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | `a1043ef` | MIT | scientific-critical-thinking, hypothesis-generation, scientific-brainstorming, experimental-design, statistical-analysis, uncertainty-and-units, literature-review, citation-management, paper-lookup, scientific-writing, peer-review, scientific-visualization, stable-baselines3, pufferlib, pymoo, pytorch-lightning, scikit-learn, shap, pymc |
| [flonat/flonat-research](https://github.com/flonat/flonat-research) | `da27600` | MIT | devils-advocate, numerical-check, verify-math, computational-experiments, review-response, proofread |
| [obra/superpowers](https://github.com/obra/superpowers) | `bb92a77` | MIT | systematic-debugging, verification-before-completion |

## Patches

- **K-Dense:** the "Citing Scientific Agent Skills" section is removed. It instructs the agent to add K-Dense's paper to the user's manuscripts. Authorship stays in each skill's frontmatter.
- **obra:** `superpowers:` references point to the vendored skill names; the TDD skill reference becomes a plain instruction.

## Known soft dependencies

These skills mention flonat infrastructure that is not vendored (`.context/`, `review-cluster`, `referee2-reviewer` agent, Task Management templates). The mentions are conditional ("if it exists", "suggested next step"); the skills work without them.

- `literature-review`, `citation-management`, `paper-lookup`: optional API keys (`OPENALEX_API_KEY`, `NCBI_API_KEY`, `CORE_API_KEY`) raise rate limits. `literature-review` uses `OPENROUTER_API_KEY` / `PARALLEL_API_KEY` for some search modes.
- `pufferlib`, `pytorch-lightning`: optional experiment-tracker keys (W&B, Comet).

## Rules

The "Co-scientist" section of `RULES.md` condenses rules from flonat-research (design-before-results, mark-unverified, doi-verification, no-hardcoded-results, paper-code-consistency, severity-gradient, scope-discipline, audit-before-fix, plan-first, latex-hygiene, overleaf-separation, python-uv) and the co-scientist principles in Causaly's [Building the AI co-scientist](https://www.causaly.com/blog/building-the-ai-co-scientist-for-the-hardest-part-of-science).

## Considered, not vendored

- `flonat/pre-submission-report`: orchestrates about 10 flonat agents that lex-claude does not deploy.
- `obra/brainstorming`: its trigger ("MUST use before any creative work") hijacks ordinary tasks; overlaps `scientific-brainstorming`.
- `obra/writing-plans`: depends on other superpowers skills; covered by the plan-first rule and plan mode.
- `K-Dense/research-lookup`: requires a paid OpenRouter or Parallel key.
- [Kaimen-Inc/Co-Scientist](https://github.com/Kaimen-Inc/Co-Scientist) (Apache-2.0): full Python reimplementation of Google's co-scientist (SQLite queue, Elo tournament, FAISS). Usable as a heavy engine through its `claude -p` backend. `lc-co-scientist` runs the same loop with Claude Code subagents instead.
- [panjose/Co-Scientist](https://github.com/panjose/Co-Scientist) `co-scientist-run`: only drives that repo's own pipeline.
