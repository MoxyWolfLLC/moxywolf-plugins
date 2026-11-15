# Goal run: review-packet-ready-5

- Outcome: running
- Approved in PR #321 by review 5908544208 at 3089602f9890, tree b1f92f67ceb0
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-opus-5-5
- Goal branch: goal/review-packet-ready-5 from ede29a9dd9d5
- Spend: $0 across {}; 0 counted calls

## Items

1. Refuse a packet with no data_use before anything is created - merged
2. Refuse missing coverage and a ledger run behind the head - merged
3. Read every surfaced file from the head commit (MOXY-159) - merged
4. Keep every changed file name whole - merged
5. Docs, version and the suites - merged

## Goal tests at the last merged head

- `tests/test_packet_ready.py::PacketReady.test_open_refuses_missing_data_use_before_dispatch` (outcome): passed
- `tests/test_packet_ready.py::PacketReady.test_open_refuses_ledger_run_behind_head` (outcome): passed
- `tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch` (outcome): passed
- `tests/test_packet_ready.py::PacketReady.test_complete_packet_still_opens_and_refused_stays_refused` (invariant): passed

## Digests and escalations

1. 2026-11-15T02:28:30+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: Ordering against load_packet's validation and both reviewer-session guards is item 2's; at this head an older check can still answer first.
   Against the brief: 1 of 5 items merged; 1 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_open_refuses_ledger_run_behind_head, tests/test_packet_ready.py::PacketReady.test_open_refuses_missing_data_use_before_dispatch, tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
2. 2026-11-15T02:46:34+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: Every place a reviewer-session guard lives: cmd_open, cmd_round and main(); a guard elsewhere (task_graph, dispatch) would not be covered by these tests.
   Against the brief: 2 of 5 items merged; 3 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
3. 2026-11-15T04:18:29+00:00 digest
   Item 3 merged
   Close calls: none
   Least sure of: head_blob now makes two git calls per surfaced file (type check, then show); fine at today's caps, slower on very large surfaces.
   Against the brief: 3 of 5 items merged; 3 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
4. 2026-11-15T04:40:12+00:00 digest
   Item 4 merged
   Close calls: none
   Least sure of: Other places that split git output on whitespace (release lane counts, dependency scans) were not audited; only changed_files was in scope.
   Against the brief: 4 of 5 items merged; 4 of 4 goal tests passing; spend $0, 0 counted calls
5. 2026-11-15T05:02:51+00:00 digest
   Item 5 merged
   Close calls: none
   Least sure of: Docs only; whether the refusals table stays in step with peer_review.py rests on review, no test ties them.
   Against the brief: 5 of 5 items merged; 4 of 4 goal tests passing; spend $0, 0 counted calls

## Delivery

- final (PR #None into main)
  - merge: not merged
  - release record: not recorded
