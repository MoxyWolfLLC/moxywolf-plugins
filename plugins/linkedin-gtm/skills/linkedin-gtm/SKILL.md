---
name: linkedin-gtm
risk_tier: generate
description: >
  Runs Dorian Cougias's daily LinkedIn go-to-market plan through the GTM API MCP server: health
  check, signal sweep, research and drafts, ONE daily approval batch, then gated execution,
  publishing, inbox triage and the end-of-day digest. Use it for "run the LinkedIn day", "/li-day",
  "LinkedIn GTM", "what's on LinkedIn today", "prepare today's LinkedIn batch", "daily LinkedIn
  plan", or any /li-* command. This orchestrator routes to the focused li-* skills and stops at
  the approval gate; it never sends anything itself.
allowed-tools: [Read, Write, Edit, Bash]
---

# LinkedIn GTM: the daily orchestrator

The plan this runs is in `../../references/` and in Dorian's operating plan (v1, 2026-11-10). One idea holds it together: Amos prepares everything, Dorian approves one batch a day, and nothing outward happens without his decision on that exact item.

## Before anything

```
P="${CLAUDE_PLUGIN_ROOT}"
CFG="${LINKEDIN_GTM_CONFIG:-$HOME/.config/linkedin-gtm/linkedin-gtm.json}"
```

If `$CFG` doesn't exist, stop and run `/li-setup`. Read it once: `account_sid`, `release_owner`, `timezone`, `approval_time`, `lanes`, `meetings`, `crm_target`, `ledger_dir`, `suppression_file`, `gate_log_dir`. Today's ledger is `$LEDGER_DIR/<YYYY-MM-DD>.json` in the config's timezone.

Connection: read `references/connection.md`. Reads go through `scripts/gtm_mcp.py read`. Outward work goes only through `scripts/gtm_mcp.py execute` for an approved item.

## The day

| Time (Pacific) | Block | Skill | Tier |
|---|---|---|---|
| 08:30 | Health and safety check | `li-health` | read-only |
| 09:00 | Signal sweep | `li-signals` | read-only |
| 09:30 | Research and drafts | `li-research-draft` | generate |
| 10:15 | The approval batch | `li-approval-batch` | side-effectful-gated |
| 10:30 | Engagement | `li-execute --block engagement` | high-stakes |
| 12:00 | Publish window (Tue, Thu) | `li-publish` | high-stakes |
| 13:00 | Network and outreach | `li-execute --block network` | high-stakes |
| 15:00 | Inbox triage | `li-inbox-triage` | generate, hand-back gated |
| 16:30 | Log, sync, digest | `li-digest` | read-only |
| Friday | Weekly report | `li-weekly` | read-only |

`/li-day` runs 08:30 through 10:15 and stops when the batch is presented. Execution starts only after Dorian answers.

## Rules every block follows

1. Red at 08:30 means no batch. Listening may continue; nothing outward.
2. One batch a day. Same-day additions (golden-hour replies, an urgent inbound) are new items with their own decision.
3. Every draft is in Dorian's voice (`references/voice-and-craft.md`), with a one-line reason and its sources. No em dashes. No invented facts.
4. Lane A is engagement-only until Dorian releases it (`references/lanes.md`).
5. Stay inside the plan caps (`references/budgets-and-guardrails.md`). Never raise a limit.
6. On any 429, quota hit or block: that action type stops for the day. On a checkpoint: everything stops. Report; never retry.
7. Every touch is exported for the MoxyWolf CRM (`references/crm-sync-contract.md`). No writes to a CRM API from here.
8. Execute one item at a time, in queue order. Parallel calls queue on the server anyway.

## Handing off

| When | Hand to |
|---|---|
| Building or refreshing the topic fingerprint, or the citation center ("reach the authors we cited") | `synergy-engine` (`/synergy-fingerprint`, `/synergy-cite-harvest`). Its fingerprint feeds li-signals scoring. |
| Drafting long practitioner comments from a top-content page in the browser | `linkedin-thought-leadership` (moxywolf-skills). Its comment rules are condensed in voice-and-craft. |
| A deep LinkedIn analytics read from the analytics pages | `linkedin-analytics` (moxywolf-skills). li-weekly uses its report shape with API numbers. |
| Writing the post itself from a blog | `4d-blog-engine` blog-social. li-publish publishes what it produced. |

Never run synergy-engine's browser sends and this plugin's API sends on the same day for the same person: one channel per person per day.

## References

- `references/gtm-api-tool-map.md`: plan block to tool, arguments, bucket, preview and confirm, errors
- `references/budgets-and-guardrails.md`: caps, stop rules, suppression, identity
- `references/lanes.md`, `references/sequences.md`
- `references/voice-and-craft.md`
- `references/approval-batch-format.md`
- `references/crm-sync-contract.md`
- `references/connection.md`
