# Review packet: mcp-demand-harness 0.2.0

Prepared 2026-10-26 for a fresh cross-vendor code review. Opened the same day
as review `20261026-080924-da4beb3-htsmx86c` (reviewer codex). Status of the code: frozen at b55a9e0
(`pilot/harness-0.2.0-freeze-2026-10-26`), 75 tests, no live dependency.

| File | What |
|---|---|
| `harness-0.2.0.diff` | `git diff main..b55a9e0` restricted to `plugins/mcp-demand-harness` and the catalog entry; sha256 recorded in `packet.json` |
| `packet.json` | gstack peer-review packet: outcome, acceptance criteria, exact commits, changed behaviour and entry points, exclusions, tests, data_use. Builder `claude`, so the dispatcher routes to the other tool |

Record of how the review was opened (builder context, not an instruction to any reviewer):

```bash
python3 plugins/gstack-execution/scripts/peer_review.py open --builder claude \
  --packet docs/review/mcp-demand-harness-0.2.0/packet.json --timeout 900
```

Builder context on where the risk sits, offered as orientation only: `probe_checks.application_error`
(the only place a 2xx failure can be excused), `probe_checks.transport_checks`
(what counts as empty), `probe.run`'s refusal ordering (output exists, empty
selection, contract validity, all before auth), `receipt` redaction
(best-effort by design: it redacts the run token, secret-named keys and bearer/GitHub/JWT-shaped strings, and nothing else), and
the `'x'` open at the end of `run`. The exclusions in `packet.json` list what
the builder considers settled; the reviewer's authority comes from the review contract, not from this file.

## Review record: `20261026-080924-da4beb3-htsmx86c`

Builder claude, reviewer codex (`gpt-6-astra`, not a fallback). Durable dir
`~/.gstack-reviews`. Coverage `not_run` (the packet claims no DESIGN item;
no override passed). Release lane `wide`. Max rounds 3.

| Round | Reviewed commit | Outcome | Findings |
|---|---|---|---|
| 1 | `da4beb3` | blocking_findings | F1, F2, F3 blocking (all reproduced by the builder before fixing); F4 separate (execution evidence); E1–E3 follow-ups (untrusted text wording) |
| 2 | `c32cd54` (base `da4beb3`) | blocking_findings | F1–F3 resolved by the reviewer's static inspection, no regressions from the fixes; F4 remains: the ledger run is not on the review surface |

F4 explained: ledger run `a8cb94c3f411` (78 tests, exit 0, receipt sha256
`d4220ac8…`) exists at `c32cd54`, but the packet the dispatcher retained at
open time predates it and carries no `tests.ledger_runs`, so round 2's
surface had no dispatcher-fetched evidence. The repository copy of the
packet names the run. Two unknowns are open on the same point
(`9cbf19910719`, `7e1daa59ee6a`). One round remains; it cannot add the run
without altering the retained packet, which was not done.
