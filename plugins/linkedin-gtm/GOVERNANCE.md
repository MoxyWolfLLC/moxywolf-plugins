# linkedin-gtm: Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and the one-line rule in [`../../CHARTER.md`](../../CHARTER.md).

Every skill declares a risk tier and is held to the five tests:

1. **Gate sized to stakes**: a human checkpoint before any high-stakes or irreversible action.
2. **A named human signs**: high-tier output needs one named human to approve, and the approval is recorded.
3. **Provenance**: claim-bearing output carries its source and date; no fabricated citations.
4. **Anti-rubber-stamp**: the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop**: no autonomous irreversible action; a named human owns the outcome.

## Risk surface

This plugin acts on LinkedIn as Dorian Cougias through the GTM API MCP server. Comments, reactions, reposts, posts, connection requests, DMs, invitation accepts and ignores, withdrawals, profile visits, endorsements and mark-unread hand-backs all reach real people under his name. Those are customer-reaching and public-broadcast actions: high-stakes under the charter.

It also reads a lot: account health, smart limits, inbox, profile viewers, searches and enrichment. Reads spend the account's sync, scraping and enrichment budgets but reach no one.

It writes local files only: the config, the daily batch ledger, signal lists, CRM export files. It writes to no CRM API. It writes rows to the shared gate log through `record_decision.py`.

## The gate

**The named Release Owner is Dorian Cougias.** He signs every outward LinkedIn action, one daily batch at a time, item by item. An approval binds him, the action, the person or post, the exact text and arguments, and the day. A changed item needs a new decision. Approvals don't carry over to another day.

How it runs:

1. `li-research-draft` adds drafted items to the day's ledger (`scripts/batch_ledger.py add`). The ledger refuses a draft that breaks the house rules: em dashes, unfilled placeholders, over-length notes or comments, links in connection notes, suppressed people, Lane A outreach while the partner campaign is held, or acting as another account.
2. `li-approval-batch` renders the one daily message, records when it was presented, and records Dorian's decision on each item: approve, edit (with his text) or strike, with his name and initials. The ledger refuses any approver who isn't the configured Release Owner, a vague one ("me", "the team", "Amos"), and any decision on a batch that wasn't presented.
3. Each decided item is written to the shared gate log: `python3 "GitHub/Projects/_gate-log/record_decision.py" --skill linkedin-gtm:li-approval-batch --tier high-stakes --action "<kind> <item id> (Lane <X>): <reason>" --target "<person or post>" --decision signed|edited|stopped --approver "Dorian Cougias" --requested-at <presented ISO-8601>` (`batch_ledger.py gate-log` builds and runs these). A strike is recorded as carefully as a signature. To share the rows, in `GitHub/Projects`, commit only `_gate-log/gate-decisions.jsonl`, push as the `moxywolf-agent` app, check that `git ls-remote origin refs/heads/main` equals `git rev-parse HEAD`, and pull back. A row whose push didn't land is reported as local only, and the ledger keeps it `pending` until it lands.
4. `li-execute` and `li-publish` run approved items only, through `scripts/gtm_mcp.py execute`.

## What is enforced in code, and what isn't

**Enforced by the shipped client (`scripts/gtm_mcp.py`).** Any call it makes to an outward tool must be `execute --ledger L --item ID` for an item that is approved or edited by the Release Owner, in today's batch (plan timezone), with arguments whose hash matches the approved ones, in a bucket that isn't stopped. It sends the call once to get the server's preview, refuses to confirm if the preview names different arguments, confirms once with the single-use commit token, and records the outcome. A tool on neither the read list nor the gated list is refused, as is everything on the never list (mass actions, profile edits, smart-limit changes, webhooks, browser operations, custom requests, InMail, voice). Rate limits, quota hits and blocks stop that bucket for the day; a checkpoint, login issue or `unauthorized` stops everything; `retry_after` is reported, never slept on. The server's own preview-then-confirm gate sits underneath as a second check.

**Not enforced in code.** When GTM API is connected over OAuth as an MCP server in Claude Code or Cowork, the model can call `call_tool` directly and the scripts aren't in the path. In that mode the gate is an instruction: every skill says outward work goes only through `gtm_mcp.py execute`, and the server's preview step still requires a second, deliberate call. Nothing stops someone with the API key from calling GTM API by other means. The ledger is a local file; the hash check catches an edited item, not a determined person rewriting the whole ledger. Test 1 and Test 5 are met in code for the scripted path and by instruction for the OAuth path, and this file doesn't claim more than that.

## Test by test

