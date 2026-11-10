---
name: li-publish
risk_tier: high-stakes
description: >
  The 12:00 publish window for the LinkedIn GTM plan (2 to 3 days a week): publishes the post
  Dorian approved in today's batch through GTM API preview then confirm, adds the approved first
  comment with the link, then watches the first 60 minutes (golden hour) and drafts replies to
  early comments for quick same-day approval. Use it for "/li-publish", "publish today's LinkedIn
  post", "golden hour", "reply to comments on my post". Never posts unapproved content.
allowed-tools: [Read, Write, Bash]
---

# li-publish: the post, the first comment, the golden hour

High-stakes: a public post under Dorian's name. Release Owner **Dorian Cougias**. The post text comes from the 4D blog pipeline (`4d-blog-engine` blog-social), already through its diligence gate, and was approved as a `post` item in today's batch.

## Before the window

- Today is a publish day (`publish_days` in the config; Tuesday and Thursday by default) and no post has gone out today. Never two posts in a day.
- The `post` item is approved or edited, and `posting` has plan-left.
- The post body has no link (the ledger warns if it does). The link and sources live in the first comment.

## Publish

```
python3 "$P/scripts/gtm_mcp.py" execute --ledger "$L" --item <post item id>
```

Same preview, check, confirm path as li-execute. On exit 4 (uncertain), check with `check_linkedin_posting_sent` and the item's `client_reference` before anything else; never publish a second copy.

The result carries the new post's URN (`execution.result_ref` in the ledger). If no URN came back, read the latest own post via `enrich_linkedin_person_posts` for Dorian's own identifier.

## First comment

If the first comment was approved in the morning batch with the post's URN unknown, it can't run as approved (its arguments would change). Add it now as a new item with the real `entity_urn` and the approved text unchanged, present it on its own, get Dorian's quick decision, then execute it. Ask within a few minutes of the post going live: the first comment matters most early.

## Golden hour (60 minutes)

Every 15 minutes for the first hour:

1. `scrape_linkedin_get_post_comments` on the new post (spends `scraping`; four reads in the hour).
2. For each new comment worth answering, draft a reply in Dorian's voice (`references/voice-and-craft.md`): one to three sentences, answer the point, no pitch. Add it as a `comment` item with `parent_comment_urn` set to the commenter's comment URN, lane OWN.
3. Render only the new items and present them to Dorian for a quick decision. Execute what he approves.

Comment replies spend `comment_posts`. If that bucket is spent or stopped, keep drafting and hand the replies to Dorian to post himself; say so.

## After

Record the post in the CRM export, note the time it went out and the golden-hour reply count for the digest, and hand the engagers (reactors and commenters) to tomorrow's li-signals as Lane D warmth.
