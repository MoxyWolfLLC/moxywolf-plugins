---
description: Generate a Product Requirements Document
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [product-name-or-description]
---

Generate a PRD for the product or feature described in $ARGUMENTS.

Read the product-orchestrator skill (trigger it by context — this is a product orchestration task). Then read `references/prd-template.md` from the product-orchestrator skill directory for the PRD format and interview protocol.

Follow the PRD interview process to extract required inputs from the user. Ask only what the user hasn't already provided in their arguments or prior conversation. Use AskUserQuestion for structured questions.

Before saving, load the `asd-ste100` skill (ST-003) and rewrite the PRD's requirements and acceptance criteria in its Strict mode. Leave the rest of the PRD as written. Text that quotes Dorian or a user's answer stays verbatim. The skill's suggestions and `ste-lint.py`'s findings are advice and never gate design, review, merge or release.

After generating the PRD:
1. Save it to the workspace folder as `PRD-{product-slug}.md`
2. Present a summary to the user
3. Suggest which deliberation to run next based on the PRD's open questions, risks, and gaps:
   - Scope ambiguity → suggest `/product-scope`
   - Technical unknowns → suggest `/product-arch`
   - NFRs or dependencies surface architecture questions → suggest `/product-arch`
   - Positioning unclear → suggest `/product-gtm`
   - High-likelihood unmitigated risks → suggest `/product-scope` to reconsider scope
   - PRD is crisp → suggest `/product-sprint`
4. End the report, after the next-step suggestion, with one line: `asd-ste100: <n> rewritten, <m> kept as-is` (counts combined across this run), then upstream's `Kept as-is:` line for each kept phrase; or `asd-ste100: not installed` when the skill is missing, and go on. Leave the line out when the run never reached the pass
