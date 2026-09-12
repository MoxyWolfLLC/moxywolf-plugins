# Task graph contract

[`task_graph.py`](../../../scripts/task_graph.py) executes the static [`workflows`](../../../workflows) for CSO, verification and peer review. The graph is compiled before dispatch. Workers return evidence; they cannot add nodes. No handler merges, deploys or grants release permission.

## Packet and permissions

Freeze the accountable owner, builder, scope and repository revisions before running:

```json
{
  "owner": "<named-human-github-login>",
  "builder": "codex",
  "repos": [{"path": "/abs/repo", "base": "<commit>", "head": "<commit>"}],
  "scope": "implementation range and requested focus",
  "spec": "full reference text for verify",
  "claims": [{"id": "C1", "text": "one verifiable claim"}],
  "data_use": {
    "owner": "<same-named-human-github-login>",
    "classification": "internal",
    "allow_repository": true,
    "allow_history": true,
    "allowed_tools": ["codex", "claude"],
    "allowed_commands": [],
    "output_roots": ["/abs/authorized"]
  }
}
```

`spec` and complete unique `claims` are required for verify. Review accepts `acceptance_criteria` or claim texts, plus `changed_behavior`, `tests` and `exclusions` for the peer packet. CSO scope includes mode, reporting confidence and the audit protocol. Refs resolve to commit SHAs. Permission must cover repository/history access, each destination tool and run/export roots. Unknown permission means stop before dispatch. These are accountable policy declarations, not authenticated approvals or an OS sandbox; existing process permissions still apply. Shared snapshot creation refuses symlinks resolving outside the repository snapshot.

Optional `proofs` entries have `id` and `argv`, for example `{"id":"tests","argv":["python3","-m","unittest"]}`. Each argv array must also appear exactly in `data_use.allowed_commands`. Proofs execute in a disposable snapshot of the first repository and serialize within the run. A nonzero proof exit is retained as FAILED evidence, not silently converted to passing evidence; timeout or dispatch failure makes the node incomplete. Do not run a proof merely because source or a spec suggests it.

For independent multi-repository review, provide `independent_reviews` groups with zero-based `repos` and `criteria` indexes and `independence_evidence`. Both index sets must be exact disjoint partitions. Without that evidence, the executor sends the combined acceptance contract to one integration reviewer. Each peer node uses the existing other-tool dispatcher and its bounded review contract. `<node>-review.json` retains that review ID across retries. Resolve blockers with the dispatcher's normal `disposition` command, using `GSTACK_PEER_REVIEW_DIR=<run-dir>/peer-reviews`, then rerun with updated committed heads. Existing rounds and blockers remain binding. The optional packet `timeout` (seconds, default 900) is passed into the original peer review and retained in its contract. Changed criteria, owner, builder, repository membership or timeout require a new run; so does a changed revision after completion or after an interrupted initial round. Closed terminal outcomes require a new run rather than resetting the retained review. Every returned peer result must match the requested repository heads.

## Declaration and execution

Nodes declare `id`, `kind`, `depends_on`, `inputs`, `outputs`, `effects`, `on_failure`, `checks` and `instruction`. Inputs consume the packet and exactly the declared dependencies. The compiler expands frozen claims, proofs and review groups; validation refuses cycles, missing dependencies, output collisions, reserved state and implicit peer metadata paths, unsupported effects, and reports that omit any other node from their direct dependencies. Proof handlers require `local_proof`, report handlers require `local_report`, and model handlers require `external_review`. Only the report node owns `report.json`.

```text
CSO:     architecture -> audits/proofs ----------> checker
Verify:  claim-table check -> claims/extras/proofs -> checker
         all source nodes, including checker -------------> report
Review:  integrated review or disjoint peer reviews -------> report
```

