# Noridoc: Execution Scripts

Path: @/plugins/gstack-execution/scripts

### Overview

- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) executes bounded cross-tool review and records revision-bound human release handoffs.
- [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) compiles static workflow declarations and schedules evidence-producing nodes with bounded concurrency.
- The scripts support the command workflows in [commands](/plugins/gstack-execution/commands); the [peer-review contract](/plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md) supplies the reviewer-facing rules.

### How it fits into the larger codebase

- [gstack-build.md](/plugins/gstack-execution/commands/gstack-build.md) supplies approved acceptance criteria and the human Release Owner's GitHub login to [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py). Machine review establishes readiness for a human release decision.
- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) routes Claude builders to Codex and Codex builders to Claude, using detached Git snapshots and explicit model floors. The reviewer receives the packet and contract; the builder owns fixes.

- [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) consumes [workflows](/plugins/gstack-execution/workflows) rather than interpreting command prose as topology. CSO and verify send independent branches to an other-tool checker before deterministic report assembly; review uses the peer dispatcher, with fan-out only for explicit disjoint repository/criterion partitions.

```text
command -> frozen packet + workflow -> executor -> worker evidence
                                         |              |
                                         +-> checker <--+
                                               |
                                            report
```

### Core Implementation

- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) resolves packet refs to commit SHAs and persists packets, rounds, dispositions, and state under the review ID. `GSTACK_PEER_REVIEW_DIR` overrides the default local review root.
- `validate()` in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) requires exact acceptance coverage, boolean results, and nonblank evidence. Fix rounds account for every prior blocker with an explicit resolution and compatible disposition. Malformed or incomplete results cannot produce a passing round.
- `cmd_round()` in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) advances fix-round bases to preceding heads, records failures as named outcomes, and tears down snapshots. Nonpassing rounds exit nonzero; terminal outcomes require a new review.
- `cmd_release()` in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) revalidates evidence and clean local heads, writes or reuses the same revision/action handoff without resetting its request timestamp, and stops with `awaiting_human_release`. `cmd_record_release()` reads GitHub's merge record and writes the exact head, actor, merge commit, and source into a local decision.

- `compile_graph()` and `validate_graph()` in [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) materialize packet-defined claims, proofs and review groups before dispatch, require consumed dependencies and distinct output ownership, and reject cycles or unconsumed results. `execute()` locks the run directory, schedules ready work within the concurrency cap, serializes proof effects and blocks descendants of failed nodes.
- [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) persists packet, graph, node outputs and execution state. Resume hashes the node, packet and dependency results and verifies output hashes before reusing success. Deterministic reports retain all successful node results in `sources`, keeping original claim/proof statuses alongside checker assessments. Report export requires complete state and an allowed output root; repeated identical exports reuse the recorded identity.
- [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) checks policy owner, classification, repository/history permission, tool destinations and exact command argv before dispatch. Proofs run in a disposable repository snapshot and preserve exit status and output as advisory evidence. The [task graph contract](/plugins/gstack-execution/skills/gstack-execution/references/task-graph-contract.md) defines packet fields and command usage.
- Peer nodes in [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) retain dispatcher IDs in per-node markers. Retrying uses the same bounded review and requires normal blocker dispositions; changed intent or a new revision after completion requires a new run. Shared snapshot creation in [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) rejects escaping symlinks.
- [governance.py](/plugins/gstack-execution/scripts/governance.py) supplies shared `data_permission()` checks to graph execution and direct peer review. Its `gate_record()` deduplicates observation identity under a lock and calls a colocated shared `record_decision.py` when available, otherwise appending the compatible schema itself.
- `observe()` in [task_graph.py](/plugins/gstack-execution/scripts/task_graph.py) stores evidence-linked human observations separately from machine events and can append shared-compatible gate records. `oversight()` computes override fractions and median response times only from observations; it does not turn these records into execution authority.

### Things to Know

- [peer_review.py](/plugins/gstack-execution/scripts/peer_review.py) rejects blocking deferral and evidence-free disproof. A deferred blocker requires an approved design amendment and a new review under the [contract](/plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md).
- [GOVERNANCE.md](/plugins/gstack-execution/GOVERNANCE.md) separates authorized branch work from human merge authority. Local records are writable and are not signatures; external branch protection and withholding human merge credentials from agents establish the operational boundary.

Created and maintained by Nori.
