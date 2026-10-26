---
description: Read MCPJam, mcp-eval, and probe reports back into the bank's terms. Writes a gap report and proposals; a named person applies them.
argument-hint: 'ingest <reports...> | apply --approver "First Last" --ids ...'
allowed-tools: [Bash, Read, Write]
---

# /mcp-demand-harness:demand-results

## Ingest (generate)

```bash
python3 $S/results.py ingest --bank $B \
  --mcpjam <bank_dir>/runs/mcpjam-*.json --mcpeval <bank_dir>/runs/mcpeval-*.json --probe <bank_dir>/runs/probe.json \
  --out <bank_dir>/runs/gap-report.md
```

The ingester reads MCPJam's `eval-local-run` report from its `metadata.cases` iterations, which is where the tool calls live. It reads mcp-eval's report through the ToolSequence and FirstToolIn details. Failures are sorted into boundary-broken, payload-wrong, wrong-tool, no-tool-used, too-many-calls and answer-failed. Fix in that order, because a boundary break or a data bug makes the model-side results meaningless.

Present the gap report. For each proposal, say what it changes and why. Promotions turn a stable discovery result into a strict regression test. Tool gaps go to the product backlog, not into the bank.

## Apply (side-effectful-gated)

Only the named person, and only the ids they read:

```bash
python3 $S/results.py apply --bank $B --proposals <bank_dir>/runs/proposals.json --approver "First Last" --ids Q-0006 Q-0015
```

Apply refuses proposals written against an older bank. If the bank changed, ingest again. After applying, run `demand-export` again so the suites match the bank.
