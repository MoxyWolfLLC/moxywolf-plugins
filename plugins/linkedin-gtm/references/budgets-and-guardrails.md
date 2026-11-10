# Budgets and guardrails

Two numbers per action type. The platform ceiling is the smart limit GTM API sets while it warms the account up (`daily_limit` on `search_linkedin_account_smart_limits`). The plan cap is what we choose to spend, and it never goes above the ceiling. `scripts/budget_check.py` reads both and reports what's left.

## Plan caps (plan section 5)

| Action | Bucket | Ceiling on 2026-11-10 | Weeks 1 to 2 | Week 3 and later |
|---|---|---|---|---|
| Connection requests | send_connection_requests | 5 | 3 to 5 | follow the ramp, cap 20/day |
| Messages (DMs and replies) | send_messages | 10 | 5 to 10 | 15 to 20 |
| Comments | comment_posts | 5 | 3 to 5 | 5 (quality ceiling) |
| Reactions | react_posts | 5 | 5 | 10 to 15 |
| Profile visits | visit_profiles | 8 | 5 to 8 | 15 to 20 |
| Endorsements | endorse_skills | 5 | 0 to 2 | 2 to 3 |
| Posts | posting | 4 | 2 to 3 a week, never 2 in a day | 3 a week |
| Enrichment reads | enrichment | 12 | 10 to 12 | platform ramp |
| Data pulls (searches) | scraping | 15 | 10 to 15 | platform ramp |

`budget_check.py` uses the high end of each range as the daily cap and picks the phase from `ramp_start_date` in the config. Repost spends `posting` too. Accept, ignore and withdraw spend `networking_general`; mark-unread spends `messaging_general`.

## Let the ramp happen

The ceilings are low because a newly connected account is being warmed up. Nothing in this plugin raises a smart limit, and no skill should suggest raising one by hand. `update_linkedin_account_smart_limit` and its relatives are on the client's never list.

## Stop rules

1. Any 429 (`rate_limited` or `limit_exceeded`), quota hit or block on an action type: stop that action type for the rest of the day, report it, don't retry. The ledger records the stop and `gtm_mcp.py` refuses every later item in that bucket.
2. A checkpoint, a login issue (`antidetect_browser.status: login_issue`), or an `unauthorized` answer: stop all outward work for the day and tell Dorian. Only he signs back in.
3. A red health check at 08:30: no batch today beyond read-only listening. The digest says why.
4. A send that comes back uncertain (`send_outcome` unknown, in_flight or sent on a 409): stop and check it with the matching `check_linkedin_*_sent` tool and the item's `client_reference`. Never send it again under a new key.
5. `target_blocked`: that person is done. Never retried.
6. The batch is over budget: cut items before presenting, lowest-ranked first. `budget_check.py --ledger` names the cut.

The client reports `retry_after` but never sleeps on it. A person decides whether a later run makes sense, and on a daily-saturated bucket it doesn't.

## Pacing

Calls on one account queue behind each other on the server, so parallel calls buy nothing. Execute items one at a time, in the queue order (`batch_ledger.py queue`): reactions, comments, reposts, accepts, replies, then the publish window, then connects, DMs and withdraws. Short waits are slept server-side; longer ones come back as 429 and stop the bucket.

## No hand-raising limits

Never raise a smart limit, re-enable a held bucket, or change `smart_limits_enabled`. If the ramp feels slow, that goes in the weekly report as a question for Dorian, not into an API call.

## Suppression

Nothing goes to anyone who:

- is on the suppression list (`suppression_file` in the config: one public identifier or profile URL per line, or a JSON export from the MoxyWolf CRM),
- said no, stop, or not interested in any channel,
- is in an active email sequence for the same campaign,
- is a current customer under an account owner who hasn't cleared it.

`batch_ledger.py add` refuses suppressed identifiers. The CRM check is the drafter's job before an item is added: see `crm-sync-contract.md`. A "no" in the inbox gets added to the suppression file the same day.

## Identity

Every outward call acts as the config's `account_sid` and nothing else. The ledger refuses an item for any other account, and the client never posts as a company page (`author_organization_id` is left unset unless Dorian approves that exact item).

## Other guardrails from the plan

- Outward actions always use preview, then confirm, after Dorian's approval of that item.
- No automated posting of unreviewed content and no automated profile edits.
- Bulk runs would need a canary first; at these volumes this plugin doesn't run bulk at all.
- Weekends and outside the sync window (Mon to Fri, 09:00 to 18:00 Pacific): read-only only.
