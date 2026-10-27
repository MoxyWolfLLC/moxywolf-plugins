## Serves
Eleventh objective: goal mode

## Outcome
Successor to `gstack-delivery-through-merge-4` (PR #255, approved at e16bfe7, merged 1c91a85), whose item 1 carried goal-3's item 1 forward as its own pull request (#256) at the reviewed head d0cd67a. That pull request cannot pass the required `tests` check against a goal branch opened from main: its version step fails ("gstack-execution: files changed and version stayed at 0.95.3", run 40508050294), because main took 0.95.3 independently in PR #252, the version item 1 carries. Fixing it would move the head off d0cd67a and need an item-1 review the approval did not give. Goal-3's #251 had passed that check only against base 80cc477, before the sync brought 0.95.3 in, so its version move was never evaluated against the base it merged into; that is recorded, not repaired.

This goal consolidates goal-3's items 1 and 2 into one item delivered as one pull request and one recorded merge: build/gstack-delivery-through-merge-3-2-bounded-recovery at the unchanged head b321160, which contains item 1 (its parent d0efc48 is #251's merge) and moves gstack-execution to 0.95.4. Validated before this brief against the actual base commit 1c91a85 in CI's goal mode by a draft validation pull request (#258, closed unmerged after approval): tests (its version step included), goal-envelope and goal-tests green (runs 40510326668 and check runs 122210299727, 122210979708), and version_bump.py in goal mode passes locally on the same merge; the merge tree differs from b321160 only by main's goals/ folders; the goal tests at the merged tree give 6 of 8 passing, the two failing being item 2's (resume after merge, dirty checkout). The item's review covers the complete combined change from the merge base 66d64eb, item 1's changes included, not omitted. Prior reviews are attached as evidence, not as a substitute: `20261026-144252-d0cd67a-pk_fdgcy` (item 1, no_blocking_findings at d0cd67a) and `20261026-180817-58f76ff-f90zynfn` (item 2, three rounds, all blockers resolved, one criterion unmet) enter through head-bound receipts at b321160 (`peer_review.py status` of each, `verify` of the item-2 review, links_verified 30 of 30), beside item 1's comparisons and test receipts re-run at b321160 (17546d5f253d, 8b30662a1e22, 6ff946a5189c, 246f9c033306, dc6f62f5a0fe, 8fce39baad5b) and item 2's (a14a4a31f799, 3c676b24cb56, 89f08647b9cc, 4a3a6f2b8b83) and the four retrospective receipts on scratch commit 254b624. The acceptance of the retrospective comparison in place of the chronological test-first criterion, given in PR #255 for the carried item, carries to the same criterion here unchanged and labelled the same way. Unknown `3107b5e1e958` (needs ci_run: did the tests execute and fail against the pre-change implementations) stays open, because its question is still true: no run before the change exists. The existing tooling closes an unknown only with an exit-0 ledger receipt on the branch, a successful CI run in a review round, or a person's observation on a release handoff; the retrospective receipts exit 1 on the scratch branch, and a command written to turn them into an exit-0 receipt would launder them, so none is made. The packet answers the unknown with the labelled retrospective receipts and the Release Owner's acceptance; an open ci_run unknown is listed on the handoff and does not hold the wide-lane release gate, which refuses only on an open unknown that needs the repository.

The item gets exactly one review pass, the single pass PR #255 allowed; no separate item-1 review is added and the version check is not bypassed. Item 2 here is goal-3's item 3, unchanged. The whole-goal review, the release companion and synchronization of `/Users/doriancougias/GitHub/moxywolf-plugins` only are unchanged.

Records preserved. Goal-4's run is ended with `goal_run.py failed --item 1` naming this conflict; #256 is closed unmerged with its refusal, close and reopen in its timeline; escalation 1 and its acknowledgement stay in goal-4's run record. In review `20261026-144252-d0cd67a-pk_fdgcy`, the goal-3 handoff stays archived (`release-handoff-goal-gstack-delivery-through-merge-3-2026-10-27T00-03-05Z.json`, sha256 7e599a0a734cb060d5a5e6f0fa85e645af7f8ed233924dbd8e048182fe5e8f3c), the goal-4 handoff written under PR #255's archival operation is archived as unused (`release-handoff-goal-gstack-delivery-through-merge-4-2026-10-27T12-58-56Z-unused.json`, sha256 e19faa7f47f5c96190e8814f52b9d6f46c93477baee9d6257a6fda6b04833c3a, also still the bytes of release.json), PR #251's record is unchanged (sha256 4e8e22ec3dcae60e515c496ad01da44c31b028e8a3e8c1257418c69430977f57), and verify read links_verified after each step. No release or record-release is run for that review again: the consolidated merge is recorded through the item's own review.

