# mcp-demand-harness — Governance

This plugin follows the MoxyWolf AI Governance Manifesto. See [../../CHARTER.md](../../CHARTER.md) and [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

Release Owner: **Dorian Cougias**.

Most of the plugin reads a repo and writes local files. Three things reach further, and each is gated: running tests against a live server, releasing real customer questions into the bank, and changing the bank based on results.

## Risk tiers

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `mcp-demand-harness` | side-effectful-gated | Orchestrates the commands below. Inherits the strictest gate of whatever step it runs. |
| `demand-inventory` | read-only | Reads repo files, writes `capability-map.json` locally. |
| `demand-seed` (personas, inventory, golden) | generate | Builds the bank from docs and code already in the repo. |
| `demand-seed` (evidence) | generate | Imports usage rows with automatic redaction and test orgs dropped. Imported questions carry no release approval, and both exporters refuse to run while any `observed` question lacks one. |
| `demand-seed approve-release` | high-stakes | Releases customer-derived questions into exports that will be committed to a repo. Needs `--approver "First Last"` and an explicit `--ids` list. The name and date are recorded on each question. |
| `demand-expand` | generate | Claude drafts questions. Drafts are excluded from every export until a person accepts them. |
| `demand-export` | generate | Writes MCPJam, mcp-eval, and probe files locally. |
| `demand-run` (staging) | side-effectful-gated | Sends real requests and spends model tokens. Show the plan and target, then confirm before running. |
| `demand-run` (production) | high-stakes | `probe.py run --target production` refuses to start without `--approver "First Last"`. The command applies the same rule before any MCPJam or mcp-eval run pointed at production. |
| `demand-results ingest` | generate | Writes the gap report and `proposals.json`. Changes nothing. |
| `demand-results apply` | side-effectful-gated | Changes the bank. Needs `--approver "First Last"` and an explicit `--ids` list, refuses proposals written against an older bank, and writes who approved each change into the question's history. |

## Rules that do not bend

1. **Provenance (Test 3).** Every question names its evidence class and source. Generated questions point at a parent. The validator rejects a bank where generated questions outnumber their seeds by more than three to one for any persona. No invented customer quotes: model-written text is never labelled `observed` or `reported`.
2. **Eval traffic is not demand.** Test runs land in the product's usage logs under a test org. The profile's `evidence_exclusions` lists those orgs, and `seed.py evidence` drops their rows. Without this, the harness would read its own test traffic back as customer demand.
3. **Usage intent is private.** Fields such as STIGViewer's `api_access_logs.mcp_intent` are written by customers. Automatic redaction runs on import, but it does not reliably catch names or free-text identifiers, so a person reads each one before approving release. Unreleased questions block every export, and the text is never quoted outside the bank.
4. **Staging by default.** Every run command targets staging unless told otherwise. Production needs a named approver.
5. **No git writes.** The plugin never touches `.git/`. Claude writes the commit text, and a human pushes through GitHub Desktop.
6. **Anti-rubber-stamp (Test 4).** Approvals are recorded per question with name and date, so approval patterns can be audited. There is no approve-all: `apply` and `approve-release` act only on the ids listed, and an approver must be a first and last name, not "claude", "the team", or "owner".
