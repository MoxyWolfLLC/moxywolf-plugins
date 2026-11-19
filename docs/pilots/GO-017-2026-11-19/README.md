# GO-017 pilot: three lanes on an Assignment Extraction prototype, 2026-11-19

A real run of `swarm.py` with three Claude Agent workers on the Cowork cloud host (Claude Code 2.1.328), with model-router 0.3.0 (MR-004) in the installed plugin. Isolated prototype with synthetic fixtures in a scratch repository: no cki branch, goal, pull request or deployment was touched. #571, #575 and #576 were left as they were.

## Plan

`pilot-PLAN.md` and `pilot-DEPS.json`: three items, one pinned interface (`interface/INTERFACE.md`, the record schema, the rule cards, two sample records and the fixtures, each pinned by sha256 as a contract of every item).

- `reader`: writes `reader/**`, `tests/test_reader.py`. No prerequisites.
- `engine`: writes `engine/**`, `tests/test_engine.py`. Integrates after `reader`; drafted and tested against the pinned contract meanwhile.
- `view`: writes `view/**`, `tests/test_view.py`. Integrates after `engine`.

`swarm.py check` accepted it: `{"serial": false, "max_workers": 3, "items": ["reader", "engine", "view"]}`.

## What happened (coordinator-events.jsonl)

| UTC | Event |
|---|---|
| 23:04:49 | `init` at base `60aa10e`, budget $12; one `tick` dispatched all three claims (reserved $9) |
| 23:05:02 to 23:05:25 | three Agent calls sent in one message, `model: "opus"` from `route.py recommend` (ledger: `recommended_model` opus, `requested_model` opus, `mutated: false`) |
| 23:05:28 to 23:05:29 | the host accepted all three; `launched` recorded for each |
| worker-reported | reader 23:05:28 to 23:06:03; engine 23:05:28 to 23:06:36; view 23:05:28 to 23:07:18 (all three running together from 23:05:28 to 23:06:03) |
| 23:06:19, 23:06:50, 23:08:50 | `result` recorded as each report arrived; each head diffed against its claim and accepted (2, 3 and 4 files, all inside its paths, no contract changed) |
| 23:09:31 | reader: gate `[]`, merged `c566eaf` |
| 23:09:32 | engine: gate had said `["status is drafted, not reviewed", "integration waits for reader"]` before any merge; after reader merged its head was refreshed onto the target (`refresh`, added after this run showed it missing), tests rerun, gate `[]`, merged `68a1e59` |
| 23:09:33 | view: refreshed, gate `[]`, merged `73481f0` |

Reviews in this pilot are the coordinator's integration checks (every lane's tests on the refreshed head), recorded with review id `coordinator-integration-check`. They are not cross-vendor reviews: the prototype merges nowhere real.

## End to end on the integrated head `73481f0`

Real reader output piped into the engine (not the engine's test helper):

- doc-a: 6 occurrences, reader reconciled, every disposition automatic by RC-1 v2, `done: true`, 24 model calls (synthetic stubs).
- doc-b: `[TBD by agency counsel]` split the blind council 1 to 2 against the proposal, RC-2 v1 `council_exception`, `done: false` ("1 disposition(s) not automatic: occ-ebfc98082f58-002 council_exception"), 12 model calls.
- `replay` on both records: `{"identical": true, "model_calls": 0, "differences": []}`.
- Both records equal the pinned sample records exactly.

Preview (private to Dorian until shared): the read-only record and exception page, from `view/index.html` at `73481f0`. Rendered in headless Chrome: done record buttons `['▸']` only; exception record adds exactly one `Add evidence (authorized)`; the banner "Synthetic fixtures. Sample rulings, not saved." is present.

## Not verified

- No cross-vendor review of the prototype lanes.
- Cost per worker: the host reported tokens (134,634, 149,534 and 149,029), not dollars; each reservation was settled at its $3 estimate.
- The confirmed-launch ledger line (`post-tool-use`) is not wired into hooks.json yet, so the router ledger shows requests only; the coordinator's `launched` events are the launch record here.
- Visual design and screen-reader behaviour of the page beyond the one screenshot.
