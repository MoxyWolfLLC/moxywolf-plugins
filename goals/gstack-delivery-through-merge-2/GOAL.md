## Serves
Eleventh objective: goal mode

## Outcome
Successor of `gstack-delivery-through-merge`, whose run stopped on item 1 at the review limit: review `20261026-115306-aaae2fc-sccuf0td` reached fixes_verified at `55d0019` on its third pass, but goal-envelope failed there because nine F2 evidence files sat in a subfolder below the allowed path. That was an execution mistake, not a scope gap, so this brief carries the work forward unchanged: PR #247, commits `c404371..55d0019`, the review, its ledger receipts (`6f9fc276d04a`, `6d9e0a77d0f0`, `996e3df1232e`, `39870200f5af`, `7d6779d3f909`, `beb0f189cc54`, `d7eb866c3cdb`) and the elapsed budget below are reused as evidence where the head they bind to is unchanged; checks the new head requires are rerun. Item 1 resumes from `55d0019` with one correction, flattening those nine files into `docs/evidence/gstack-delivery/`, and one review pass. Items 2 and 3 are unchanged. The goal tests, their holdout and the plain-English reading are the predecessor's, byte for byte.

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
17

## Max items
3

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- active agent time exceeds two and a half hours, the remainder of the predecessor's four after its 1h30m; time waiting on CI or a reviewer is reported separately and does not reset the limit
- 80% of the spend cap or of Max calls is reached, as GO-004 already stops
- a gate-owned file (goal_spend.py, goal_guard.py, goal_envelope.py, a workflow, CODEOWNERS) would have to change to reach the outcome
- the same required check fails after two repair cycles without a resolved cause
- a delivered change would need a fourth review pass, counting replacement review IDs and the predecessor's: item 1 has used three (`20261026-115306-aaae2fc-sccuf0td`, rounds 1 to 3), so it gets exactly one pass here, pinned to the head that carries the flattening and nothing else; a second pass on item 1 stops the run
- an unreadable gate, budget, or authority record

## Pre-mortem
- a file lands outside the allowed paths and goal-envelope is read only after the last review pass; this time the envelope check at the pushed head precedes every review dispatch
- GitHub accepts a merge but the process dies before recording it, and resume issues a second merge request instead of recording the existing one
- a wrong-host path exists locally and is synchronized in place of the named Mac checkout
- a review restarts under a new ID and the cumulative repair limit and original findings are lost
- a ledger receipt exists but belongs to the old head or another repository and is read as proof of the current candidate
- a selected artifact is fresh but its attested prerequisite or embedded binding is stale and a worker is dispatched anyway
- a dirty required checkout is stashed, reset or cleaned so delivery can report complete
- a goal reports complete while its declared release companion is unmerged or unrecorded
