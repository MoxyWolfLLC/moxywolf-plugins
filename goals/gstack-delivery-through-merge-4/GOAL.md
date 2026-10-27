## Serves
Eleventh objective: goal mode

## Outcome
Successor to `gstack-delivery-through-merge-3` (PR #250, approved at 776ec7c), which merged its item 1 into goal/gstack-delivery-through-merge-3 (PR #251, d0efc48; sync PR #253) and stopped on item 2 at the review limit: review `20261026-180817-58f76ff-f90zynfn` used its three rounds and ended rounds_exhausted at b321160 (PR #254) with every blocking finding resolved, no regression, and one acceptance criterion unmet, "the new and changed tests fail before the functions change and pass after". That criterion's chronological reading cannot be established from the record: every commit on the branch changes tests and implementation together, and the reviewer's unknown `3107b5e1e958` asking for a fail-before execution was raised in round 1 and left unsettled through rounds 2 and 3, an evidence omission by the agent, not a code defect. What exists instead is a retrospective comparison made after the review closed, recorded with its actual failure causes in the run record (`goal-runs/gstack-delivery-through-merge-3/item2-retrospective-evidence.md`): the item's tests applied over the pre-change implementation at d0efc48 do not pass (receipts 26f283ab9948, 0b4dd9f67655, b823d57686d7, 9e2c26f20696 on scratch branch `scratch/item2-fail-before`, never pushed), and 3 of the 27 failing tests fail for a behavioral reason while 23 fail because a module, function or state key does not exist yet and one file cannot be imported at all. This brief asks the Release Owner to accept that retrospective comparison, labelled as such, in place of the chronological criterion. It does not claim the original requirement was met.

Item 1 here is goal-3's item 2 at the unchanged candidate b321160 with exactly one further review pass, its fourth cumulative, under a new review ID dispatched with the CI runs, the head-bound ledger receipts and the retrospective receipts attached from the start, the unknown closed through unknowns.py with the receipts named before the reviewer reads, and the item's fifth criterion restated as the retrospective comparison. Item 2 here is goal-3's item 3, unchanged. The whole-goal review, the release companion and synchronization of the required checkout are unchanged from the first brief.

Goal-3's item 1 is merged only on goal/gstack-delivery-through-merge-3 (d0efc48, which contains main 66d64eb through sync PR #253). So that the single item-1 pass here reviews exactly PR #254's range (d0efc48 to b321160) and not goal-3's already reviewed item 1 again, goal/gstack-delivery-through-merge-4 is opened from main by goal_run start as GO-003 requires and then fast-forwarded to d0efc48 by one push under the goal ledger's own grant on that branch, before any item PR; the whole-goal pull request into main then carries both items. If the ledger refuses that push, the run stops there with no workaround branch. PR #254 stays as goal-3's record; item 1 here opens its own pull request from the unchanged branch head into goal/gstack-delivery-through-merge-4.

All goal-3 records are preserved: its run record, PRs #251, #253 and #254, reviews `20261026-144252-d0cd67a-pk_fdgcy`, `20261026-155917-7b5e323-9ryg2d5g` (the EV-014.9 verifier fix, PR #252) and `20261026-180817-58f76ff-f90zynfn`, and every ledger receipt, reused where the head they bind to is unchanged. Spent before this goal: 11 subscription calls cumulative (4 before goal-3, 7 in it, including the three verifier-fix rounds), $0 metered, about 7h25m active across the predecessors (2h40m before goal-3, about 4h45m in it). The limits below carry the remainder forward and reset nothing: 9 calls to the unchanged 20-call cumulative operating stop, and about 4h15m of the nine active hours.

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
- active agent time exceeds 4h15m in this goal, the remainder of the nine hours approved for goal-3 after its 4h45m; the predecessors' time stays on their records; time waiting on CI or a reviewer is reported separately and does not reset the limit
- 80% of the spend cap or of Max calls is reached, as GO-004 already stops: Max calls 11 here means the stop fires at the 9th call in this goal, which with the 11 already spent is the unchanged 20-call cumulative operating stop; the nominal 11 is never reached
- a gate-owned file (goal_spend.py, goal_guard.py, goal_envelope.py, a workflow, CODEOWNERS) would have to change to reach the outcome
- the same required check fails after two repair cycles without a resolved cause
- a delivered change would need a review pass beyond its count, counting replacement review IDs and the predecessors': item 1 has used three (`20261026-180817-58f76ff-f90zynfn` rounds 1 to 3), so it gets exactly one pass here, its fourth cumulative, at b321160 and no other head; a second pass on item 1, or any commit to its candidate before that pass, stops the run; item 2 keeps three
- a review for item 1 is dispatched while unknown `3107b5e1e958` is still open, or without the retrospective receipts and their labels attached
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
