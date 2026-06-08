---
description: Create or update a project's CHARTER.md — the durable principles and boundaries the Council consults before scope and PRD decisions
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
argument-hint: [project-name-or-path]
---

Create or update the project charter for the project described in $ARGUMENTS (default: the current working directory / active project).

Read the product-orchestrator skill (trigger it by context — this is a product orchestration task), then read `references/charter-template.md` from the product-orchestrator skill directory for the charter format and interview protocol.

A charter is the project's **constitution**: the small set of durable principles, technical constraints, and architectural boundaries that should hold across every feature — the kind of invariant that, once decided, shouldn't be relitigated on every scope or PRD call (e.g. "the importer owns Supabase writes; the extractor never writes the lexicon store directly"). It is governance the Council loads as context, not a gate that blocks work.

## Steps

1. **Locate the charter.** Look for an existing `CHARTER.md` at the project root (the active GitHub repo, or the path in $ARGUMENTS). If one exists, read it and treat this as an update; otherwise create a new one.

2. **Interview only for what's missing.** Using the `charter-template.md` protocol, gather: the project's mission in one line, 3–7 durable principles, hard technical constraints, explicit architectural boundaries (what owns what / what must never happen), and any non-negotiables (compliance, security, data-egress rules). Ask only what isn't already evident from $ARGUMENTS, the repo, prior conversation, or an existing charter. Use AskUserQuestion for structured choices. Pull candidate principles from existing decision records (`DR-*.md` / `PD-*.md`) when available and ask the user to confirm them.

3. **Keep it short and durable.** A charter is invariants, not a spec. If a line would change feature-to-feature, it belongs in a PRD, not the charter. Aim for one screen. Every principle should be falsifiable enough that the Council can check a decision against it.

4. **Write `CHARTER.md` to the project root** in the format from `charter-template.md`. On an update, preserve the version-history block and append a dated entry describing what changed.

5. **Confirm the wiring.** Remind the user that once `CHARTER.md` exists at the project root, `/product-scope` and `/product-prd` automatically load it as Council context — it informs deliberation but never blocks it (progressive opt-in rigor: tiny changes ignore it, large changes lean on it). See DR-004.

6. **Present a summary** of the charter's principles and boundaries, and suggest the next step (`/product-scope` or `/product-prd`) now that the governing context exists.

## Notes

- The charter does not gate anything. It is passive context. Absent a `CHARTER.md`, every other command behaves exactly as before.
- Do not invent principles. Use only what the user confirms or what existing decision records establish.
- This command lives in product-orchestrator because the charter governs the *decide-what-to-build* phase. Implementation-time consistency checks against the charter are a separate, optional concern (see DR-004's `/product-analyze` and `/gstack-verify` follow-ons).
