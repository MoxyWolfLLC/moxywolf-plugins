# Design: gstack Governed Execution

## Goal

Make gstack’s execution graph conform to Governed Autonomy: enforce authority and evidence completeness before introducing parallel execution. Every consequential action must be traceable to its governing policy, supporting evidence, and accountable human.

## Constraints and settled decisions

- Preserve cross-tool review, pinned commits, bounded review rounds, and recursion refusal.
- Keep low-risk, authorized work autonomous. Human approval belongs at consequential boundaries.
- Successful machine review does not grant release authority.
- Classify individual actions within commands; assess the effects of pushes and merges, including deployment triggers.
- Start with static workflows. No autonomous topology expansion.
- Keep `/gstack-verify` advisory; incomplete verification must remain visible.
- Reuse existing governance and audit machinery where it meets the requirements.
- A nonce establishes freshness and linkage, not proof of substantive review.
- Limit the GA items to gstack and the shared declarations necessary to govern it.
- Other plugins in this repository carry their own objective sections and items.

## Items and acceptance criteria

### GA-001 — Reconcile authority and enforce evidence completeness

**Status:** review. Implementation prepared; independent review and human merge pending.

1. Build, ship, peer-review, and governance documentation express one consistent release policy. Routine branch work remains authorized; consequential release requires recorded human authorization.
2. Review success requires coverage of every expected acceptance criterion. Missing, duplicate, unknown, malformed, or unmet criteria cannot produce a passing outcome.
3. Fix verification accounts for every previous blocker. Omission cannot silently resolve a finding; deferral requires the applicable authorization.
4. Evidence and release authorization identify the exact reviewed revision and action. Changed code invalidates an earlier release authorization.
5. Tests demonstrate that unauthorized release is refused through the execution entry point, rather than only through a helper.
6. Applicable command tiers and the named Release Owner are recorded. The agent cannot manufacture the human’s approval.

### GA-002 — Declare and execute static topology

**Status:** review; implemented on the GA-001 feature branch foundation; human merge pending.

1. Introduce machine-readable workflows for CSO and verify first.
2. The executor consumes the declarations; they are not parallel documentation.
3. Each node declares dependencies, inputs, outputs, permitted effects, and failure behavior.
4. Cycles, missing dependencies, conflicting writers, and missing required results prevent successful completion.
5. Persist node attempts and evidence references. Resume preserves valid work and invalidates descendants when their inputs change.

### GA-003 — Optimize independent branches

**Status:** review; depends on GA-002; human merge pending.

1. CSO prepares scope and architecture before parallel audit branches; independent verification precedes one owned report.
2. Verify freezes claims and code before parallel checks; convergence verifies coverage and detects extra implementation.
3. Multi-repository reviews split only where acceptance criteria are independent; coupled changes retain integration review.
4. Enforce a concurrency cap. Shared-state proof commands remain serialized unless isolated.
5. Demonstrate overlapping execution without lost findings, conflicting writes, or false success after a worker fails.

### GA-004 — Complete governance records and data boundaries

**Status:** review; builds on GA-001 and GA-002; human merge pending.

1. Record approvals, stops, overrides, edits, and execution outcomes with owner, action, revision, and evidence references.
2. Reuse the shared gate-log where possible; report machine-review outcomes separately from human oversight.
3. Enforce declared data-use permissions before external reviewer dispatch and release checks before output leaves its permitted scope.
4. Report oversight timing and override rates as investigation signals, never automatic judgments.
5. Prevent resumed runs from replaying consequential actions already completed.

## Second objective: academic-pipeline integrity

Goal: the pipeline must not encode a fact it cannot know. Names, filenames, and required sections come from run data or from the user, never from a template constant, and a mechanical gate reports what was checked before anything is presented as finished.

### AP-001 — Derive deliverable names and attribution from run data

**Status:** building.

1. Stage 7 writes its deliverable to a name derived from the Stage 1 target slug. The orchestrator's artifact table and Stage 8's input reference that same name.
2. Stage 1's diagram deliverable is derived from the target slug likewise.
3. No skill contains a person's name as a worked example. The author block is populated from the vault voice profile or by asking. Inventing a name is forbidden in text.
4. Tests: grepping the plugin tree for the literal strings `complete_document.md`, `mermaid_diagram.md`, and the fabricated surname each return zero hits.

### AP-002 — Every declared requirement has a producer

**Status:** planned.

1. End-matter sections declared in Stage 4 appear in Stage 5's `structure_plan` whenever the venue requires them.
2. Stage 6 writes those sections as ordinary sections.
3. Stage 6 carries an explicit rule to number Vancouver citations by first appearance while drafting, rather than leaving order to a later repair.
4. Tests: a fixture run produces every section named in the formatting requirements' `section_order`.

### AP-003 — Mechanical release gate before completion

**Status:** planned.

1. The orchestrator runs a gate before presenting deliverables: zero em dashes, zero forbidden phrases, renumber `--check` exit 0, every `section_order` entry present, and no two references sharing a normalized DOI or URL.
2. Stage 7 dedupes on normalized DOI/URL, not only on BibTeX key, and warns when two keys resolve to one work.
3. The gate names each check and its result. A failing gate blocks the completion report rather than being narrated around it.
4. Tests: the gate run against a fixture carrying a planted em dash, a duplicate URL, and a missing section fails on exactly those three.

## Validation

Write failing behavioral tests before implementation. Exercise real dispatcher and state transitions using temporary repositories. Use controlled reviewer responses for malformed-output and failure cases, followed by a live cross-tool review to verify integration.

Test stale approvals, incomplete acceptance, dropped blockers, failed branches, changed inputs, interrupted runs, and duplicate release attempts. No production release is required to prove refusal behavior.

## Amendments log

- 2026-09-11: Approved by Dorian in the Codex Team Plugins conversation. Establishes the Governed Autonomy objective and acceptance criteria above. Initial implementation is GA-001; subsequent items begin only when requested.

- 2026-09-11: Dorian requested the remaining task graph implementation ("Then build it"). GA-002 through GA-004 retain the approved criteria.

- 2026-09-11: Dorian approved a second objective for this repository after a naming defect surfaced during an academic-pipeline run: the deliverable was written to a hardcoded `complete_document.md` and the formatting skill carried a fabricated author surname. AP-001 through AP-003 add derived naming, producers for declared requirements, and a mechanical release gate.
