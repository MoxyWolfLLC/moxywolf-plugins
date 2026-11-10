---
name: li-research-draft
risk_tier: generate
description: >
  The 09:30 research and drafting block for the LinkedIn GTM plan. Takes the ranked signal list,
  enriches the top people, checks connection degree, picks 3 to 5 posts worth a practitioner
  comment, and drafts comments, connection notes, DMs, follow-ups and inbound replies in Dorian's
  voice, each with a one-line reason and its sources, into today's batch ledger as drafted items.
  Use it for "/li-draft", "draft today's LinkedIn comments", "draft connection notes", "write the
  LinkedIn DMs", or as step three of /li-day. Drafts only; nothing is sent.
allowed-tools: [Read, Write, Edit, Bash]
---

# li-research-draft: from signals to drafted items

Generate tier. Reads spend `enrichment` (10 to 12 a day in weeks 1 and 2) and a little `networking_general` (degree checks). Output is drafted items in today's ledger; nothing leaves.

## Inputs

- `signals-<date>.json` from li-signals (or run li-signals first).
- Today's plan-left per bucket from `budget_check.py --json`. Draft no more of a kind than its bucket can carry, plus at most one spare per kind so Dorian has something to strike.
- `references/voice-and-craft.md`, `references/lanes.md`, `references/sequences.md`.

## Research (top signals only)

For each person worth drafting to:

1. `enrich_linkedin_person_lite_profile` with the account pinned: role, company, network distance.
2. Only if the item is a connect or DM: `enrich_linkedin_person_comment_activity` or `enrich_linkedin_person_posts` to find the thing to reference. Full profile only when the lite one leaves the lane unclear.
3. Before any DM: `check_linkedin_connection_degree`. DMs go to first-degree connections only; a second-degree person gets a connection request instead.
4. For each post to comment on: `enrich_linkedin_get_activity_urn_by_url` if you only have its URL, then `scrape_linkedin_get_post_comments` to confirm Dorian hasn't already commented.
5. CRM check for outreach items (`references/crm-sync-contract.md`).

Record what each claim in a draft rests on. A draft that cites a number, a quote or a fact carries that source URL in `--sources`.

## Draft

| Kind | Rules |
|---|---|
| comment (3 to 5 a day) | Specific point, one concrete practitioner detail, a real question. No links, brands, hashtags or pitch. 200 to 900 chars. |
| reaction | Pair with each comment, and for posts worth a nod but not a comment. Pick from like, celebrate, support, love, insightful, funny. |
| connect | Under 200 chars, tied to their work, no link. Lane A only when released. |
| dm / reply | Thank plus one question on accept; day 4 resource, no ask; day 10 close. No booking link. Set `stop_if_replied_after` on follow-ups. |
| accept / ignore | Inbound invites with a one-line reason (fit, lane, or why not). |
| visit / endorse | Sparingly, only with a reason that isn't "to get noticed". |

Add each one:

```
python3 "$P/scripts/batch_ledger.py" add --ledger "$L" --config "$CFG" \
  --kind connect --lane B \
  --args '{"public_identifier": "janeroe", "note": "Your post on crosswalk drift matched what I see in audits. Would be glad to connect.", "allow_no_note_fallback": false}' \
  --target '{"name": "Jane Roe", "identifier": "janeroe", "url": "https://www.linkedin.com/in/janeroe/", "company": "Acme GRC"}' \
  --reason "Lane B: commented on control-mapping drift yesterday, runs compliance at a 400-person SaaS" \
  --sources "https://www.linkedin.com/feed/update/urn:li:activity:..." \
  --sequence '{"name": "prospect", "step": "connect"}'
```

If `add` refuses a draft (em dash, length, link in a note, suppression, Lane A hold), fix the draft; don't work around the check. Warnings are fine to keep; they show in the batch for Dorian.

## Hand off

Tell the operator how many items per kind are drafted against plan-left, and hand to li-approval-batch. Don't present the batch from here.

Long comment work from a LinkedIn top-content page in the browser belongs to `linkedin-thought-leadership`; a comment drafted there can be added here as an item.
