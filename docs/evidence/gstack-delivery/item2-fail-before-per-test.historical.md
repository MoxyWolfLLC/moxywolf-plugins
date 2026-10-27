# Historical per-test log (retrospective, not a receipt)

`item2-fail-before-per-test.historical.log` is a byte-identical copy of the log written on 2026-10-27 at
`~/.cache/mcp-audit/goal-item1/item2-fail-before-per-test.log` on Dorian's Mac, sha256 `88bb14a55fc2f795afa1e31f7ec4bc9ea59f6ea144ccb3936e0652a403f6f71f`.

What it is: a per-test rerun of goal-3 item 2's `test_ledger_evidence.py`, made after review
`20261026-180817-58f76ff-f90zynfn` closed, with the item's test files applied over the pre-change implementation
at `d0efc48` (scratch commit `254b624`, branch `scratch/item2-fail-before`). It lists 16 tests: 12 pass and 4 fail
(2 on behaviour, 2 on the absent `adjudicated_round` key).

Limits, stated rather than repaired:
- It is a plain log. It was not produced through `check_ledger.py run`, so no ledger line binds it to a head or
  hashes it at the time it was written. The hash above is of the file as it stands.
- It is retrospective: the tests were run after the implementation existed, never before it. It does not show
  test-first development, and nothing here claims it does.
- The ledger receipt for the same file (`b823d57686d7`) stops at the first exception after two tests; this log is
  the only per-test breakdown, and it is history, not a new execution.

Accepted, with this label, as retrospective evidence in PRs #255, #259 and #262. Unknown `3107b5e1e958` stays open
as a chronological question.
