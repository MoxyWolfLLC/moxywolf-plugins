---
description: Run the discovery pass, the strict pass, or the direct probes against a live server. Staging by default; production needs a named approver.
argument-hint: '[discovery | strict | probe] [--target staging|production] [--approver "First Last"]'
allowed-tools: [Bash, Read, Write]
---

# /mcp-demand-harness:demand-run (side-effectful-gated)

This step sends real requests and spends model tokens. Show the plan before running anything: the target URL, the case count, the iterations, the model, and roughly how many calls that adds up to. Then wait for a yes.

Environment: the profile's `auth.token_env` (for STIGViewer, `STIGVIEWER_API_TOKEN`, a test-org token) and `ANTHROPIC_API_KEY`. Do not print either one.

Run discovery first. It names no expected tools, so it shows what the model reaches for. Run strict once discovery has been ingested.

## MCPJam

```bash
mcpjam test .mcpjam/evals/<product>-discovery.yaml \
  --server <server_name>=<target mcp_url> --access-token "$<TOKEN_ENV>" \
  --inference byok --reporter json-summary --out <bank_dir>/runs/mcpjam-discovery.json
```

Approximated strict cases are disabled. To run one, name it and give a reason. A blanket flag does not exist:
`--allow-approximated q-0014 --approval-reason "any-of tool choice reviewed by First Last"`.
Local runs do not execute the LLM judge, so rubric checks need mcp-eval or a cloud run.

## mcp-eval

```bash
<venv>/bin/python $S/run_mcpeval.py --dir <bank_dir>/mcp-eval --run discovery --out <bank_dir>/runs/mcpeval-discovery
```

## Probes (no model)

```bash
python3 $S/probe.py run --plan <bank_dir>/probe-plan.json --profile <profile> --target staging --out <bank_dir>/runs/probe.json
```

For any target the profile marks `requires_named_approval`, add `--approver "First Last"`. Apply that rule to MCPJam and mcp-eval runs too: if the URL is production, stop and ask for the named approver first.
