# Goal run: review-packet-ready-4

- Outcome: running
- Approved in PR #314 by review 5907400066 at 5cac3d759ae4, tree 8e53e4bcbf01
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-opus-5-5
- Goal branch: goal/review-packet-ready-4 from 1e0f020bcbd2
- Spend: $0 across {}; 0 counted calls

## Items

1. Refuse a packet with no data_use before anything is created - merged
2. Refuse missing coverage and a ledger run behind the head - merged
3. Read every surfaced file from the head commit (MOXY-159) - merged
4. Docs, version and the suites - merged

## Goal tests at the last merged head

- `tests/test_packet_ready.py::PacketReady.test_open_refuses_missing_data_use_before_dispatch` (outcome): passed
- `tests/test_packet_ready.py::PacketReady.test_open_refuses_ledger_run_behind_head` (outcome): passed
- `tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch` (outcome): passed
- `tests/test_packet_ready.py::PacketReady.test_complete_packet_still_opens_and_refused_stays_refused` (invariant): passed

## Digests and escalations

1. 2026-11-14T22:41:29+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: Ordering against load_packet's validation is deferred to item 2, so at this head a packet failing both data_use and an older check still gets the older refusal.
   Against the brief: 1 of 4 items merged; 1 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_open_refuses_ledger_run_behind_head, tests/test_packet_ready.py::PacketReady.test_open_refuses_missing_data_use_before_dispatch, tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
2. 2026-11-14T23:13:24+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: Whether a first round given --head should send it: this goal made it do so per criterion 2.1; callers that relied on round 1 ignoring --head would now review that head.
   Against the brief: 2 of 4 items merged; 3 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
3. 2026-11-14T23:52:16+00:00 digest
   Item 3 merged
   Close calls: none
   Least sure of: Surfacing JS and TS callers adds files to every web repo's review surface; the cap bounds it, but how often it crowds out other callers is unmeasured.
   Against the brief: 3 of 4 items merged; 4 of 4 goal tests passing; spend $0, 0 counted calls
4. 2026-11-15T00:31:36+00:00 digest
   Item 4 merged
   Close calls: none
   Least sure of: Docs only; whether the refusals table stays in step with peer_review.py rests on review, no test ties them.
   Against the brief: 4 of 4 items merged; 4 of 4 goal tests passing; spend $0, 0 counted calls

## Delivery

- final (PR #None into main)
  - merge: not merged
  - release record: not recorded
