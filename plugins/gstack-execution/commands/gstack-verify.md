---
description: Advisory implementation/spec verification through a frozen claim graph and other-tool checker
allowed-tools: Read, Grep, Glob, Bash, Write, AskUserQuestion
argument-hint: [plan=<path>] [--base <ref>] [focus ...]
---

Read the gstack-execution skill and [task graph contract](../skills/gstack-execution/references/task-graph-contract.md). This is the post-build counterpart to `/gstack-plan-review`: report whether implementation matches the spec. It never authorizes or blocks shipping on its own authority.

## Freeze the spec and claims

Resolve `plan=<path>` from `$ARGUMENTS`, else root `PLAN.md`, else the latest identified session spec. If none exists, ask "verify against what?" Resolve `--base` or the smallest commit range containing the implementation. Preserve focus text in `scope`.

Before dispatch, copy the full reference text into packet `spec` and extract every verifiable step, decision, exclusion and acceptance criterion into `claims` entries with stable unique `id` and `text`. Record named `owner`, `builder`, repository base/head pairs and authorized `data_use` destinations. This caller preparation freezes the graph's workload; workers cannot grow it. If permissions are unclear, stop before sending source to either tool.

## Execute the graph

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" plan --workflow verify --packet packet.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" run --workflow verify --packet packet.json --run-dir /abs/authorized/verify-run --jobs 3
```

[`workflows/verify.json`](../workflows/verify.json) first checks the complete claim table against the frozen spec. An omitted or distorted claim makes the node incomplete; correct the packet and rerun rather than spawning new nodes mid-run. After that check, per-claim workers and an extras scan run independently. Explicit authorized proofs run through the executor's proof path. The other-tool checker consumes the branches before deterministic report assembly.

| Claim status | Meaning |
|---|---|
| BUILT | Source implements the claim, with location evidence. |
| DRIFTED | Source differs; state the actual delta. |
| MISSING | Specified behavior is absent. |
| EXTRA | Implementation is outside the frozen claims. |
| UNVERIFIABLE | Evidence requires a runtime, external system, or human knowledge not available in this run. |

A spec's proof command is not permission to run it. Put approved argv arrays in `proofs` and the exact arrays in `data_use.allowed_commands`, as described in the contract. Record the actual result; a missing proof remains unverified. Proof tasks serialize their execution.

## Report

Read `report.json`, including its `sources` map of every successful node, and the node artifacts. Original claim and proof statuses remain alongside checker assessments. Present every claim, status and evidence, extra implementation, actual proof outcomes, and anything not verified. Preserve checker dispositions and the underlying evidence. An incomplete graph exits nonzero and cannot export a successful report; this concerns report completeness, not shipping authority.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" export --run-dir /abs/authorized/verify-run --output /abs/authorized/verification.json
```

No source fixes or spec amendments occur here. Route changes to the owning build/spec workflow. Reusing the run directory resumes valid work; changed packet, node or dependency evidence invalidates affected cached results. Human observations can be recorded separately under the task graph contract and do not change these gates.