Budget carried forward, nothing reset. Calls: 11 subscription calls cumulative, $0 metered; the 20-call cumulative stop is unchanged, so 9 remain. Active time already spent, each shown separately and none reset: about 2h40m before goal-3, about 4h45m in goal-3, about 2h35m in goal-4 and this brief's preparation (agent working time between Dorian's messages), about 10h in all; waiting on CI, reviewers and Dorian is excluded and reported separately.

Remaining work, estimated from the code at b321160 and the two goal tests still failing there (test_resume_after_accepted_merge_records_once, test_dirty_required_checkout_preserved_and_pending), with scope unchanged:
- goal_delivery.sync_checkout and its `sync-checkout --checkout --merge` CLI, which do not exist yet: host, path, remote, branch, tracked and untracked cleanliness and divergence checks, fast-forward only, with focused tests for the five refusal cases and the advanced-main control; about 1h30m
- the resume executors in goal_run.resume, which today stop at returning next_action: carry out merge (one exact-head merge request through the existing gates), record-release (through peer_review.py) and sync_checkout in order, persisting after each, idempotent on a second resume, with the subprocess crash-after-accept test and the moved-head, lost-response, owner-gate, missing-companion and failure-after-record cases; about 2h30m to 3h
- goal_run.complete recording the goal merge without ending delivery before release and sync, and the record rendering merge, record and sync states separately; about 45m
- command contracts (gstack-goal.md, gstack-build.md, README, peer-review-contract.md), version 0.95.5, version_bump.py in goal mode, focused suites, the full runner and head-bound receipts; about 1h
- item 1's single review pass at b321160, its release handoff, merge, record-release and goal_run merged; about 45m
- item 2's review, up to three passes, with fixes between them; about 1h30m to 2h30m
- finalize, the whole-goal pull request with a fresh review and the holdout, the GO-011.2 merge and its release record, including fixes if the review blocks; about 1h30m to 2h30m
- the release companion (marketplace top-level bump) through its own review, merge and record; about 45m
- synchronization of /Users/doriancougias/GitHub/moxywolf-plugins, which today is checked out on the item-2 branch, back to main and fast-forwarded, plus the per-command usability check; about 45m
That is about 11h to 13h of active work. Expected model calls: 1 for item 1, 1 to 3 for item 2, 1 to 2 for the whole-goal review, 1 for the companion, so 4 to 7, inside the 9 remaining; three blocking rounds on item 2 and two on the whole-goal review would reach the stop at the 9th call before completion.

Completion allowance proposed: 12h of active agent time in this goal, counted from its start, with the run stopping at 12h whatever is left; about 22h cumulative across all four goals. It replaces the 2h remaining under the earlier nine-hour limit, which this approval would supersede rather than extend in pieces. The time is an estimate, not a commitment: the main risks are the resume executors' merge and release path against the fixture, and findings in the whole-goal review.

Deliver an explicitly approved repository change through verified merge, release recording, and synchronization of every required working copy, without Dorian coordinating tools or repeating permission. Merging is part of completion: a prepared PR, a clean review, a release handoff, or a merged implementation awaiting a required marketplace bump is not completion.

## Non-goals
- consolidating the pilot model-handoff wrappers or adding a model transport
- a graph database, a new service, a generic agent framework, or a change to model routing
- repairing STIGViewer or touching its repository
- editing gate-owned files: goal_spend.py, goal_guard.py, goal_envelope.py, workflows, CODEOWNERS
- the five-task everyday-work evaluation and the two live interruption tests, which are separately approved real changes

## Scenarios
- Given a packet whose selected artifact is fresh but whose attested prerequisite or embedded pointer binding is stale, then the executor refuses before any worker starts and creates no run directory
- Given a review fix round that names a ledger run at the new head, then the round's record carries that run with head_matches true and receipt_verified true, and the retained packet and earlier round bytes are unchanged
- Given a ledger receipt that belongs to an older head or another repository, then it reports head_matches false or receipt_verified false and cannot clear the candidate
- Given a delivery whose change has used its three review passes, then a fourth reservation under a new review ID is refused and a restart preserves the count
- Given GitHub has accepted the exact-head merge and the process exits before record-release, then a fresh process discovers that merge, records it once, synchronizes the required clean checkout, and reports complete without issuing a second merge request
- Given a required checkout that is dirty, on an unexpected branch, divergent, on the wrong host, or unavailable, then its tracked and untracked bytes, status and Git metadata are unchanged and the delivery reports sync_pending naming that checkout and reason
- Given a goal whose declared release companion is not merged and recorded, then delivery_status is not complete
- A second merge request for a change GitHub has already merged must never happen
- A repeated authorization question for an already authorized step must never happen
- A dirty required checkout being stashed, reset, cleaned, switched or overwritten to appear synchronized must never happen
- record-release performing or requesting a merge must never happen

