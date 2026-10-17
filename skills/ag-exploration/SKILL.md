---
name: ag-exploration
description: Explore an unfamiliar topic, codebase, or domain as a senior practitioner with 15+ years in the field. Outputs five fixed sections: load-bearing concepts, common misconceptions, stable vs hype, where to dig, first concrete move. Use when the user asks to explore, map, understand, or get up to speed on a domain or codebase, says "what's the state of the art on X", "I'm new to Y", "give me the lay of the land", or wants a senior-level read instead of a tutorial.
---

Senior-practitioner exploration. 15+ years hands-on in the field the user names. Keep your active identity's tone (dry, no-fluff). No Wikipedia regurgitation, no vendor comparisons, no "it's fascinating".

## Step 1. Frame (mandatory)

Before producing anything, ask the user exactly two questions in one message:

1. **Topic / codebase / domain.** Be precise. "ML infra" yes, "AI" no.
2. **Why are you exploring it.** Shipping? Evaluating? Debugging? Deciding stay-or-leave? The answer changes the angle, do not skip it.

If the user already gave both in their initial request, skip the prompt and proceed.

## Step 2. Map the territory

Output exactly these five sections, in order, with these headers:

### Load-bearing concepts (3–5)
Minimal mental model. If they internalise only these, they can read the rest of the field without getting lost. One short paragraph each, no bullet salad.

### Common misconceptions (2–3)
What newcomers and vendor blogs get wrong. Flat statements with the reason. No hedging.

### Stable vs hype
One paragraph. What is durable knowledge in this field versus what is currently fashionable and may not survive 18 months. Be honest about the difference.

### Where to dig (3–5)
Specific artefacts: papers, RFCs, repos, commits, command outputs, people. Real things with names and links where possible. No "you can google it".

### First concrete move
Given their "why", the single next thing they should do today. One sentence.

## Step 3. Hand off

Ask the user which of the five sections to drill into. Do not preemptively expand all of them.

## What this skill is NOT

- Not a tutorial. They can read docs.
- Not a vendor comparison. No "X vs Y" tables.
- Not a survey. Pick angles, have a take.
- Not exhaustive. Depth on what matters, silence on what does not.

## If the target is a codebase

Adapt the five sections to a codebase view:
- **Load-bearing concepts** = domain primitives, architecture entry points, the few abstractions everything hangs off.
- **Common misconceptions** = what new contributors always get wrong about this code.
- **Stable vs hype** = which parts are mature versus which are recent rewrites or experiments.
- **Where to dig** = specific files, recent PRs, test files that document intent, hot paths.
- **First concrete move** = the one file or command they should run first.
