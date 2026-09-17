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

**Status:** review. Built; peer review and human merge pending.

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

**Status:** review. Built and reviewed (20260912-122421-80159e3-_lrr97ak, codex/gpt-6-astra, rounds_exhausted). Six blockers raised, five verified fixed by the reviewer. F2 was raised three times: a missing round record, then a record carrying only an outcome, then fields checked for presence but not shape. The third repair and the one-walk change that followed it carry regressions but no reviewer sign-off, because the round limit was reached first. Exhausting the limit is not approval; the Release Owner decides whether to merge on the evidence as it stands or open a fresh review on the final head.

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

**Status:** review. Built; peer review and human merge pending.

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

**Status:** review. Built; peer review and human merge pending.

**Links introduced:** each observation's claim-to-command-to-output link, re-runnable by
`verify`.

1. `release` records, per repository, that the release head is the reviewed head, with
   the command and a digest of its output, plus any observation the approver adds.
2. The record states plainly that it captures what was run, not that a person read it.
3. `verify` re-runs recorded observations and reports one that no longer holds.
4. Tests: the automatic observation is recorded and re-verified; a stale digest is caught.

### EV-005 — Each item declares the links it introduces

**Status:** review. Built; peer review and human merge pending.

**Links introduced:** none.

1. The design-doc template carries a `Links this item introduces` column and says to
   derive it from the change rather than copy another item's.
2. `/gstack-build` treats an item that introduces state with no declared links as not yet
   covered, and amends the doc before any code.
3. The review packet carries that row, and the reviewer rules on each link in both
   directions.

### EV-006 — Instrument reads

**Status:** built, partially. Criterion 2 is met: a declared dependency the consumer's result gives no sign of using is reported as a candidate fake edge, surfaced in the report node. Criterion 1 is NOT met and is not claimed. Dependencies reach a command handler inlined in input.json and a model handler inlined in its prompt, so there is no per-dependency read to observe without changing the payload contract every existing handler depends on. What is measured is whether the handler's result references the dependency, which is a proxy: unreferenced is not proof of unused, so it is reported and never fatal. Upgrade path, mechanism verified 2026-09-17: per-dependency files make reads observable through atime, given the aging described in EV-008.

**Links introduced:** the read side of every handler's declaration.

1. A node's declared inputs are compared against what its handler actually read.
2. A declared dependency that nothing reads is reported, completing the fake-edge test in
   both directions.

### EV-007 — Reference identity and archive at citation time

**Status:** built. Criterion 1 is met for identifiers whose canonical form is mechanical — arXiv, DOI and PubMed ids resolve to one work identity regardless of URL form, case or resolver, and the check reports which rule produced each identity. Linking a preprint to the DOI it later received needs a registry lookup, is not attempted, and the two remain separate works. Criterion 2 is met: cited URLs are archived at citation time to the Wayback Machine AND stored as a local copy beside the bibliography (Dorian, 2026-09-17, chose both), with the SHA-256 of the archived snapshot. The hash covers the SNAPSHOT, not the live page: hashing live HTML detects ad and timestamp rotation rather than drift, so this proves "this is the page I cited", not "the page has not changed". Persistently resolvable identifiers are skipped and recorded as skipped. An unreachable archive never blocks a citation; it is recorded with its reason, and the gate reports coverage from the record without touching the network. Criterion 3 is met: cited commits, test files and review identifiers resolve in the named repository, and a paper with no repository available returns SKIP rather than PASS.

**Links introduced:** the reference-to-work link (identifier to canonical work) and the
citation-to-snapshot link.

1. References resolve to a canonical work identity before comparison, so one study cited
   as a preprint and as its announcement is detected as one work rather than two strings.
2. Every cited URL is archived at citation time and the reference stores the snapshot and
   its hash.
3. Every commit, test name and review identifier a manuscript cites resolves in the named
   repository at the cited commit.

### EV-008 — Record what a review examined, not only what it found

