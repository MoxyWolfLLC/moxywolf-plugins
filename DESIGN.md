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
- This repository has no Vercel project, no package.json and no Playwright suite, so the Endform E2E gate does not apply to it.

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

**Status:** done. Review 20260911-163931-423bd0a-bo_glftu, fixes_verified; merged as 6603aae.

1. Stage 7 writes its deliverable to a name derived from the Stage 1 target slug. The orchestrator's artifact table and Stage 8's input reference that same name.
2. Stage 1's diagram deliverable is derived from the target slug likewise.
3. No skill contains a person's name as a worked example. The author block is populated from the vault voice profile or by asking. Inventing a name is forbidden in text.
4. Tests: grepping the plugin tree for the literal strings `complete_document.md`, `mermaid_diagram.md`, and the fabricated surname each return zero hits.

### AP-002 — Every declared requirement has a producer

**Status:** done. Review 20260911-165938-d11564a-g289mqlt, fixes_verified; merged as 856f5c6.

1. End-matter sections declared in Stage 4 appear in Stage 5's `structure_plan` whenever the venue requires them.
2. Stage 6 writes those sections as ordinary sections.
3. Stage 6 carries an explicit rule to number Vancouver citations by first appearance while drafting, rather than leaving order to a later repair.
4. Tests: a fixture run produces every section named in the formatting requirements' `section_order`.

### AP-003 — Mechanical release gate before completion

**Status:** done. Review 20260911-165938-d11564a-g289mqlt, fixes_verified; merged as 856f5c6.

1. The orchestrator runs a gate before presenting deliverables: zero em dashes, zero forbidden phrases, renumber `--check` exit 0, every `section_order` entry present, and no two references sharing a normalized DOI or URL.
2. Stage 7 dedupes on normalized DOI/URL, not only on BibTeX key, and warns when two keys resolve to one work.
3. The gate names each check and its result. A failing gate blocks the completion report rather than being narrated around it.
4. Tests: the gate run against a fixture carrying a planted em dash, a duplicate URL, and a missing section fails on exactly those three.

## Third objective: evidence integrity

Goal: a report is treated as evidence only when the links between it and the work it
describes still hold. Completeness checks items; nothing checked links. Every defect in
this objective is a link that still resolved after the thing at its other end had
changed, which produces a complete report, no error, and a person about to sign it.

Derived from "When Structure Pays" (Cougias, 2026), which reports three such defects in
this repository's own executor plus three false passes in its own completeness gate.

### EV-001 — No check reports a pass over input it did not examine

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** none; this item removes a false one (a verdict that implied
coverage it never had).

1. Every check returns what it examined and in what unit, and a PASS with zero coverage
   becomes a FAIL naming the shortfall. The rule is applied where results are assembled,
   so no later check can opt out of it by forgetting to.
2. A check that does not apply returns SKIP, is printed as SKIP, and is counted in the
   summary line. It is never folded into a green line.
3. Each check carries a seeded defect it must catch, because a repair verified only
   against the case that was reported reproduces the defect it is repairing.
4. Tests: a paper with no reference list fails `duplicate_sources` for examining nothing;
   an empty forbidden-phrase list and an empty `section_order` fail rather than report a
   clean paper; a non-Vancouver paper skips rather than passes citation order.

### EV-002 — Findings bind to content, and every link re-resolves on demand

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner, on the evidence as it stood and without a fresh review of the final head. Reviewed as `20260912-122421-80159e3-_lrr97ak` (codex/gpt-6-astra, `rounds_exhausted`): six blockers raised, five verified fixed by the reviewer. F2 was raised three times, as a missing round record, then a record carrying only an outcome, then fields checked for presence but not shape; repairing the third surfaced a fourth instance, two later sweeps re-reading the rounds without the shape check. The third repair and the one-walk change that followed it carry regression tests and no reviewer sign-off, because the round limit was reached first. **The record that review ID names no longer exists.** See EV-009: it was written to a session-local home and destroyed with the session, so what follows from it in this document is reconstruction from the pull request and the commit messages, not a record a reader can pull on.

**Links introduced:** a per-finding subject (blob id plus a span hash at the reviewed
head) retained in `round-N.json`; the `verify` report's re-resolution of that subject at
the repository's current head.

1. The dispatcher, not the reviewer, binds each finding to the content at the reviewed
   head when the round is recorded.
2. `verify` re-resolves the packet's commits, every finding subject, every disposition,
   and every recorded observation, and names each link it examined.
3. Drift expected from a repair is not reported as staleness; drift under any other
   disposition is.
4. A missing entry and a link that resolved to the wrong thing do not share an outcome
   name, and a record that cannot be re-resolved is a third answer.
5. `release` refuses on `stale_link` and `incomplete_record`.
6. Tests: content changing under an undisposed finding is stale; the same change under a
   `fixed` finding is not; a hand-edited span is detected; a snapshot-prefixed path and a
   repo-relative path bind to one subject.

### EV-003 — The undeclared-write sweep, in the direction nobody had

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** the declaration-to-behaviour link for every handler, checked at
runtime rather than against other declarations.

1. `run --audit-writes` hashes the run root before each node and after its handler
   returns, before declared outputs are written, and fails a node that wrote a path no
   declaration mentions.
2. The sweep forces serial execution, because attributing a write while several nodes are
   writing would be a declaration that can be false.
