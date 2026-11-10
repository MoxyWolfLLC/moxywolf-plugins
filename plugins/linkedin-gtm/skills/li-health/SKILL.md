---
name: li-health
risk_tier: read-only
description: >
  The 08:30 account health and safety check for the LinkedIn GTM plan. Reads the GTM API account,
  browser session, smart limits, quota hits, blocks and recent activity, and says GREEN or RED. Use
  it for "/li-health", "is LinkedIn safe today", "LinkedIn account health", "smart limits today",
  "any quota hits", or as the first step of /li-day. Read-only; spends no outward budget.
allowed-tools: [Read, Bash]
---

# li-health: is it safe to work today

Read-only. Every call below is on the client's read list. Set `P`, `CFG` and `SID` (the config's `account_sid`) as in the `linkedin-gtm` skill.

## Steps

1. Account and session:
   ```
   python3 "$P/scripts/gtm_mcp.py" read get_linkedin_account \
     --args '{"sid": "'$SID'", "include": ["antidetect_browser", "linkedin_account_snapshot"]}'
   ```
   Check `item.status` is `active`, `included.antidetect_browser.status` isn't `login_issue`, and `fail_count` / `logout_count` haven't risen since yesterday's digest. Note `has_premium`, `has_sn`, the sync window and when the last snapshot finished.
2. Budgets:
   ```
   python3 "$P/scripts/budget_check.py" --live --config "$CFG"
   ```
   (Add `--proxy-auth` under the credential proxy.) Exit 3 means a red outward bucket.
3. Yesterday's trouble: `search_linkedin_account_quota_hits`, `search_linkedin_account_block_log` and `search_linkedin_account_activity_log`, each with `{"filter": {"linkedin_account_sid": {"eq": "<SID>"}}, "page_size": 20}`. Look at the last 24 hours.
4. If an earlier ledger has `uncertain` items, list them. They must be checked (`check_linkedin_message_sent` and friends with the item's `client_reference`) before anything new goes to the same person.

## Verdict

- **GREEN**: account active, session healthy, no red outward bucket, no checkpoint or block in 24 hours.
- **RED**: any of those fails. Name the cause, say which action types stop (or all of them), and stop. Only Dorian signs back in after a login issue; never touch the session or a smart limit.

Report in five lines or fewer: verdict, cause if red, today's plan-left per outward bucket, open uncertain sends, and anything new in the block log. Hand the budget JSON (`budget_check.py --json`) to li-approval-batch.

Errors: an `unauthorized` answer is a credential problem, not a LinkedIn one. Say so and stop; see `references/connection.md`.
