## Serves
Fourth objective: execution economy

## Outcome
Dorian, 2026-11-13: "Write a goal to focus on items 1 through 3 without requiring my intervention." This goal is the third of those items, the 2026-10-31 handoff's "make review packaging stop wasting rounds", together with MOXY-159: `peer_review.py` refuses to dispatch a packet missing `data_use`, attached coverage, or a ledger run at the head it's sending, and it reads every surfaced file from the head commit, never the working tree. It succeeds review-packet-ready-2, which stopped at item 1: its plan contradicted itself (two open spec-review contradictions) and its coverage refusal would have refused task_graph.py's peer reviews, which were outside its allowed paths.

## Non-goals
- building a missing `data_use` block, coverage report or ledger run for the builder; a missing part is refused, not filled in
- weakening any refusal `peer_review.py` makes today
- changing which reviewer is chosen or how a round is scored
- changing anything under `agent_token.py`, `governance.py` or `run_all_tests.py`
- changing what an existing test asserts; an existing test may only gain the `data_use` and `coverage` blocks its fixture packet now needs, or `--accept-narrow-packet` where it is about a packet without coverage, except that a test asserting a check this goal moves to `open` changes to expect the refusal at `open`
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
4

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- a refusal peer_review.py makes today stops being made
- an existing test's assertion changes for any reason other than expecting at `open` a refusal this goal moves there
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