**Status:** built. Criteria 1 and 2 are met for file reads: the round records which surface files the reviewer opened, how many were offered, and whether it looked beyond the diff. Commands the reviewer ran are NOT recorded — the CLIs differ in what they report and some report nothing — so criterion 1's second half is unmet and unclaimed. Criterion 3 is not built; routing ad-hoc consultations through a recording address is a separate change to how tools are invoked, not to the review record.

**Links introduced:** the review-to-search-space link.

1. A round records the paths the reviewer opened and the commands it ran.
2. A round that examined nothing outside the diff is visible as such.
3. Ad-hoc consultations with other tools are conducted through an address that leaves a
   record, so the denominator of a search stops being unknown.

## Fourth objective: execution economy

Opened 2026-09-17 after an audit of a three-day Codex session that built the OpenControls support platform. That session spent 2,319 tool calls to produce 54 file changes, 1,039 of them browser calls where an API existed, and was interrupted 43 times by approvals that re-derived authority the human had already granted. The implementation stayed small, so the restraint layer did its job. The cost was in the loop around the change, which no item in this design governs.

The premise: **a loop that cannot prove its own preconditions pays for them at the slowest point, and an approval that must be re-derived is not a decision, it is an interruption.** Completeness is a property of the change. Economy is a property of the path taken to make it, and that path is not in the diff.

Each item's `**Status:**` below is the only record of what is built. This preamble deliberately restates none of it: the previous version carried a count that contradicted the statuses beneath it within a day, because a fact with two homes drifts on the first merge that touches one.

### XE-001 — The gate proves it can run before anything is pushed

**Status:** done. Review 20260917-193232-339fea5-afng5hkw (gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance); merged as f1a1034.

**Links introduced:** none. The preflight report is derived from the working tree at call time and is not stored.

1. `endform_workflow.py preflight --repo <path>` answers, locally and without network, whether the E2E gate can run in this repository, and names every condition it examined.
2. It fails when the Playwright project root and the workflow's run directory differ, which is the defect that cost two push/CI/fix cycles in the audited session.
3. It fails when a `tsconfig` the test project extends resolves outside that project root, which is the defect that cost a third.
4. It reports every `secrets.*` name the workflow references, so a missing CI secret is discovered before the push rather than by a red check.
5. Per EV-001, a condition that could not be examined reports `SKIP` and is distinct from `PASS`, and a run that examined nothing exits non-zero rather than reporting success.
6. `/gstack-build` runs it once per repository before the first item and refuses to treat a red E2E gate as a code defect until it is green.

### XE-002 — An approval binds to a scope, and re-resolves

**Status:** done. Review 20260917-193232-339fea5-afng5hkw (gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance); merged as f1a1034.

**Links introduced:** a capability grant ledger. Each grant links a human decision to an action class and a resource pattern, and every subsequent action re-resolves against it.

1. An approval writes a structured grant, not a sentence. The grant carries the action class, a resource pattern, a scope of one-shot, session or project, and the granting human.
2. The checker matches a pending action against the ledger by pattern. It never re-reads the prose of a prior approval to decide whether that prose covers a new action.
3. A grant that does not match prompts once and writes a new grant. The prompt names the class and pattern being granted, so the human decides policy rather than re-deciding the same act.
4. Action classes that stay one-shot by construction: production data writes, sending mail to a real recipient, and merge.
5. This inherits EV-002's mechanism. Findings bind to content and re-resolve; grants bind to a scope and re-resolve. Neither re-reads prose to decide whether a link still holds.
6. **The ledger is not a security control.** It is written by the process it governs, exactly as `GOVERNANCE.md` already says of the review state files, so an agent that can write a grant can write its own. What the ledger buys is the human's attention, not containment. The containment is `ONE_SHOT_ONLY`, a set of classes no grant satisfies in advance at any scope, and protected-branch enforcement outside this process. An item that moves a class out of `ONE_SHOT_ONLY` is amending that boundary and needs the amendment, not a code change.
7. The ledger widens what a packet's `data_use` policy covers. It never removes a refusal: the owner, classification and repository/history checks are unchanged, and an action with no matching grant is still denied rather than resolved by re-reading a prior approval.

