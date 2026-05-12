---
description: Deliberate on product scope decisions
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [scope-question-or-feature]
---

Run a Council deliberation on a product scope decision.

Read the product-orchestrator skill for the full orchestration protocol. Then read `references/scope-templates.md` for the four role prompts (User Advocate, Business Strategist, Ship-It Pragmatist, Long-Game Architect).

Steps:
1. If a PRD exists in the workspace, load it for context. If not, ask the user for the minimum context needed: product name, target user, and the specific scope question.
2. Build the product context block as defined in the SKILL.md.
3. Invoke the Council deliberation-engine skill with the scope role prompts and voting protocol.
4. Parse the synthesis into SHIP / DEFER / CUT lists.
5. Present the decision to the user.
6. If approved, write a PD decision record to the vault (if accessible).
7. If a PRD exists, update it with the scope decisions and bump its status.
8. Suggest next steps: `/product-arch` if technical decisions are needed, or proceed to execution.

The scope question is: $ARGUMENTS

If no arguments provided, ask the user what scope decision needs deliberation.