3. The exclusion of executor-owned files has one home.
4. Reads are not instrumented; a declared dependency that nothing reads is still
   undetected and is stated as a limit rather than implied to be covered.
5. Tests: a handler writing an undeclared path fails by name; a clean graph passes; audit
   mode does not overlap nodes.

### EV-004 — The approver's reconstruction gets a field

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** each observation's claim-to-command-to-output link, re-runnable by
`verify`.

1. `release` records, per repository, that the release head is the reviewed head, with
   the command and a digest of its output, plus any observation the approver adds.
2. The record states plainly that it captures what was run, not that a person read it.
3. `verify` re-runs recorded observations and reports one that no longer holds.
4. Tests: the automatic observation is recorded and re-verified; a stale digest is caught.

### EV-005 — Each item declares the links it introduces

**Status:** done. Merged to `main` in `c747ab9` (PR #9, head `b746e22`) on 13 September 2026 by the Release Owner.

**Links introduced:** none.

1. The design-doc template carries a `Links this item introduces` column and says to
   derive it from the change rather than copy another item's.
2. `/gstack-build` treats an item that introduces state with no declared links as not yet
   covered, and amends the doc before any code.
3. The review packet carries that row, and the reviewer rules on each link in both
   directions.

### EV-009 — A review record outlives the session that produced it

**Status:** building.

**Links introduced:** the review ID to its record on disk, which is the link this item
exists because it was already broken.

Found on 14 September 2026 by going to pull review `20260912-122421-80159e3-_lrr97ak`,
cited as the evidence for EV-002 one day after merge. `REVIEW_DIR` defaulted to
`$HOME/.gstack/peer-review`. In a sandboxed session `$HOME` is per-session and outside
every connected folder, so every record written there was destroyed when the session
ended. The identifier went on reading like evidence in this document, which is the same
failure the EV items were built to catch, in the governance record of the fix for it.

1. `GSTACK_PEER_REVIEW_DIR` is required and has no default. A review that cannot name a
   durable root does not open, and the error says what to set and why.
2. No code path falls back to the home directory, and a test asserts that against the
   source rather than against one call, because the defect was a default rather than a
   call site.
3. The command, the contract and `docs.md` all state the requirement, so the three places
   a reader could learn the old default agree with the code.
4. Tests: `review_root` exits naming the variable when it is unset; a declared directory
   is used as given; the source contains no home-directory fallback.

**Open:** graph-driven reviews already land in the run directory because `task_graph.py`
sets the variable. Direct invocations were the unprotected path, and nothing here recovers
the records already lost.

### EV-006 — Instrument reads

**Status:** planned.

**Links introduced:** the read side of every handler's declaration.

1. A node's declared inputs are compared against what its handler actually read.
2. A declared dependency that nothing reads is reported, completing the fake-edge test in
   both directions.

### EV-007 — Reference identity and archive at citation time

**Status:** planned.

**Links introduced:** the reference-to-work link (identifier to canonical work) and the
citation-to-snapshot link.

1. References resolve to a canonical work identity before comparison, so one study cited
   as a preprint and as its announcement is detected as one work rather than two strings.
2. Every cited URL is archived at citation time and the reference stores the snapshot and
   its hash.
3. Every commit, test name and review identifier a manuscript cites resolves in the named
   repository at the cited commit.

### EV-008 — Record what a review examined, not only what it found

**Status:** planned.

**Links introduced:** the review-to-search-space link.

1. A round records the paths the reviewer opened and the commands it ran.
2. A round that examined nothing outside the diff is visible as such.
3. Ad-hoc consultations with other tools are conducted through an address that leaves a
   record, so the denominator of a search stops being unknown.

## Validation

Write failing behavioral tests before implementation. Exercise real dispatcher and state transitions using temporary repositories. Use controlled reviewer responses for malformed-output and failure cases, followed by a live cross-tool review to verify integration.

Test stale approvals, incomplete acceptance, dropped blockers, failed branches, changed inputs, interrupted runs, and duplicate release attempts. No production release is required to prove refusal behavior.

## Amendments log

- 2026-09-12: Dorian approved a third objective after reading "When Structure Pays", which reports three defects in this executor and three false passes in this repository's own completeness gate. EV-001 through EV-005 are built in this change; EV-006 through EV-008 are declared and not started. The paper's central claim is the reason the objective exists: completeness is a property of an artifact, evidential force is a property of the relationship between the artifact and the work, and that relationship is not in the artifact.

- 2026-09-11: Approved by Dorian in the Codex Team Plugins conversation. Establishes the Governed Autonomy objective and acceptance criteria above. Initial implementation is GA-001; subsequent items begin only when requested.

- 2026-09-11: Dorian requested the remaining task graph implementation ("Then build it"). GA-002 through GA-004 retain the approved criteria.

- 2026-09-11: Dorian approved a second objective for this repository after a naming defect surfaced during an academic-pipeline run: the deliverable was written to a hardcoded `complete_document.md` and the formatting skill carried a fabricated author surname. AP-001 through AP-003 add derived naming, producers for declared requirements, and a mechanical release gate.

- 2026-09-12: AP-001 through AP-003 complete. Two reviews, four blocking findings, all false passes in either the acceptance test or the gate itself. Both merges were executed by Claude with the vault PAT at Dorian's explicit instruction rather than by a human clicking Merge; the merge commits record that, and record-release cannot distinguish the two because the PAT carries the owner's identity. Closing that gap needs an agent credential without merge rights, which the release-boundary contract already assumes exists.
