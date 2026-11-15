## Serves
Fourth objective: execution economy

## Outcome
Dorian, 2026-11-13: "Write a goal to focus on items 1 through 3 without requiring my intervention." This goal is the third of those items, the 2026-10-31 handoff's "make review packaging stop wasting rounds", together with MOXY-159: `peer_review.py` refuses to dispatch a packet missing `data_use`, attached coverage, or a ledger run at the head it's sending, and it reads every surfaced file from the head commit, never the working tree. It succeeds review-packet-ready-4, which built all four items and passed its goal tests but failed its holdout on 2026-11-14: a second copy of the reviewer-session guard in `peer_review.py`'s `main()` still refused before the new checks, with exit 1. Its whole-goal review also held a pre-existing bug: `changed_files` splits changed file names on whitespace. This goal carries the reviewed code from review-packet-ready-4's goal branch, fixes both, and keeps every decision Dorian made in review-packet-ready-3 and -4. Dorian, 2026-11-14: "I need you to design and build this system and let me know when I can test what's in production." Judgment calls inside this brief's envelope are the builder's to make and record, not Dorian's.

## Non-goals
- building a missing `data_use` block, coverage report or ledger run for the builder; a missing part is refused, not filled in
- weakening any refusal `peer_review.py` or `task_graph.py` makes today, including the graph's own `data_use` governance
- changing which reviewer is chosen or how a round is scored
- changing anything under `agent_token.py`, `governance.py` or `run_all_tests.py`
- editing anything under `goals/` other than this goal's own folder; a completed goal's tests are frozen and are not kept passing against later gates
- changing what an existing test asserts, except: a test may gain the `data_use` and `coverage` blocks its fixture packet now needs, or `--accept-narrow-packet` where it is about a packet without coverage; a test asserting a check this goal moves to `open` changes to expect the refusal at `open`; and these six, Dorian's calls in review-packet-ready-3, carried by review-packet-ready-4: in `test_ledger_evidence.py`, the stale-run case of `test_a_named_run_at_an_older_head_or_with_a_tampered_or_foreign_receipt_cannot_clear_the_fix`, `test_a_rejected_evidence_round_keeps_the_open_blockers_and_corrected_evidence_still_verifies_them` and `test_a_review_recorded_before_adjudication_tracking_survives_a_rejected_round` expect the `round` refusal with exit 2 and nothing recorded (call #1, b), and `test_h1_a_review_passing_after_a_rejected_round_releases_against_the_adjudicated_round` changes only how its stale round is refused (call #1, b); in `test_criterion_files.py`, `test_an_unreadable_named_file_opens_as_unusable_for_any_reviewer` and `test_a_named_file_that_cannot_be_read_is_unusable_and_named` expect a named file removed only from the checkout to be surfaced with its head bytes (call #3, b)
- changing what a task graph checks or how its nodes run, beyond its peer nodes opening their review with `--accept-narrow-packet`

## Scenarios
- Given a packet with no data_use block, when peer_review.py open runs, then it refuses before any reviewer is called and names data_use
- Given a packet whose named ledger run is at a commit older than the head being sent, when open runs, then it refuses and names the ledger run and both commits
- Given a checkout sitting on a different branch from the packet's head, when open builds the reviewer's surface, then every changed file shows the head commit's bytes
- A complete packet at its head being refused, or a packet that is refused today being dispatched, must never happen

## Goal tests
- `tests/test_packet_ready.py::PacketReady.test_open_refuses_missing_data_use_before_dispatch` (outcome)
- `tests/test_packet_ready.py::PacketReady.test_open_refuses_ledger_run_behind_head` (outcome)
- `tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch` (outcome)
- `tests/test_packet_ready.py::PacketReady.test_complete_packet_still_opens_and_refused_stays_refused` (invariant)

## Allowed paths
- plugins/gstack-execution/scripts/peer_review.py
- plugins/gstack-execution/scripts/task_graph.py
- plugins/gstack-execution/scripts/test_*.py
- plugins/gstack-execution/commands/gstack-peer-review.md
- plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md
- plugins/gstack-execution/README.md
- plugins/gstack-execution/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json

## Spend cap
$8

## Provider budgets
- openrouter: $5

## Max calls
40

## Max items
5

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder, any other CODEOWNERS path, or anything under `goals/` other than this goal's folder
- the marketplace's top-level version moves on the goal branch
- a refusal peer_review.py or task_graph.py makes today stops being made
- an existing test's assertion changes beyond the exceptions the Non-goals list
- a task graph's peer review is refused where it opened before
- a deploy to any environment other than goal-holdout; the repository reports no other environment, so any deploy at all is Dorian's call

## Pre-mortem
- an existing test is made to pass by weakening what it asserts, not by giving its fixture the blocks it needs
- task_graph.py's peer nodes are made to pass the coverage check with a fabricated coverage report instead of the recorded override
- open refuses a missing data_use only after it has created the review, so the round is still spent and the review folder is left behind
- the ledger check compares the run with the packet's head by a short or abbreviated SHA, so a run one commit behind still matches
- the surface reads the head's bytes for changed files but the callers XE-007 adds still come from the working tree, so the reviewer sees a mix
- the head check reads the checkout's HEAD instead of the packet's head, so a checkout on the right branch but behind passes
- a new refusal fires on the --accept-* paths that exist to open anyway, so recorded overrides stop working
- a reviewer reads a decision Dorian made in chat as unestablished, so every such decision is written into this brief before the run
- a guard or check is moved in one place while another copy of it still runs first (review-packet-ready-4's holdout failure)
