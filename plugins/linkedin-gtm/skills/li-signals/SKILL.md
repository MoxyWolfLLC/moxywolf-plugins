---
name: li-signals
risk_tier: read-only
description: >
  The 09:00 signal sweep for the LinkedIn GTM plan: inbound warmth (profile viewers, invitations,
  new followers, engagers on Dorian's posts, catch-up cards), lane keyword post searches for the
  last 24 hours, target people's new posts, and sequence steps that are due. Produces a ranked,
  CRM-deduped signal list. Use it for "/li-signals", "who engaged with me on LinkedIn", "what's
  being posted about STIGs today", "LinkedIn signals", or as step two of /li-day. Read-only.
allowed-tools: [Read, Write, Bash]
---

# li-signals: who and what is worth Dorian's time today

Read-only, but it spends `self_account_sync`, `scraping` and a little `enrichment`. Check `budget_check.py` first; if `scraping` plan_left is under 5, sweep inbound only.

## Sweep

Run these through `gtm_mcp.py read` with the config's account sid. Tool details: `references/gtm-api-tool-map.md`.

1. **Inbound warmth (Lane D)**
   - `get_my_latest_linkedin_connection_invitations` (page_size 20): new invites, with the `ln_ci_` sid each accept or ignore needs.
   - `get_my_latest_linkedin_followers` (page_size 20).
   - `get_linkedin_account_my_profile_views` (page_size 20). Times are relative ("Viewed 1w ago"); keep only the last few days and skip anonymized viewers.
   - `get_linkedin_account_my_catch_up`.
   - For Dorian's posts from the last 7 days: `scrape_linkedin_get_post_comments` and `scrape_linkedin_get_post_reactors`.
2. **Discourse (Lanes A, B, C)**: per lane, one `scrape_linkedin_search_posts` with a search URL, not `filters` (only `filters.keywords` is a confirmed key):
   ```
   {"linkedin_account_sid": "<SID>", "page_size": 10,
    "url": "https://www.linkedin.com/search/results/content/?keywords=control%20mapping&datePosted=%22past-24h%22&sortBy=%22date_posted%22"}
   ```
3. **Targets**: for saved target people, `enrich_linkedin_person_posts` (enrichment; at most 3 a day in weeks 1 and 2).
4. **Sequences due**: newly accepted requests (`get_my_latest_linkedin_connection_requests` against yesterday's pending list) and executed sequence steps in earlier ledgers that are 4 or 10 days old (`references/sequences.md`). Replies stop a sequence: check `get_my_latest_linkedin_conversations`.

## Score and dedupe

- Score discourse posts against the synergy-engine topic fingerprint when there is one (`synergy-engine` plugin); otherwise against the lane keywords. Drop off-topic posts hard.
- Drop anyone suppressed (the suppression file, and the MoxyWolf CRM when it can be read), anyone with an active email sequence for the same campaign, and posts Dorian already commented on.
- Assign each signal a lane (`references/lanes.md`). Lane A signals are engagement-only.

## Output

Write `signals-<date>.json` next to the ledger and show the top 15 as a table: rank, lane, person, signal, post URL, suggested action (react, comment, connect, dm, accept, reply), one-line reason. Every row keeps its source URL. This is a list of candidates, not a plan; li-research-draft decides what makes the batch.
