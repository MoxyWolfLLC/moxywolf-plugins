---
description: Generate a Product Requirements Document
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [product-name-or-description]
---

Generate a PRD for the product or feature described in $ARGUMENTS.

Read the product-orchestrator skill (trigger it by context — this is a product orchestration task). Then read `references/prd-template.md` from the product-orchestrator skill directory for the PRD format and interview protocol.

Follow the PRD interview process to extract required inputs from the user. Ask only what the user hasn't already provided in their arguments or prior conversation. Use AskUserQuestion for structured questions.

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
