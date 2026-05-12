---
description: Deliberate on go-to-market positioning
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [positioning-question]
---

Run a Council deliberation on a go-to-market or positioning decision.

Read the product-orchestrator skill for the full orchestration protocol. Then read `references/gtm-templates.md` for the four role prompts (Customer Voice, Market Analyst, Revenue Architect, Contrarian Advisor).

Steps:
1. If a PRD exists in the workspace, load it for context (especially Problem, Target User, and Competitive Landscape). If not, ask the user for: product name, target user, current positioning (if any), and the specific GTM question.
2. Build the product context block as defined in the SKILL.md.
3. Invoke the Council deliberation-engine skill with the GTM role prompts and voting protocol.
4. Parse the synthesis into positioning statement, messaging hierarchy, pricing recommendation, and distribution plan.
5. Present the decision to the user.
6. If approved, write a PD decision record to the vault (if accessible).
7. If a PRD exists, update it with GTM decisions and bump its status.
8. Suggest next steps: route to `copywriting`, `pricing-engine`, `launch-strategy`, or `content-strategy` for execution.

The GTM question is: $ARGUMENTS

If no arguments provided, ask the user what positioning or go-to-market decision needs deliberation.
