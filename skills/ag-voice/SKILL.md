---
name: ag-voice
description: Write in the user's own voice (A. Ghribi, accelerator physics, cryogenics, AI for accelerators). Use whenever drafting anything signed or submitted in the user's name - EU proposal sections (Part B, WPs, KPIs, impact), papers and technical notes, French institutional writing (HDR, CNRS/DR projects, reports), emails and abstracts. Also on "write this as me", "in my voice", "draft my section", "rédige comme moi".
---

The user's voice. One DNA, four registers. Pick the register first, then write.

Ground truth is the corpus listed in the user's `Voice.md` (Obsidian work vault; ask for the path if it is not obvious). The single-author texts carry the voice: the HDR manuscript first, then the user's own sections of EU proposals. Multi-author proposal text is diluted; `projet_recherche_dr_cid55_optimise` shows heavy em-dash use (about 60x the HDR rate) and is treated as AI-polished, not as ground truth. Read the corpus before any long draft; these rules are the distillation. Never copy passages from unpublished proposals into other documents or this repo.

## The DNA (every register)

- **The physics does the arguing.** Quantities with units and orders of magnitude (∼0.25 K, ±5 mbar, 100 Hz), named machines, components and labs. No adjective where a number or a name fits.
- **Causal chains.** Observation, consequence, action, in that order, linked by plain connectives: "donc", "thus", "then", "the latter" / "ce dernier". Requirements are justified by what they buy (noise, stability, cost).
- **Candid about what went wrong.** Setbacks are stated flat, with the cause and the fix (a component found burnt, an oscillation that broke regulation). Success gets one short sentence, no fanfare.
- **Didactic when explaining.** Walks the reader through: "let us first look at", "take the case of", "examinons d'abord", "prenons le cas de", "divisons maintenant". Explains before claiming.
- **Parentheses for precision.** Acronym expansions, partner and site names, figure and section references, units. Frequent (about 1.5 per 100 words); that is part of the voice.
- **Sentences of medium length**, median 18 to 22 words, with long technical ones next to short conclusive ones. No fragment chains.
- **Low boosters, low hedges.** "Novel", "crucial", "cutting-edge" only when a number backs them. Uncertainty is stated as a quantity or a condition, not as "may potentially".
- **Em dashes rare** (about 6 per 10,000 words in the HDR). Use commas, colons, parentheses.

## The registers

| Register | Venue | Notes |
|---|---|---|
| Paper / technical note (EN) | Journals, conference proceedings, internal notes | Results first, method in the order it was done, "we". Figures and tables carry the numbers; the text says what they show. No storytelling. |
| EU proposal (EN) | Horizon Europe Part B: excellence, impact, implementation | Structure carries it: WP, Task, Subtask labels, KPIs tagged in brackets (`[KPI 2.1]`), partners by acronym and role. "The project will", "this task will". Sequencers (firstly, secondly, finally) for arguments. One plain memorable line per section at most. Every impact claim tied to a KPI, a deliverable or a facility. British spelling (organisation, utilisation). |
| French institutional (FR) | HDR, CNRS/DR applications, activity reports | Narrative and chronological, dated ("dès juillet 2016"). "Nous" for team work, "je" for own initiatives, coordination and the personal arc. Plain idioms allowed sparingly ("qu'à cela ne tienne"), understatement over enthusiasm. Passé composé and imparfait for the story, present for the state of things. |
| Email / short form | Collaborators, EU officers, abstracts, forms | No corpus samples yet: ask for 3 to 5 sent emails before a long or sensitive one. Default: greeting, the fact or the ask in the first two lines, the deadline or next step, signature. Abstracts follow the paper register in 150 to 250 words. |

Language: write in the language of the venue. French text keeps French typography (space before `:` `;` `?` `!`, guillemets « »).

## Anti-LLM pass (before showing any draft)

Adapted from the lex-claude `lc-voice` checklist, calibrated on this corpus:

1. Swap long words for short ones where meaning holds.
2. Keep median sentence length near 18 to 22 words; vary it hard (a 35-word technical sentence next to a 6-word conclusion).
3. Dedupe repeated nouns ("platform", "framework", "ecosystem" five times is a tell).
4. Kill boosters: "notably", "significantly", "crucially", "seamless", "robust", "holistic", "leverage", "cutting-edge", unless a number backs them.
5. No mic-drop sentence closing every paragraph. One landing line per section at most.
6. No "it's not X, it's Y", no "N of X before Y" cadence, no triads of adjectives.
7. Grep for em dashes and rewrite them.
8. Every number, date, partner role and facility name is from the corpus or the user. Never invented.

## Rules of engagement

- Never invent facts, dates, partners, budgets, results or KPIs. If it is not in the corpus or given by the user, ask, or mark `[UNVERIFIED]`.
- Test for every sentence: would the user say it in a collaboration meeting or write it in the HDR?
- The user is ground truth for their own voice. When in doubt, show the draft and ask for a red pen.
