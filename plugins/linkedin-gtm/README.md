# linkedin-gtm

Daily LinkedIn go-to-market work for Dorian Cougias, run through the [GTM API](https://docs.gtm-api.com/llms.txt) MCP server, with one human approval gate a day.

Amos (the operator) prepares everything. Dorian approves one batch. Nothing outward happens without his recorded decision on that exact item, and the shipped client enforces that for every call it makes.

## The day

| Time (Pacific) | Block | Command | Skill | Tier |
|---|---|---|---|---|
| 08:30 | Health and safety check | `/li-health` | `li-health` | read-only |
| 09:00 | Signal sweep | `/li-signals` | `li-signals` | read-only |
| 09:30 | Research and drafts | `/li-draft` | `li-research-draft` | generate |
| Mon, Tue, Thu | Blog to LinkedIn: ask the page, Article, teaser | `/li-blog` | `li-blog-bridge` | generate |
| 10:15 | The approval batch | `/li-batch` | `li-approval-batch` | side-effectful-gated |
| 10:30 | Engagement | `/li-execute` | `li-execute` | high-stakes |
| 12:00 | Publish window, golden hour | `/li-publish` | `li-publish` | high-stakes |
| 13:00 | Network and outreach | `/li-execute` | `li-execute` | high-stakes |
| 15:00 | Inbox triage | `/li-triage` | `li-inbox-triage` | generate (hand-back gated) |
| 16:30 | Log, sync, digest | `/li-digest` | `li-digest` | read-only |
| Friday | Weekly report | `/li-weekly` | `li-weekly` | read-only |

`/li-day` runs 08:30 through 10:15 and stops at the gate. `/li-setup` writes the config.

## Install and set up

1. Install the plugin from the `moxywolf-plugins` marketplace.
2. Connect GTM API: OAuth for interactive reads, or an API key (`GTM_API_KEY`) or the Perplexity credential proxy for the scripts. See [`references/connection.md`](references/connection.md).
3. Run `/li-setup`. It copies [`config/linkedin-gtm.example.json`](config/linkedin-gtm.example.json) to `~/.config/linkedin-gtm/linkedin-gtm.json` and walks the fields.
4. Run `/li-health`.

The defaults answer the plan's open decisions conservatively: Lane A (the held partner campaign) is engagement-only, the batch is at 10:15 Pacific, every meeting is handed to Dorian, and the MoxyWolf CRM is the only sync target.

## What's inside

```
linkedin-gtm/
  .claude-plugin/plugin.json
  GOVERNANCE.md                 five tests, risk tiers, the Release Owner gate
  commands/                     12 commands: li-day, li-health, li-signals, li-draft, li-batch,
                                li-execute, li-publish, li-blog, li-triage, li-digest, li-weekly, li-setup
  skills/
    linkedin-gtm/               the orchestrator: routes, stops at the gate, hands off
    li-health/  li-signals/  li-research-draft/  li-approval-batch/
    li-execute/  li-publish/  li-blog-bridge/  li-inbox-triage/  li-digest/  li-weekly/
  references/
    gtm-api-tool-map.md         plan block to tool, key args, bucket, preview and confirm, errors
    budgets-and-guardrails.md   plan caps, stop rules, ramp, suppression, identity
    lanes.md  sequences.md  voice-and-craft.md
    approval-batch-format.md    the one daily message and how decisions are recorded
    crm-sync-contract.md        what goes to the MoxyWolf CRM, and how
    connection.md               OAuth, API key, credential proxy
  scripts/
    gtm_mcp.py                  refusing JSON-RPC client: reads run, outward calls need an approved item
    batch_ledger.py             the daily batch: items, decisions, execution, gate log, CRM export
    budget_check.py             smart limits against plan caps, red flags, over-budget batches
    tool_policy.json            read list, gated kinds, never list (from the live catalog)
  config/linkedin-gtm.example.json
  tests/                        stdlib unittest, mocked HTTP
```

## How the gate is enforced

- `batch_ledger.py` holds the day's items. It refuses drafts that break the house rules (em dashes, placeholders, over-length notes, links in connection notes, suppressed people, Lane A outreach while held, another account) and records decisions only from the named Release Owner, only after the batch was presented.
- `gtm_mcp.py execute --ledger L --item ID` is the only way the client makes an outward call. It checks the item is approved for today with unchanged arguments and an open bucket, gets the server's preview, refuses if the preview names different arguments, confirms with the single-use commit token, and records the result.
- A rate limit, quota hit or block stops that action type for the day; a checkpoint stops everything. The client reports `retry_after` and never loops.
- Mass actions, profile edits, smart-limit changes, webhooks, browser operations, InMail and custom requests are refused outright.

Through an OAuth-connected `call_tool`, the scripts aren't in the path and the gate is an instruction. `GOVERNANCE.md` says so.

## Works with

| Plugin or skill | Use it for | Hand-off |
|---|---|---|
| `synergy-engine` | topic fingerprint, author and citation centers, browser-based comment-first runs | its fingerprint scores li-signals; one channel per person per day |
| `linkedin-thought-leadership` (moxywolf-skills) | long practitioner comments from top-content pages | its comment rules are condensed in voice-and-craft; its drafts can be added as batch items |
| `linkedin-analytics` (moxywolf-skills) | deep reads of the analytics pages | li-weekly uses its report shape with API numbers |
| `4d-blog-engine` blog-social | writing the Article, teaser post and first comment from a signed blog | li-blog-bridge asks Dorian which page (FrontierFounder, MoxyWolf LLC or STIGViewer) for every piece, hands him the Article to publish, and drafts the teaser as a page post; li-publish posts it |

## Tests

```
for t in tests/test_*.py; do (cd tests && python3 "$(basename "$t")"); done
```

All HTTP is mocked (plus one local HTTP server); the tests never reach GTM API.
