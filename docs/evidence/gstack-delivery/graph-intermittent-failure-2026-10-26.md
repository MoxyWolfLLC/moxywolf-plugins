# Intermittent graph test failure, kept open (goal gstack-delivery-through-merge, item 1)

**Test:** `test_task_graph.GraphTests.test_command_handler_input_carries_provenance_for_every_key`
**Candidate:** graph-context `d389119` (runtime subset landed by this item, unchanged)
**Reproduced once:** 2026-10-26, sequential full run of `test_task_graph.py` (55 tests, 1 failure); the executor exited 1 with empty stderr and empty stdout, so the run record holds no diagnostic text.
**Log:** `~/.cache/mcp-audit/flaky/candidate-d389119-sequential-FAIL-20261026T173505Z.log`, sha256 `b4d1d2e4dcc2df309e846a4e48ebbdc9b1035af37fad7b8dfa9319a969863480` (outside the repository: a session cache, not durable evidence; copied here by hash only).
**Isolation:** passes 6/6 when run alone; the stress scripts in the same cache folder did not reproduce it.

Status: **unresolved**. No retry was added, no assertion weakened, no timeout raised. A green run of the file in this item's receipts is one run that passed, not evidence the cause is gone. Resolution is a separate change with its own review.

## Candidate-to-head comparison (review F2, 20261026-115306-aaae2fc-sccuf0td)

`git diff --stat d389119 -- <runtime subset>` at this item's head, where the subset is `graph_context.py`, `test_graph_context.py`, `task_graph.py`, `test_task_graph.py`, `references/task-graph-contract.md`, `README.md`, `commands/gstack-build.md`, `.claude-plugin/plugin.json`:

- `graph_context.py`, `test_graph_context.py`, `task-graph-contract.md`, `README.md`, `gstack-build.md`, `plugin.json`: identical to the candidate at item 1. Item 2 changed one message in `graph_context.py` (an attested artifact whose revision is not a packet repository head is now reported as `stale attested artifact <id>`, which is what the goal test `test_stale_binding_refuses_before_dispatch` reads) and moved the plugin version.
- `task_graph.py`: one line, review F1. The retained-review contract digest now includes the materialized context digest, so a completed peer review is refused for a changed context at unchanged heads (`review contract changed; use a new run for new intent`) instead of being reused. `materialize`/`verify` interfaces and CLI behaviour unchanged.
- `test_task_graph.py`: two added tests, `test_every_context_refusal_starts_zero_workers_and_makes_no_run_directory` (item criterion 2) and `test_completed_peer_review_is_not_reused_for_changed_context` (F1 regression, reproduced failing before the fix).

The candidate's copy of each runtime file sits beside this note verbatim as `candidate-d389119-<name>.d389119` (the suffix keeps test discovery away from them; flat, inside the goal's allowed path) and `compare-d389119.sh`, which prints each file's sha256 at d389119, in the retained copy and at HEAD, then the diff; it exits non-zero if a retained copy differs from d389119. Run through `check_ledger.py run` so the receipt carries the comparison.
