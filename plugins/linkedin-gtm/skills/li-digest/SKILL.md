---
name: li-digest
risk_tier: read-only
description: >
  The 16:30 end-of-day log, sync and digest for the LinkedIn GTM plan: actions taken against
  budget, replies, new conversations, meetings and risk flags in five lines or fewer, plus the CRM
  touch export. Use it for "/li-digest", "LinkedIn end of day", "what went out on LinkedIn today",
  "LinkedIn daily summary". Read-only toward LinkedIn; writes local files only.
allowed-tools: [Read, Write, Bash]
---

# li-digest: five lines, then done

Read-only toward LinkedIn. It writes the day's CRM export file and a digest; it loads nothing into any CRM.

## Gather

- `batch_ledger.py list --ledger "$L"`: executed, stopped, uncertain, struck per kind.
- `budget_check.py --live --config "$CFG" --json`: spent against plan cap.
- Inbox triage summary (li-inbox-triage), if it ran.
- `search_linkedin_account_quota_hits` and `search_linkedin_account_block_log` for today.
- `batch_ledger.py crm-export --ledger "$L" > crm-touches-<date>.jsonl`, and the triage events file.
- Gate-log rows still `pending` (local only) in the ledger.

## The digest (five lines or fewer)

```
LinkedIn 2026-11-10: GREEN
Out: 4 comments, 5 reactions, 3 connects (plan 5), 2 DMs, 1 accept. Struck 2, edited 1.
In: 3 replies, 2 new conversations, 1 meeting handed to you, 0 referrals.
Risk: none. (Or: comment_posts stopped at 11:40, rate_limited; 1 uncertain DM, checked: sent.)
CRM: 15 touches exported, 4 events; gate log 12 rows pushed (or: local only).
```

Numbers come from the ledger and the API, never from memory. If a source couldn't be read, the line says so.

Deliver it to Dorian the way the operator normally reaches him. Sending the digest to him is internal reporting, not outreach.
