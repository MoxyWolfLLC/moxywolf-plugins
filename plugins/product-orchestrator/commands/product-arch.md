---
description: Deliberate on architecture decisions
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [architecture-question]
---

Run a Council deliberation on a product architecture decision.

Read the product-orchestrator skill for the full orchestration protocol. Then read `references/architecture-templates.md` for the four role prompts (Scalability Realist, Security & Compliance Advocate, Developer Experience Champion, Migration & Evolution Strategist).

Steps:
1. If a PRD exists in the workspace, load it for context (especially Constraints and Technical sections). If not, ask the user for: product name, current tech stack, team size, scale expectations, and the specific architecture question.
2. Build the product context block as defined in the SKILL.md.
3. Invoke the Council deliberation-engine skill with the architecture role prompts and consensus protocol.
4. Parse the synthesis into technology choices, evolution triggers, and security requirements.
5. Present the decision to the user.
6. If approved, write a PD decision record to the vault (if accessible).
7. If a PRD exists, update it with architecture decisions and bump its status.
8. Suggest next steps: route to `dev-create-orchestrator`, `database-schema-designer`, or `supabase-postgres` for implementation.

The architecture question is: $ARGUMENTS

If no arguments provided, ask the user what architecture decision needs deliberation.
