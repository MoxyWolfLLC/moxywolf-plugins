---
description: Full sprint orchestration with deliberation gates
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [product-name]
---

Run a full product sprint: PRD → scope → architecture → GTM → execute → review.

Read the product-orchestrator skill for the full orchestration protocol. Then read `references/sprint-protocol.md` for the complete sprint sequence, deliberation gating rules, and execution routing tables.

Steps:

**Phase 0: PRD Check**
Check the workspace for an existing PRD file (`PRD-*.md`). If none exists, run the PRD generation flow (see `references/prd-template.md`). If one exists, present it and confirm it's still current.

**Phase 0.5: Clarify (optional, recommended for new PRDs)**
Run `/product-clarify` to resolve ambiguity and coverage gaps in the PRD before committing architecture (up to 5 targeted questions, answers encoded back into the PRD). Skip for crisp PRDs or tiny reversible changes. See `references/clarify-protocol.md`.

**Phase 1: Deliberation**
Use the sprint protocol's deliberation gating table to determine which deliberations this sprint needs. Ask the user:
- "Is this a single-session sprint or multi-day?"
- Present the recommended deliberation set and let them confirm or adjust.

Run each needed deliberation in sequence: scope → architecture → GTM. Each uses the appropriate role templates and writes a decision record.

**Phase 2: Execution Plan**
Convert deliberation outputs into a concrete, ordered task list. For each task, identify the downstream skill and estimate effort.

**Phase 2.5: Analyze (read-only consistency gate)**
Run `/product-analyze` to cross-check the PRD, architecture decisions, task plan, and `CHARTER.md` for duplication, ambiguity, charter conflicts, coverage gaps, and inconsistency. It reports; it never edits or blocks. If CRITICAL findings surface, resolve them before executing. See `references/analyze-protocol.md`.

**Phase 3: Execute**
Present the plan. On user confirmation, hand off tasks to downstream skills one at a time. Check in between tasks.

**Phase 4: Review Gate**
After execution, run the sprint review. Document what shipped, what deferred, what we learned. Write the sprint summary to the vault.

The product is: $ARGUMENTS

If no arguments provided, ask the user what product or feature they're sprinting on.
