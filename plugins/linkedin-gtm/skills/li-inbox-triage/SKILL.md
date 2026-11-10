---
name: li-inbox-triage
risk_tier: generate
description: >
  The 15:00 inbox triage for the LinkedIn GTM plan. Reads recent conversations through GTM API,
  sorts each into reply needed, meeting, referral, not now, or no/stop, drafts replies for
  tomorrow's batch (or flags a same-day urgent one), logs CRM events and suppressions, and queues
  mark-unread hand-backs for threads Dorian must answer himself, which run only after his decision.
  Use it for "/li-triage", "triage my LinkedIn inbox", "LinkedIn messages", "who replied on
  LinkedIn".
allowed-tools: [Read, Write, Edit, Bash]
---

# li-inbox-triage: five buckets and a hand-back

Generate tier for the reading, sorting and drafting. The one outward action, marking a thread unread as a hand-back, is a `mark_unread` batch item and runs only through `gtm_mcp.py execute` after Dorian decides it (side-effectful-gated).

## Read

1. `get_my_latest_linkedin_conversations` (page_size 25) for threads with new inbound messages since the last triage.
2. `get_my_latest_linkedin_messages` for each such thread (`linkedin_conversation_sid`).

Both spend `self_account_sync`, which has plenty of room.

## Sort

| Bucket | Means | Do |
|---|---|---|
| Reply needed | They asked or said something that needs an answer | Draft a `reply` item (`linkedin_conversation_sid`, `reply_to_linkedin_message_sid`, `stop_if_replied_after` = their last message time). Tomorrow's batch, or flag urgent for a same-day decision. |
| Meeting | They want to talk | Meetings are handed to Dorian (`meetings: hand-to-dorian`): queue a `mark_unread` hand-back and log `meeting_requested`. If the config ever says `booking-link`, draft a reply with the link for his approval instead. |
| Referral | They pointed to someone else | Log both people (`referral`). Draft a thank-you if it's owed. |
| Not now | Interested later | Log `not_now` with a nurture date. No reply unless one is owed. |
| No / stop | Not interested, stop, unsubscribe | Log `stop`, add them to the suppression file today, stop any sequence. No reply beyond a short acknowledgement if Dorian wants one. |

Any reply stops that person's sequence (`references/sequences.md`).

Threads that need Dorian personally, whatever the bucket (pricing, partnership terms, anything personal or sensitive), get a `mark_unread` item:

```
python3 "$P/scripts/batch_ledger.py" add --ledger "$L" --config "$CFG" --kind mark_unread --lane D \
  --args '{"sid": "<conversation sid>"}' --target '{"name": "Jane Roe"}' \
  --reason "Asked about partnership terms; needs Dorian"
```

## Write

- CRM events as JSONL (`references/crm-sync-contract.md`), one line per event, next to the ledger: `crm-events-<date>.jsonl`.
- Summary for the digest: counts per bucket, meetings handed back, new suppressions.
- Never answer pricing, commit to terms, or invent availability in a draft.
