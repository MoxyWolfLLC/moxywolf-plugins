# GTM API tool map

Every plan block, the GTM API tool that does it, the arguments that matter, the smart-limit bucket it spends, and whether it goes through preview and confirm. Checked against the live verbose catalog (`get_toolset_tools` with `verbose: true`) on 2026-11-10. Tool names drift; if a call returns `unknown tool`, re-read the toolset with `gtm_mcp.py tools <toolset> --verbose` before guessing.

How calls are made: every call goes through the `call_tool` meta-tool, `{"name": "<tool>", "arguments": {...}}`. Read tools run through `scripts/gtm_mcp.py read <tool> --args '<json>'`. Outward tools run only through `scripts/gtm_mcp.py execute --ledger <file> --item <id>`, for an item the Release Owner approved today. `scripts/tool_policy.json` is the authoritative list of which is which.

Account in every call: `linkedin_account_sid` (or `sid` on account-scoped tools) is the config's `account_sid`. The ledger fills it and refuses any other account.

## 08:30 Health and safety (read-only)

| Need | Tool | Key arguments | Bucket |
|---|---|---|---|
| Account status, premium, sync window, browser session | `get_linkedin_account` | `sid`, `include: ["antidetect_browser", "linkedin_account_snapshot"]` | none |
| Today's budgets and flags | `search_linkedin_account_smart_limits` | `filter: {linkedin_account_sid: {eq: sid}}`, `page_size: 50` | none |
| Yesterday's quota hits | `search_linkedin_account_quota_hits` | `filter: {linkedin_account_sid: {eq: sid}}` | none |
| Blocks | `search_linkedin_account_block_log` | same filter | none |
| What actually ran | `search_linkedin_account_activity_log` | same filter | none |
| Last syncs | `search_linkedin_account_snapshots` | same filter | none |

Red means: account `status` not `active`; `included.antidetect_browser.status` is `login_issue` (signed out) or `fail_count`/`logout_count` rising; any outward smart limit with `status` not `active`, a future `hold_till` or `linkedin_quota_hit_till`, or `risk_level` other than `none`. See `budgets-and-guardrails.md`.

## 09:00 Signal sweep (read-only, spends sync, scraping and enrichment)