## Goal tests
- `tests/test_delivery.py::Delivery.test_stale_binding_refuses_before_dispatch` (outcome)
- `tests/test_delivery.py::Delivery.test_fix_round_refreshes_head_bound_ledger` (outcome)
- `tests/test_delivery.py::Delivery.test_wrong_head_or_tampered_receipt_cannot_clear_head` (outcome)
- `tests/test_delivery.py::Delivery.test_replacement_review_cannot_reset_attempt_limit` (outcome)
- `tests/test_delivery.py::Delivery.test_resume_after_accepted_merge_records_once` (outcome)
- `tests/test_delivery.py::Delivery.test_dirty_required_checkout_preserved_and_pending` (outcome)
- `tests/test_delivery.py::Delivery.test_release_companion_required_before_complete` (outcome)
- `tests/test_delivery.py::Delivery.test_record_release_never_merges` (invariant)

## Allowed paths
- plugins/gstack-execution/scripts/graph_context.py
- plugins/gstack-execution/scripts/test_graph_context.py
- plugins/gstack-execution/scripts/task_graph.py
- plugins/gstack-execution/scripts/test_task_graph.py
- plugins/gstack-execution/scripts/goal_delivery.py
- plugins/gstack-execution/scripts/test_goal_delivery.py
- plugins/gstack-execution/scripts/goal_run.py
- plugins/gstack-execution/scripts/test_goal_run.py
- plugins/gstack-execution/scripts/peer_review.py
- plugins/gstack-execution/scripts/test_ledger_evidence.py
- plugins/gstack-execution/scripts/test_ci_run_paths.py
- plugins/gstack-execution/commands/gstack-build.md
- plugins/gstack-execution/commands/gstack-goal.md
- plugins/gstack-execution/skills/gstack-execution/references/task-graph-contract.md
- plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md
- plugins/gstack-execution/README.md
- plugins/gstack-execution/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json
- docs/evidence/gstack-delivery/*
- docs/evidence/gstack-delivery/registry/*

## Spend cap
$50

## Provider budgets
- openrouter: $50

## Max calls
11

## Max items
2

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- active agent time exceeds 12h in this goal, the completion allowance this approval gives; the predecessors' about 10h stays on their records; the predecessors' time stays on their records; time waiting on CI or a reviewer is reported separately and does not reset the limit
- 80% of the spend cap or of Max calls is reached, as GO-004 already stops: Max calls 11 here means the stop fires at the 9th call in this goal, which with the 11 already spent is the unchanged 20-call cumulative operating stop; the nominal 11 is never reached
- a gate-owned file (goal_spend.py, goal_guard.py, goal_envelope.py, a workflow, CODEOWNERS) would have to change to reach the outcome
- the same required check fails after two repair cycles without a resolved cause
- a delivered change would need a review pass beyond its count, counting replacement review IDs and the predecessors': item 1 (the consolidated change at b321160) gets exactly one pass, at b321160 and no other head; a second pass, a separate review of the carried-forward item-1 changes, or any commit to the candidate before that pass stops the run; item 2 keeps three
- a review for item 1 is dispatched without unknown `3107b5e1e958` answered in its packet by the labelled retrospective receipts, or without the retrospective receipts, the prior-review receipts and their labels attached, or with a range that omits item 1's changes
- the version check, or any other required check, would have to be skipped, overridden or rerun-until-green for item 1 to merge
- an unreadable gate, budget, or authority record

## Pre-mortem
- a file lands outside the allowed paths and goal-envelope is read only after the last review pass; the envelope check at the pushed head precedes every review dispatch
- a review is dispatched without the CI runs and head-bound ledger receipts attached, and the pass is spent on evidence shape; every dispatch here carries --ci-run and the receipts at that head
- a reviewer's unknown asks for evidence the agent could produce, and the agent spends the remaining rounds on code instead of settling it; every open unknown is read and settled or answered before the next dispatch
- the retrospective comparison is described as test-first evidence; it is labelled as a later reconstruction with its failure causes, and the Release Owner's acceptance of that label is what the item relies on
- a model call runs without GSTACK_GOAL_LEDGER set and the spend ledger undercounts; every dispatch runs with the goal ledger named, and the count reported to Dorian is reconciled against the review records
- GitHub accepts a merge but the process dies before recording it, and resume issues a second merge request instead of recording the existing one
- a wrong-host path exists locally and is synchronized in place of the named Mac checkout
- a review restarts under a new ID and the cumulative repair limit and original findings are lost
- a ledger receipt exists but belongs to the old head or another repository and is read as proof of the current candidate
- a selected artifact is fresh but its attested prerequisite or embedded binding is stale and a worker is dispatched anyway
- a dirty required checkout is stashed, reset or cleaned so delivery can report complete
- a goal reports complete while its declared release companion is unmerged or unrecorded
