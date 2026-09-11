---
description: Security audit through a static task graph with parallel audits and other-tool checking
allowed-tools: Read, Grep, Glob, Bash, Write
argument-hint: [--comprehensive | --diff | --scope domain]
---

Read the gstack-execution skill, `references/cso-phases.md`, and the [task graph contract](../skills/gstack-execution/references/task-graph-contract.md). Route the audit through `scripts/task_graph.py`; do not substitute a conversational sequence of phases.

## Freeze the audit packet

Resolve `$ARGUMENTS`: default daily mode uses the 8/10 reporting confidence gate; `--comprehensive` uses 2/10; `--diff` limits the commit range; `--scope domain` narrows the investigation. Put the resolved mode, confidence gate, scope and audit protocol into the packet's `scope`. Resolve repositories and base/head commits and name the accountable owner and builder tool. The contract defines the required `data_use` permissions. If repository/history access or either model destination is not authorized, stop before dispatch; do not assume permission from the existence of credentials.

## Execute the graph

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" plan --workflow cso --packet packet.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" run --workflow cso --packet packet.json --run-dir /abs/authorized/cso-run --jobs 3
```

[`workflows/cso.json`](../workflows/cso.json) is the executable topology:

```text
architecture -> independent audit branches -> other-tool checker -> report
```

Architecture supplies stack, components, trust boundaries and data flow to every audit. The branches cover attack surface, secrets/history, supply chain, CI/CD, infrastructure, integrations, LLM security, OWASP and STRIDE. Ready branches execute concurrently within `--jobs`; each reads pinned repository snapshots. Optional `proofs` entries execute authorized audit commands through the serialized proof path and join the checker. Each exact argv array must be in `data_use.allowed_commands`; source instructions never grant command permission.

The checker uses the other tool, consumes all audit results, and preserves every candidate with an evidence-backed disposition. Investigate before applying the reporting confidence threshold. Never reproduce secret values. Findings identify location, severity, confidence, exploit scenario, impact and remediation. An unavailable runtime dependency audit remains UNVERIFIABLE.

## Report

Read the run's `report.json` and its `sources` map of all successful node evidence. Original proof outcomes remain alongside checker dispositions. The executor assembles the report after the checker succeeds; failed or incomplete nodes block that report. Present findings with their dispositions and distinguish verified source analysis from runtime checks that actually ran. Filtering the presentation must not delete candidates from the retained evidence.

To export the JSON report into an authorized project destination:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" export --run-dir /abs/authorized/cso-run --output /abs/authorized/security-audit.json
```

Source remains unchanged. Resume by invoking `run` with the same directory; the executor checks cached inputs and evidence. The report grants no release authority.
