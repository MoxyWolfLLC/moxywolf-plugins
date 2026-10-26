# Intermittent graph test failure, kept open (goal gstack-delivery-through-merge, item 1)

**Test:** `test_task_graph.GraphTests.test_command_handler_input_carries_provenance_for_every_key`
**Candidate:** graph-context `d389119` (runtime subset landed by this item, unchanged)
**Reproduced once:** 2026-10-26, sequential full run of `test_task_graph.py` (55 tests, 1 failure); the executor exited 1 with empty stderr and empty stdout, so the run record holds no diagnostic text.
**Log:** `~/.cache/mcp-audit/flaky/candidate-d389119-sequential-FAIL-20261026T173505Z.log`, sha256 `b4d1d2e4dcc2df309e846a4e48ebbdc9b1035af37fad7b8dfa9319a969863480` (outside the repository: a session cache, not durable evidence; copied here by hash only).
**Isolation:** passes 6/6 when run alone; the stress scripts in the same cache folder did not reproduce it.

Status: **unresolved**. No retry was added, no assertion weakened, no timeout raised. A green run of the file in this item's receipts is one run that passed, not evidence the cause is gone. Resolution is a separate change with its own review.