| Signal | Tool | Key arguments | Bucket |
|---|---|---|---|
| Inbound invitations | `get_my_latest_linkedin_connection_invitations` | `linkedin_account_sid`, `page_size`, `cursor` | self_account_sync |
| New followers | `get_my_latest_linkedin_followers` | same | self_account_sync |
| Conversations with unread or new messages | `get_my_latest_linkedin_conversations` | same | self_account_sync |
| Messages in one thread | `get_my_latest_linkedin_messages` | `linkedin_conversation_sid` | self_account_sync |
| Sent requests still pending | `get_my_latest_linkedin_connection_requests` | same as invitations | self_account_sync |
| Profile viewers (90 days, relative times like "Viewed 1w ago", `anonymized` flag) | `get_linkedin_account_my_profile_views` | `sid`, `page_size`, `cursor` | self_account_sync |
| My Network catch-up cards | `get_linkedin_account_my_catch_up` | `sid`, `cursor` | self_account_sync |
| Discourse posts, last 24 hours | `scrape_linkedin_search_posts` | `linkedin_account_sid` and either `url` (a `linkedin.com/search/results/content/?keywords=...&datePosted=%22past-24h%22&sortBy=%22date_posted%22` URL) or `filters: {keywords}` | scraping |
| Who engaged a post (yours or a target's) | `scrape_linkedin_get_post_comments`, `scrape_linkedin_get_post_reactors`, `scrape_linkedin_get_post_resharers` | `post` (URL or URN), `linkedin_account_sid`, `page_size` | scraping |
| A target person's recent posts | `enrich_linkedin_person_posts` | `profile_id` or `public_identifier`, `linkedin_account_sid` | enrichment |

Schema note: `scrape_linkedin_search_posts` takes `filters` XOR `url`. Only `filters.keywords` is confirmed; the date and sort sub-keys inside `filters` were not verified, so the skills pass a search URL with `datePosted` and `sortBy` instead.

## 09:30 Research and drafting (read-only, spends enrichment)

| Need | Tool | Key arguments | Bucket |
|---|---|---|---|
| Quick person check, with network distance when the account is pinned | `enrich_linkedin_person_lite_profile` | `public_identifier` or `profile_id`, `linkedin_account_sid` | enrichment |
| Full profile | `enrich_linkedin_person_full_profile` (or `enrich_linkedin_person_basic_profile`) | same | enrichment |
| What they comment on | `enrich_linkedin_person_comment_activity` | same | enrichment |
| Featured section | `enrich_linkedin_person_featured` | same | enrichment |
| Post URL to activity URN (needed for comments and reactions) | `enrich_linkedin_get_activity_urn_by_url` | `url` | enrichment |
| Degree check before a DM | `check_linkedin_connection_degree` | `linkedin_account_sid`, `target` | networking_general |
| House rules and how-tos | `search_knowledge` | `query`, `top_k` | none |

Spend enrichment on the top signals only: the budget is 10 to 12 reads a day in weeks 1 and 2.

## 10:30 Engagement (outward, preview then confirm)

| Batch kind | Tool | Key arguments | Bucket |
|---|---|---|---|
| reaction | `react_linkedin_post` | `entity_urn`, `reaction_type`: like, celebrate, support, love, insightful, funny (`interested` is for event posts only and silently does nothing elsewhere) | react_posts |
| comment | `create_linkedin_comment` | `entity_urn`, `text`, optional `parent_comment_urn`, `mentions`, `client_reference` | comment_posts |
| repost | `repost_linkedin_post` | `post_urn`, `text` (your thoughts), `visibility`, `client_reference` | posting |
| accept / ignore | `accept_linkedin_connection_invitation` / `ignore_linkedin_connection_invitation` | `sid` (`ln_ci_...`) | networking_general |
| reply | `send_linkedin_message` | `linkedin_conversation_sid`, `text`, `reply_to_linkedin_message_sid`, `stop_if_replied_after`, `client_reference` | send_messages |
| visit | `visit_linkedin_account_profile` | `sid`, `target` | visit_profiles |
| endorse | `endorse_linkedin_account_skill_by_id` | `sid`, `target`, `skill_id` | endorse_skills |

## 12:00 Publish (outward, preview then confirm)

| Batch kind | Tool | Key arguments | Bucket |
|---|---|---|---|
| post | `create_linkedin_post` | `text`, optional `images`, `document`, `video`, `visibility`, `scheduled_at`, `mentions`, `client_reference` | posting |
| first comment with the link | `create_linkedin_comment` on the new post's URN | as above | comment_posts |
| did it go out | `check_linkedin_posting_sent` | `linkedin_account_sid`, `client_reference` (or `activity_log_sid`) | none |
| golden hour comments | `scrape_linkedin_get_post_comments` | `post` | scraping |

The first comment is its own batch item. If the post's URN isn't known at batch time, li-publish adds it as a same-day item and asks for a quick decision.

## 13:00 Network (outward, preview then confirm)

| Batch kind | Tool | Key arguments | Bucket |
|---|---|---|---|
| connect | `send_linkedin_connection_request` | `public_identifier` or `profile_id`, `note` (plan cap 200 chars), `allow_no_note_fallback: false`, `client_reference` | send_connection_requests |
| dm | `send_linkedin_message` | `public_identifier` or `ln_id` or `linkedin_conversation_sid`, `text`, `stop_if_replied_after`, `client_reference` | send_messages |
| withdraw (Wednesday hygiene, pending over 21 days) | `withdraw_linkedin_connection_request` | `sid` (`ln_cr_...`) | networking_general |

DMs go to first-degree connections only. A connection request to the same person can't be resent for 21 days after a withdraw.

## 15:00 Inbox (outward hand-back, gated)

| Batch kind | Tool | Key arguments | Bucket |
|---|---|---|---|
| mark_unread | `mark_linkedin_conversation_unread` | `sid` (conversation) | messaging_general |

## 16:30 and Friday (read-only)

| Need | Tool | Key arguments |
|---|---|---|
| Reply rate and message volume | `get_linkedin_messages_metrics` | `filter: {linkedin_account_sid}`, `period: {from, to}` (90 days max) |
| Acceptance rate | `get_linkedin_connection_requests_metrics` | same |
| Inbound invitations | `get_linkedin_connection_invitations_metrics` | same |
| Follower growth | `get_linkedin_followers_metrics` | same |
| Content analytics, default trailing 28 days (spends self_account_sync) | `get_linkedin_account_my_analytics` | `sid`, `date_from`, `date_to` |
| SSI (spends self_account_sync) | `get_linkedin_account_my_ssi` | `sid` |
| Benchmarks | `get_latest_linkedin_benchmark` | none |

## Preview and confirm

The first call to an outward tool returns a preview, not an action: `structuredContent` with `preview: true`, `summary`, `arguments`, `validated`, `commit_token` and `expires_in_seconds` (300). The second call, with the same arguments plus `commit_token`, does it. The token is single-use and bound to the exact arguments. `gtm_mcp.py execute` does both calls, refuses to confirm if the preview names different arguments, and records the result in the ledger.

## Errors and what they mean here

| Error | Meaning | What the client does |
|---|---|---|
| `rate_limited` 429, `context.reason: bucket_saturated` | Bucket full, held, or the delay hasn't elapsed (`context.cause`) | Records `rate_limited`, stops that bucket for the day, reports `retry_after`. No retry. |
| `rate_limited` with `cause: linkedin_quota_hit` | LinkedIn itself pushed back | Records `quota_hit`, stops the bucket. |
| `limit_exceeded` 429 | Plan or platform limit | Same as rate_limited. |
| `target_blocked` 422 | The person can't be reached | Records `blocked`. Never retried. |
| `conflict` 409 with `send_outcome` unknown, in_flight or sent | A send may have happened | Records `uncertain`, exit 4. Check with `check_linkedin_message_sent` / `check_linkedin_connection_request_sent` / `check_linkedin_posting_sent` using the item's `client_reference`. Never resend under a new key. |
| `service_unavailable` 503 `browser_starting` | Cold start, about 50 seconds | Recorded as failed. A person may re-run the item after a minute; the client does not loop. |
| login issue, checkpoint, `unauthorized` | Session or credential problem | Stops all outward work for the day. |

## Never through this plugin

`create_mass_action` and the rest of the mass-action family, profile edits, smart-limit changes, custom requests, webhooks, browser operations, InMail and voice messages. The full list is the `never` array in `scripts/tool_policy.json`. `preview_mass_action` is read-only but has no use here at these volumes.
