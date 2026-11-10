---
name: li-execute
risk_tier: high-stakes
description: >
  Executes the LinkedIn actions Dorian Cougias approved in today's batch, and nothing else:
  reactions, comments, reposts, invitation accepts and ignores, inbound replies, connection
  requests, DMs, follow-ups and withdrawals, one at a time through GTM API preview then confirm,
  stopping an action type on any rate limit, quota hit or block and stopping everything on a
  checkpoint. Use it for "/li-execute", "send the approved LinkedIn items", "run the engagement
  block", "run the network block". Refuses any item without a recorded Release Owner decision.
allowed-tools: [Read, Write, Bash]
---

# li-execute: only what was signed

High-stakes. Every call here reaches a real person under Dorian's name. The Release Owner is **Dorian Cougias**; his decision on each item is already in today's ledger (li-approval-batch) or the item doesn't run.

## The one way an outward call is made

```
python3 "$P/scripts/gtm_mcp.py" execute --ledger "$L" --item <id>
```

For that item the client:

1. checks the ledger: approved or edited by the Release Owner, today's batch, arguments unchanged since the decision (hash), its bucket not stopped;
2. calls the tool once and expects a preview with a `commit_token`;
3. refuses to confirm if the preview names different arguments;
4. confirms with the token, once;
5. records the outcome in the ledger.

Never call an outward tool any other way: not through `gtm_mcp.py read`, not through an OAuth-connected `call_tool`, not with a hand-built commit token. Never edit an item's arguments to make it run; a changed item needs a new decision.

## Order and pacing

```
python3 "$P/scripts/batch_ledger.py" queue --ledger "$L" --block engagement   # 10:30
python3 "$P/scripts/batch_ledger.py" queue --ledger "$L" --block network      # 13:00
python3 "$P/scripts/batch_ledger.py" queue --ledger "$L" --block inbox        # after triage
```

Run the queue top to bottom, one item at a time, waiting for each to finish. Reactions and comments first (comment-first warm-up), then accepts and replies; connection requests and DMs in the afternoon. Before the network block, re-run `budget_check.py --live` and stop if a bucket turned red. Publishing is li-publish.

## Exit codes and what to do

| Exit | Outcome | Do |
|---|---|---|
| 0 | executed | next item |
| 3 | rate_limited, quota_hit or blocked: that bucket is now stopped for the day | skip the rest of that bucket (the client refuses them anyway), carry on with other buckets, report `retry_after` without waiting on it |
| 3 | checkpoint or login issue: everything is stopped | stop the run, tell Dorian now. Only he signs back in. |
| 4 | uncertain: a send may have happened | stop work on that person. Check with `check_linkedin_message_sent`, `check_linkedin_connection_request_sent` or `check_linkedin_posting_sent` (`linkedin_account_sid` plus the item's `client_reference`, or the `activity_log_sid` the error carried). Never re-send under a new key. |
| 1 | failed (validation, preview mismatch, server error) | report it with the message; don't retry in a loop. A 503 `browser_starting` may be re-run once after a minute by a person deciding to. |
| 2 | refused by the client (not approved, stale, stopped bucket, tampered) | that's the gate working. Report it. |

## After the block

- `batch_ledger.py list --ledger "$L"` for the per-item outcome.
- `batch_ledger.py crm-export --ledger "$L"` appends today's touches for the MoxyWolf CRM (`references/crm-sync-contract.md`).
- Report in a few lines: executed per kind against plan cap, anything stopped and why, uncertain sends and their check result.

## Never

Mass actions (`create_mass_action` and family), profile edits, smart-limit changes, webhooks, browser operations, InMail, voice notes, custom requests, posting as a company page without that exact item approved, or acting as any account but the config's. The client refuses all of these; don't look for another route.