### XE-003 — The cheapest surface that answers the question

**Status:** done. Built and reviewed (20260917-204651-c8e63f7-humw079_, gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance). PR #14; human merge pending.

**Links introduced:** none.

1. The tool order is connector, then CLI, then REST, then browser. A browser call is the last rung, not the first.
2. A session that uses a browser where a connector for that service is configured says so, and says which rung it took.
3. Where a browser is genuinely required, the page is read as structure rather than as pixels, and a query-focused read is preferred over a full snapshot on any page large enough for the difference to matter.

### XE-004 — A checkpoint is a batch, not an item

**Status:** done. Built and reviewed (20260917-204651-c8e63f7-humw079_, gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance). PR #14; human merge pending.

**Links introduced:** none.

1. Cross-tool review runs at a checkpoint covering several items, not once per item.
2. A review is dispatched and collected. The dispatching session does not block on it and does not narrate its progress while it runs.
3. The audited session produced 51 messages whose entire content was that a review had not yet returned. That is the behavior this item removes.

### XE-005 — A reviewer is independent by what differs, not by its name

**Status:** done. Review 20260917-193232-339fea5-afng5hkw (gemini/gemini-3.1-pro-preview, no_blocking_findings, 13/13 acceptance); merged as f1a1034. Criterion 6 (per-entry output headroom) was NOT in that merge's acceptance criteria and so was not reviewed; it is built in the XE-003/XE-004 checkpoint.

**Links introduced:** none. The reviewer table is static configuration in the dispatcher, not stored state.

The dispatcher hardcodes two tools and derives the reviewer as "the other one". That encodes independence as a name rather than as a property, and two things already break it. Cursor can run Claude models, so a Claude builder reviewed by Cursor could share the builder's model family while satisfying every current check. And when the only named reviewer is unreachable, as happened on 2026-09-17 when Codex was first absent and then refused by its API for billing, the loop has nowhere to fall back to and the checkpoint lands unreviewed.

1. Reviewer routing is a table of `{tool, model_family, floor, invocation}` rather than a two-key map of builder to other tool. Adding a reviewer is a table entry, not a change to the dispatch path.
2. A reviewer whose `model_family` matches the builder's is refused before it runs, under an outcome distinct from `review_unavailable`, because a harness swap is not an independent mind and a record that cannot tell the two apart is worth less than no record.
3. The review record names the reviewer's tool **and** its model family, so a later reader can see what independence was actually obtained rather than inferring it from a tool name.
4. Fallback to a second reviewer is permitted only among entries whose family differs from the builder's, and the record says which reviewer ran and that it was a fallback. A fallback that is not recorded as one is a silent downgrade.
5. A reviewer response cut off at its output limit reports `output_truncated`, distinct from `malformed_output`. The two have different causes and different fixes, and collapsing them makes a headroom problem look like a broken reviewer. Gemini truncated a long structured response twice in this team's only run of it, during the 2026-09-15 Council deliberation, and the reviewer contract demands a longer and stricter structure than that deliberation did.
6. Each table entry carries its own output headroom, set against the reviewer contract's full response rather than a provider default. Precedent: the Council Sonnet-5 slot was configured at 3000 tokens and needed 12000, and under-provisioned it returned empty content while the dispatcher still reported success.

### XE-006 — The repo runs its own checks, or it has no gate

**Status:** declared, building in this change.

**Links introduced:** none.

This repository ships the verification discipline and does not apply it to itself. It carries eight
test files and four `--selftest` entry points, and no `.github/workflows` directory at all. Every
"suites green" reported during the XE objective was a human running commands in a sandbox and
reporting the result. Nothing ran at the boundary, so nothing stopped a broken dispatcher from
merging except attention.

