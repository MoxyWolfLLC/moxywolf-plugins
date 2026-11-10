---
name: li-weekly
risk_tier: read-only
description: >
  The Friday weekly report for the LinkedIn GTM plan: impressions, engagement, follower growth,
  acceptance rate, reply rate, meetings, health (quota hits, blocks, checkpoints, SSI trend),
  activity against budget, the approval override rate, and experiment notes for next week. Also
  the Monday plan-the-week and Wednesday hygiene checklists. Use it for "/li-weekly", "LinkedIn
  weekly report", "how did LinkedIn do this week", "LinkedIn KPIs". Read-only.
allowed-tools: [Read, Write, Bash]
---

# li-weekly: the numbers that say whether it's working

Read-only. Uses the GTM API metrics tools for the funnel and the ledgers for activity and oversight. The report shape follows `linkedin-analytics` (moxywolf-skills); hand off to that skill when Dorian wants the analytics pages read in depth (demographics, per-post breakdowns the API doesn't return).

## Pull (period = the last 7 days, and the 7 before for the trend)

| KPI | Tool or file | Target |
|---|---|---|
| Acceptance rate | `get_linkedin_connection_requests_metrics` (`filter: {linkedin_account_sid}`, `period: {from, to}`) | 35% or more |
| Reply rate | `get_linkedin_messages_metrics` (`reply_rate_pct`) | 20% or more |
| Inbound invitations | `get_linkedin_connection_invitations_metrics` | trend |
| Follower growth | `get_linkedin_followers_metrics` | trend |
| Impressions, engagement | `get_linkedin_account_my_analytics` (`sid`, `date_from`, `date_to`) | trend |
| SSI | `get_linkedin_account_my_ssi` | trend |
| Benchmarks | `get_latest_linkedin_benchmark` | context only |
| Quota hits, blocks, checkpoints | `search_linkedin_account_quota_hits`, `search_linkedin_account_block_log`, ledger stops | zero |
| Activity against budget | the week's ledgers | inside plan caps |
| Positive replies, meetings | triage events files | count |
| Override rate, median decision time | `batch_ledger.py stats --ledger-dir "$LEDGER_DIR" --days 7` | flags explained |

The metrics tools take a period of at most 90 days.

## Report

A markdown report with: a three-line summary; the KPI table with this week, last week and target; what converted by lane (acceptance and reply rate per lane from the ledgers); the oversight line (override rate, median response, any `RUBBER-STAMP?` or `TOO-FAST?` flag, and gate-log rows still local only); health; and two or three experiment notes for next week. Every number names where it came from. A number the API didn't return is marked missing, not estimated.

## Weekly overlay checklists

- **Monday, plan the week**: pick 2 to 3 post topics from the 4D blog pipeline, refresh lane keywords and target lists, review last week's report.
- **Wednesday, hygiene**: list sent requests pending over 21 days (`get_my_latest_linkedin_connection_requests`) as `withdraw` candidates for the batch; check SSI pillars. Profile changes are Dorian's to make by hand; this plugin makes none.
- **Monthly**: lane review (what converts), voice and story-bank refresh, a look at the smart-limit ramp. The ramp is reviewed, never raised by hand.
