---
description: Export the bank as MCPJam v6 suites, mcp-eval datasets, and a payload and REST probe plan. Validates each format offline.
argument-hint: '<bank> --profile <profile> [--include-drafts]'
allowed-tools: [Bash, Read, Write]
---

# /mcp-demand-harness:demand-export (generate)

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts"; R=<repo>; D=$R/<bank_dir>; B=$D/demand-bank.json; M=$D/capability-map.json; PR=<profile>
python3 $S/bank.py validate --bank $B --capability-map $M --for-export
python3 $S/export_mcpjam.py  --bank $B --capability-map $M --profile $PR --out $R/.mcpjam/evals
python3 $S/export_mcpeval.py --bank $B --capability-map $M --profile $PR --out $D/mcp-eval
python3 $S/probe.py plan     --bank $B --capability-map $M --out $D/probe-plan.json
python3 $S/bank.py report    --bank $B --capability-map $M --out $D/demand-report.md
```

Then validate each format with its own tool. Do not hand off a file the tool has not loaded.

```bash
for f in $R/.mcpjam/evals/*.yaml; do mcpjam cloud eval validate --file $f --format json; done   # offline, no account needed
<mcp-eval venv>/bin/python $S/run_mcpeval.py --dir $D/mcp-eval --check
```

`--check` reports any evaluator that mcp-eval would have dropped without saying so. Report the case counts, the exact and approximated split from the MCPJam mapping report, and the skipped questions with their reasons.

`--include-drafts` is for review on staging only. Never commit draft exports.