The E2E gate is correctly scoped to Vercel-deployed repositories, and this is not one: there is no
`package.json`, no `vercel.json`, and no page to drive. Adding Playwright here would manufacture a
green check over nothing, which EV-001 already forbids. The error was not the missing browser suite.
It was reading "the web gate does not apply" as "no gate applies."

1. Every pull request and every push to `main` runs the repository's own checks in CI, and the
   merge is gated on them.
2. The runner reports what it examined — how many suites it discovered and ran, by name — rather
   than reporting only a verdict.
3. A run that discovers zero suites fails. A gate that finds nothing and exits green is the exact
   false pass this objective exists to remove, and it is how a gate silently dies when files move.
4. The check the loop requires is the one matching the repository kind. A repository with no web
   deployment is not exempt from having a gate; it is exempt from having *that* gate.

### XE-007 — The reviewer gets the change and its callers, not the tree

**Status:** declared, building in this change.

**Links introduced:** none. The surface is derived per round from the pinned commits; it stores nothing.

Every review in the 2026-09-17 session ran close to its time limit, and three did not finish at all.
The cause was measured, not guessed: the reviewer is handed a detached worktree of the whole
repository — 776 files, 31 MB — to answer a question about a 4-file, 172-line diff, and spends its
budget reading the repository. The same prompt and model against the change and the files it touches
returned a valid review in 81 seconds. This is XE-003's principle applied to the review loop itself.

The naive fix is wrong. Handing over only the changed files removes the reviewer's ability to see
that a change breaks an untouched caller, which is where the substantive blockers come from.

1. The reviewer receives the diff, the files it changes, and the files that reference those files —
   not the repository tree.
2. The surface is bounded, and when the bound excludes candidate files the excluded set is reported
   rather than silently dropped.
3. The surface states its own limits to the reviewer, and a reviewer that needs a file the surface
   does not carry reports that as a finding rather than guessing.
4. The round record names how many files the review could see and how many were withheld, so a later
   reader can tell a narrow review from a thorough one.

### XE-008 — A fact with two homes drifts; a format with one producer cannot

**Status:** declared, building in this change.

**Links introduced:** none.

On 2026-09-17 the same defect shipped three times in one session: a design-doc preamble contradicting
the item statuses beneath it, a surface path format updated in its writer and not its parser, and a
function deleted after grepping the tests and not the callers. Checks caught all three. Reading
caught none — and verification check 5, "before changing a rule, find its second home", was already
written in four files and injected into every turn of that session. Restating it a fifth time is the
intervention that had already failed, which is the same shape as XE-003.

The three cases do not share one fix, and pretending they do is how a single mechanism gets credit
for coverage it does not have.

1. Where a fact can have one home, it has one. Prose does not restate a status that a structured
   field already carries.
2. Where a format crosses a boundary, one function emits it and the same function's output is what
   the parser accepts, so the two cannot drift. A test asserts the round trip rather than restating
   the spelling, because a spelling copied into a test is another home.
3. Where neither applies — a function's callers cannot be structurally prevented — the dispatcher
   computes which files reference the change and were not themselves touched, names them to the
   reviewer, and says what to do with them. The builder asserting "I checked the callers" is worth
   what the prose rule was worth.
4. This is a report routed to the reviewer, not a gate. Referencing a changed file is not an error,
   and a check that cannot fail must not be dressed as one.

### XE-009 — A review that cannot finish is not a review

**Status:** declared, building in this change.

**Links introduced:** none.

XE-004 split review into dispatch and collect so the loop would stop blocking. It could not actually
be used: Cowork's `device_bash` caps each call and gives it a PID namespace torn down on return, so
a dispatched review is reaped before it writes anything. Three reviews died that way on 2026-09-17,
and one change reached its pull request unreviewed as a result. The vault records the same class of
failure on 2026-06-13, where a reasoning model tripped a 45-second sandbox cap.

