---
description: Read-only cross-artifact consistency check across PRD, architecture decisions, the task plan, and CHARTER.md before execution
allowed-tools: Read, Grep, Glob, Bash
argument-hint: [product-name-or-prd-path]
---

Run a non-destructive consistency and coverage analysis across a product's planning artifacts before execution begins. This is DR-004's anticipated `/product-analyze`. Concept-ported from spec-kit's `/speckit.analyze` (MIT) — the cross-artifact detection discipline, re-specified for MoxyWolf's PRD → architecture → task-plan → charter chain.

Read the product-orchestrator skill for context, then read `references/analyze-protocol.md` for the detection passes, severity rubric, and report format.

**STRICTLY READ-ONLY.** Do not modify any file. Produce a report; offer a remediation plan the user must explicitly approve before any follow-on editing command runs. This mirrors the charter's posture — analyze *reports*, it never gates or auto-edits.

Steps:

1. **Gather artifacts.** Load what exists: the PRD (`PRD-*.md`), architecture decisions (the PRD's architecture section and any `PD-*.md` / `DR-*.md` arch records), the execution/task plan (from the current `/product-sprint` run or a saved task list), and `CHARTER.md` at the project root. Note which artifacts are absent — a missing task plan means run this after Phase 2, not before.
2. **Build semantic models.** Extract the requirement inventory from the PRD, the architecture commitments, the task list, and the charter's MUST/SHOULD principles.
3. **Run the detection passes** from the protocol: duplication, ambiguity, underspecification, **charter alignment** (a decision conflicting with a charter MUST is automatically CRITICAL), **coverage** (map each task → requirement; flag requirements with zero tasks and tasks mapping to no requirement), and inconsistency (terminology drift, contradictory statements across artifacts).
4. **Assign severity** (CRITICAL / HIGH / MEDIUM / LOW per the rubric) and produce the report: a findings table with stable IDs, a requirement→task coverage table, a charter-alignment section, unmapped-tasks list, and a metrics block (coverage %, ambiguity/duplication/critical counts).
5. **Next actions.** If CRITICAL issues exist, recommend resolving them before execution and name the command that fixes each (`/product-clarify`, `/product-scope`, `/product-arch`, or a manual task-plan edit). Charter conflicts resolve by changing the artifact — or, explicitly and separately, by amending the charter via `/project-charter`, never by silently reinterpreting a principle.

Analyze checks the *artifacts against each other and the charter* before build. Its paired follow-on, checking the *implementation* against the spec after build, is a gstack-side concern (DR-004's `/gstack-verify`) — out of scope here.

The product is: $ARGUMENTS

If no arguments provided, analyze the most recent PRD and its associated artifacts in the workspace.
