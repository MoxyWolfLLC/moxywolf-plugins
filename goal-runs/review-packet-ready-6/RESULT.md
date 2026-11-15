# Goal run: review-packet-ready-6

- Outcome: running
- Approved in PR #329 by review 5909264350 at 984c5e01e62e, tree 458803fb646f
- Goal tests drafted by gpt, read by gemini
- Builder: claude/claude-opus-5-5
- Goal branch: goal/review-packet-ready-6 from b2204a032165
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

1. 2026-11-15T05:45:48+00:00 digest
   Item 1 merged
   Close calls: none
   Least sure of: The no-owner skip trusts load_packet's malformed_packet to refuse a packet with neither owner nor release_owner.
   Against the brief: 1 of 5 items merged; 1 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_open_refuses_ledger_run_behind_head, tests/test_packet_ready.py::PacketReady.test_open_refuses_missing_data_use_before_dispatch, tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
2. 2026-11-15T06:38:33+00:00 digest
   Item 2 merged
   Close calls: none
   Least sure of: Whether every caller that builds a packet for a graph peer node keeps passing --accept-narrow-packet; task_graph.py is the only one today.
   Against the brief: 2 of 5 items merged; 3 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
3. 2026-11-15T06:57:11+00:00 digest
   Item 3 merged
   Close calls: none
   Least sure of: Whether a symlink whose target the head commits as a directory is judged correctly by _head_link_escapes; the tests cover file targets and escaping chains.
   Against the brief: 3 of 5 items merged; 3 of 4 goal tests passing (tests/test_packet_ready.py::PacketReady.test_surface_shows_head_commit_bytes_from_other_branch still failing); spend $0, 0 counted calls
4. 2026-11-15T07:13:48+00:00 digest
   Item 4 merged
   Close calls: none
   Least sure of: Whether git diff --name-only -z with core.quotePath set to false behaves the same; the -z flag disables quoting, so it should.
   Against the brief: 4 of 5 items merged; 4 of 4 goal tests passing; spend $0, 0 counted calls
5. 2026-11-15T07:37:25+00:00 digest
   Item 5 merged
   Close calls: none
   Least sure of: Whether the contract's tests row reads clearly to a reviewer about which ledger failures cost a round and which are refused before one.
   Against the brief: 5 of 5 items merged; 4 of 4 goal tests passing; spend $0, 0 counted calls

## Delivery

- final (PR #None into main)
  - merge: not merged
  - release record: not recorded
