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
(best-effort by design; confirm nothing it misses is a run credential), and
the `'x'` open at the end of `run`. The exclusions in `packet.json` list what
the builder considers settled; the reviewer's authority comes from the review contract, not from this file.