The wrong fix is available and tempting: pick a faster model, or trim acceptance criteria until a
review fits the clock. Both buy a pass rather than earning one, and the second is the XE-005.6
error — criteria narrower than the item, so the review passes something unfinished.

1. A review host is stood up by one idempotent script: reviewer CLI, checkout, and the environment
   a review needs.
2. Credentials are read from files, never passed as arguments, so they do not appear in `ps` or
   shell history.
3. The script fails loudly and specifically when it cannot do its job, rather than leaving a
   half-prepared host that fails later at the review.
4. The build loop names when to reach for a host, and names the two wrong fixes so they are not
   discovered independently by the next session.

## Validation

Write failing behavioral tests before implementation. Exercise real dispatcher and state transitions using temporary repositories. Use controlled reviewer responses for malformed-output and failure cases, followed by a live cross-tool review to verify integration.

Test stale approvals, incomplete acceptance, dropped blockers, failed branches, changed inputs, interrupted runs, and duplicate release attempts. No production release is required to prove refusal behavior.

## Amendments log

- 2026-09-17: XE-005 declared after the checkpoint for XE-001 and XE-002 landed unreviewed. Two review records for `5761c37` both returned `review_unavailable`, first because the `codex` CLI was absent and then, once it was installed and authenticated, because the OpenAI account had no credits. Dorian merged as Release Owner with the gap recorded on the pull request, which the release-boundary contract already allows: a passing machine review was never release authorization. Cursor and Gemini were both considered as a third reviewer. Gemini is the better fit on independence, since Cursor can run the builder's own model family, and the item is written so that neither can be added without declaring what actually differs.

- 2026-09-17: XE-002 built alongside XE-001 and reviewed with it in one checkpoint, per XE-004. Capability grants extend `governance.py` rather than adding a parallel authority path: the packet's `data_use` policy already carried an owner, an exact-match `allowed_tools` list and pattern-matched `output_roots`, and the defect was that the policy is re-declared per invocation and matched by exact string. Grants persist, match by pattern, and record the granting human. The classes that matter are unreachable by any grant.

- 2026-09-17: Dorian approved a fourth objective after an audit of the 2026-09-15/16 support-platform session. The audit counted 2,319 tool calls against 54 file changes, 1,039 browser calls where connectors were configured, 43 approval interruptions, and 193 failed commands. XE-001 is built in this change; XE-002 through XE-004 are declared and not started. The session's own self-diagnosis, recorded in its transcript, agrees: the implementation stayed small and the loop around it did not.

- 2026-09-12: Dorian approved a third objective after reading "When Structure Pays", which reports three defects in this executor and three false passes in this repository's own completeness gate. EV-001 through EV-005 are built in this change; EV-006 through EV-008 are declared and not started. The paper's central claim is the reason the objective exists: completeness is a property of an artifact, evidential force is a property of the relationship between the artifact and the work, and that relationship is not in the artifact.

- 2026-09-11: Approved by Dorian in the Codex Team Plugins conversation. Establishes the Governed Autonomy objective and acceptance criteria above. Initial implementation is GA-001; subsequent items begin only when requested.

- 2026-09-11: Dorian requested the remaining task graph implementation ("Then build it"). GA-002 through GA-004 retain the approved criteria.

- 2026-09-11: Dorian approved a second objective for this repository after a naming defect surfaced during an academic-pipeline run: the deliverable was written to a hardcoded `complete_document.md` and the formatting skill carried a fabricated author surname. AP-001 through AP-003 add derived naming, producers for declared requirements, and a mechanical release gate.

- 2026-09-12: AP-001 through AP-003 complete. Two reviews, four blocking findings, all false passes in either the acceptance test or the gate itself. Both merges were executed by Claude with the vault PAT at Dorian's explicit instruction rather than by a human clicking Merge; the merge commits record that, and record-release cannot distinguish the two because the PAT carries the owner's identity. Closing that gap needs an agent credential without merge rights, which the release-boundary contract already assumes exists.