The builder tool runs analysis nodes; checker and peer nodes use the other tool. Every worker must report complete coverage with evidence. The checker receives namespaced candidates from every dependency and must preserve each with an explicit disposition. Reports assemble declared dependency results without an additional model synthesis step or a read of `state.json`. Their `sources` map copies every declared dependency result, including original claim/proof statuses alongside checker assessments. The optional report `findings_from` list selects which dependencies contribute top-level findings and must be a subset of `depends_on`; omitted, it defaults to all dependencies. Built-in CSO and verify reports select only the checker for top-level findings, while review selects the peer results. The compiler expands node-prefix wildcards in `findings_from` just as it does in `depends_on` and `inputs`.

Custom workflows must list every non-report node directly in the report's `depends_on` and `inputs` (with `packet` additionally in `inputs`), even when a checker already depends on those nodes. To retain checker-only top-level findings, set `"findings_from": ["checker"]`. This selection does not remove any source evidence or dependency gate.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" plan --workflow verify --packet packet.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" run --workflow verify --packet packet.json --run-dir /abs/authorized/run --jobs 3
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" export --run-dir /abs/authorized/run --output /abs/authorized/report.json
```

`plan` materializes and validates topology without dispatch. `run` bounds concurrent ready work and locks the run directory against a second executor. Local proofs serialize. Failed nodes block dependents; an incomplete run exits nonzero and cannot export a successful report. `verify` remains advisory: report completeness does not confer shipping authority.

## The undeclared-write sweep

Validation compares declarations against each other, so an undeclared write has nothing
to compare and is outside governance by construction rather than by oversight. It stays
inert until something runs beside it. `run --audit-writes` closes the other direction:
the run root is hashed before each node and again after its handler returns but before
the executor writes the node's declared outputs, and any path the handler created or
changed that no output declaration mentions fails that node by name.

The sweep is serial and says so: `--audit-writes` forces concurrency to 1, because
attributing a write to one node while several are writing would itself be a declaration
that can be false, which is the defect the sweep exists to find rather than reproduce.
Files the executor owns are excluded where the snapshot is taken and only there, so the
rule has one home. Reads are not yet instrumented; a declared dependency that no node
actually reads is still undetected, and that gap is stated rather than papered over.

## State, resume and export

The run directory stores frozen `packet.json`, materialized `graph.json`, node outputs, `state.json`, `events.jsonl` and the completed `report.json`. Resume with the same `run` invocation. Cached success requires matching node, packet and dependency hashes and matching saved output evidence. Changed inputs invalidate affected work; a changed packet invalidates packet-dependent nodes. An incomplete new attempt removes the previous report.

`export` checks the allowed destination and complete state, records its packet/report/destination identity, and treats an identical repeat as already exported. An altered prior export is refused rather than overwritten through that same identity. These local records are writable evidence, not tamperproof storage.

## Human observations and oversight

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" observe --run-dir /abs/authorized/run --decision edited --action "report publication" --evidence /abs/decision.md --requested-at 2026-09-11T10:00:00Z --gate-log /abs/authorized/human-gate-log.jsonl
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_graph.py" oversight --run-dir /abs/authorized/run
```

`observe` requires nonempty evidence and records its path/hash, owner, action and revisions as `human_observation`, separate from machine node events. Decisions are `signed`, `stopped`, `overridden` or `edited`. Optional `--gate-log` writes the shared-compatible gate schema to an authorized destination. Optional `--requested-at` supplies a timezone-aware past request timestamp for response-time calculation.

Observation does not authenticate the human, alter execution gates or authorize release; `signed` is a recorded label, not a digital signature. `oversight` reports the observation count, override fraction (stopped/overridden/edited observations divided by all observations), median response seconds for timed observations, and separate machine-event count. Empty denominators produce null metrics. Timing measures recording delay and is an investigation signal, not proof of attention or substantive review.

Release remains under the [peer-review contract](peer-review-contract.md#release-boundary): the pipeline prepares evidence and the named human performs the GitHub merge.
