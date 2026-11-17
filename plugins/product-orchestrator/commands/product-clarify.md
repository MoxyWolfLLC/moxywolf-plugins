---
description: Scan a PRD for ambiguity and coverage gaps, then resolve them with up to 5 targeted questions encoded back into the PRD
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
argument-hint: [prd-path-or-product-name]
---

Run a structured clarification pass on a PRD before it goes to architecture deliberation. Concept-ported from spec-kit's `/speckit.clarify` (MIT) — the ambiguity-scan discipline, re-specified for the product-orchestrator PRD flow. See DR-004's clarify follow-on.

Read the product-orchestrator skill for context, then read `references/clarify-protocol.md` for the ambiguity taxonomy, the question-selection heuristic, and the encode-back rules.

Steps:

1. **Locate the PRD.** Load the PRD named in $ARGUMENTS, or the most recent `PRD-*.md` in the workspace. If none exists, tell the user to run `/product-prd` first — clarify operates on an existing PRD, it doesn't create one.
2. **Coverage scan.** Walk the PRD against the ambiguity taxonomy in the protocol. For each category, mark Clear / Partial / Missing. Build the coverage map internally (don't dump it unless no questions are warranted).
3. **Prioritize.** Queue at most 5 candidate questions, ranked by Impact × Uncertainty. Only include questions whose answers materially change architecture, data model, task decomposition, scope, or verification. Exclude anything already answered, stylistic, or pure execution detail.
4. **Ask one at a time.** Use AskUserQuestion, exactly one question per turn, each answerable from a short option set or a one-line answer. Never reveal the queue. Stop early once the critical ambiguities are resolved; never exceed 5.
5. **Encode back.** After each accepted answer, write it into the right PRD section (not a scratchpad), and append a `- Q: <question> → A: <answer>` bullet to a `## Clarifications ({date})` block. Replace any statement the answer invalidates — leave no contradictory text. Load the `asd-ste100` skill (ST-003) and rewrite the prose you write into the PRD section in its Strict mode. The `- Q: … → A: …` bullet keeps the user's answer verbatim, and so do any words the prose quotes from it. Text that quotes Dorian or a user's answer stays verbatim. The skill's suggestions and `ste-lint.py`'s findings are advice and never gate design, review, merge or release.
6. **Report.** Summarize: questions asked/answered, categories still Partial/Missing (as explicit Deferred items with rationale), and the recommended next step (`/product-scope` or `/product-arch`). End with one line: `asd-ste100: <n> rewritten, <m> kept as-is` (counts combined across this run), then upstream's `Kept as-is:` line for each kept phrase; or `asd-ste100: not installed` when the skill is missing, and go on. Leave the line out when the run never reached the pass.

If the scan finds no material ambiguities, say "No critical ambiguities detected worth formal clarification" and suggest advancing — do not manufacture questions.

The target PRD is: $ARGUMENTS

If no arguments provided, look for the most recent PRD in the workspace and confirm it with the user before scanning.