| Test | How this plugin meets it |
|---|---|
| 1. Gate sized to stakes | Reads run freely; every outward kind is a batch item that needs a decision. Preview then confirm on every call. |
| 2. A named human signs | The Release Owner is named in the config (Dorian Cougias). The ledger records his name, initials, decision time and response time per item; the gate log records every decision. |
| 3. Provenance | Every item carries a one-line reason and its source URLs. Drafts may cite only what a source supports (`references/voice-and-craft.md`). Reports name where each number came from and mark missing numbers missing. |
| 4. Anti-rubber-stamp | The ledger refuses drafts below the house rules, so Dorian never sees them. `batch_ledger.py stats` reports override rate and median decision time and flags `RUBBER-STAMP?` (under 10% overrides on 5 or more decisions) and `TOO-FAST?` (under 20 seconds per item); li-approval-batch shows them with every batch and li-weekly reports them. The fleet's `override_report.py` reads the same gate-log rows. |
| 5. Human above the loop | No outward action without his decision. No mass actions. No limit raising. Any limit, block or checkpoint stops the work and goes to a person. Meetings are handed to Dorian by default. |

## Skill and command risk tiers

| Skill or command | risk_tier | Gate or note |
|---|---|---|
| skill `linkedin-gtm` | generate | Orchestrator. Routes and stops at the gate; sends nothing. |
| skill `li-health` | read-only | Account, session, smart limits, quota hits, blocks. |
| skill `li-signals` | read-only | Inbound warmth, post searches, target posts, sequence steps due. Spends read budgets only. |
| skill `li-research-draft` | generate | Enrichment reads; drafted items into the local ledger. |
| skill `li-approval-batch` | side-effectful-gated | The gate itself. Its side effects are the decision record and gate-log rows; it sends nothing to LinkedIn and records only the Release Owner's own decisions. |
| skill `li-execute` | **high-stakes** | Reactions, comments, reposts, accepts, ignores, replies, connection requests, DMs, withdrawals, visits, endorsements, mark-unread. Approved items only, preview then confirm, sequential, stop on block. |
| skill `li-publish` | **high-stakes** | Public posts and first comments; golden-hour replies are new items with their own decision. |
| skill `li-topic-scout` | read-only | Proposes blog topics per page with sources and candidate earned secrets. Never starts a pipeline or picks a page. |
| skill `li-blog-bridge` | generate | Drafts blog-derived page posts. Asks Dorian which page gets each long form; the ledger refuses a page post without his recorded choice. Articles are published by Dorian. |
| skill `li-inbox-triage` | generate | Reads and drafts. Its one outward action, mark-unread hand-back, is a batch item run by li-execute after a decision (side-effectful-gated). |
| skill `li-digest` | read-only | Digest and CRM export file. No CRM writes. |
| skill `li-weekly` | read-only | Metrics and ledgers. |
| `/li-day` | generate | Health, signals, drafts, present. Stops at the gate. |
| `/li-health`, `/li-signals`, `/li-digest`, `/li-weekly` | read-only | |
| `/li-draft`, `/li-triage` | generate | |
| `/li-batch` | side-effectful-gated | Records decisions and gate-log rows. |
| `/li-execute`, `/li-publish` | **high-stakes** | Approved items only. |
| `/li-setup` | side-effectful-gated | Writes the local config. A change to `release_owner` or the Lane A mode is reported to Dorian and logged. |
| `scripts/gtm_mcp.py` | high-stakes (enforcing) | The client that holds the gate for scripted calls. |
| `scripts/batch_ledger.py` | generate | Local ledger; runs `record_decision.py` for gate-log rows. |
| `scripts/budget_check.py` | read-only | Reads smart limits. |

**Skills tiered: 10** (high-stakes: 2, li-execute and li-publish; side-effectful-gated: 1; generate: 3; read-only: 4).

## Decisions in v0.1.0

- Mass actions are off. At 3 to 20 actions a day, item-by-item approval is the right size, and a mass action's canary-then-release flow would add a second approval path to keep honest. Revisit if volumes grow past what one batch can hold.
- One gate-log row per decided item, not one per batch, so override rates are per action.
- CRM sync is a file contract (`references/crm-sync-contract.md`) until the MoxyWolf CRM integration point is named. No skill writes to a CRM it finds connected.
- The plan's open decisions default to the conservative answer: Lane A engagement-only, approval at 10:15 Pacific, meetings handed to Dorian, MoxyWolf CRM only.

## What re-triggers this file

A new outward tool in `scripts/tool_policy.json`, enabling mass actions, a booking-link meeting mode, a CRM write, a scheduled run that executes without a person present, or any change to how `gtm_mcp.py` checks the ledger. Each means the five tests again and an update here before it ships.
