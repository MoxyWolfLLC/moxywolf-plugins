---
name: li-blog-bridge
risk_tier: generate
description: >
  Carries a signed 4D blog piece into the LinkedIn GTM batch as a long-form Article plus a short
  teaser post. Finds blog pieces whose Release Owner Gate is signed, asks Dorian which page the
  long form goes to (FrontierFounder, MoxyWolf LLC or STIGViewer; asked for every piece, never
  defaulted), hands the Article to him to publish on that page, then drafts the teaser post AS
  that page and its first comment as batch items for the next publish day. Use it for
  "/li-blog", "push the blog to LinkedIn", "long form and short post", "where does this piece go",
  or from /li-day on Mondays and publish days. It drafts; it never posts.
allowed-tools: [Read, Write, Bash]
---

# li-blog-bridge: one blog, one long form, one short post

The writing belongs to `4d-blog-engine`. This skill moves its output into the daily batch on a steady rhythm, and it asks Dorian Cougias where each long form goes.

## Rhythm

`long_form` in the config holds the defaults: one blog a week, the long-form Article on Tuesday, the teaser post on Thursday. Those are targets, not promises. If no signed piece is waiting, say so in the digest and move on. Never fill the slot with something that hasn't passed the gate.

## Steps

1. **Find a ready piece.** A piece is ready when its `changelog.md` carries the Release Owner sign-off ("Verified", initials, date) and it is published on its site (`/4d-blog-engine:blog-publish`). Look in the target repos the blog engine names (FrontierFounder today). Skip pieces already carried (the ledger history has their slug in `sequence`).
2. **Ask where the long form goes. Every time.** One question, its own message, not folded into the morning batch:
   "<title> is signed and live. Which page gets the long form: FrontierFounder, MoxyWolf LLC or STIGViewer?"
   Don't suggest a default, don't reuse last week's answer and don't infer it from the topic. Wait for his answer. Record it in `~/.config/linkedin-gtm/long-form-choices.jsonl` (slug, page, chosen_by "Dorian Cougias", chosen_at).
3. **Stage 1, the Article.** Run `/4d-blog-engine:blog-social` on the piece with that page as the channel. On a Company or Showcase Page it writes only `linkedin-article.md` first. GTM API has no tool that publishes a LinkedIn Article, so hand the Article to Dorian to publish on the chosen page (the page's admin view, Write article) on the Article day, and ask him for the Article URL once it's live. Don't write the teaser against a placeholder URL.
4. **Stage 2, the short post.** With the real Article URL, re-run blog-social for Stage 2 (`linkedin-post.md`, the teaser with its image, and `linkedin-first-comment.md`). Then add them to the batch for the teaser day:
   ```
   python3 "$P/scripts/batch_ledger.py" add --ledger "$L" --kind post --lane OWN \
     --args '{"text": "<linkedin-post.md body>", "images": ["<hero url>"], "author_organization_id": "<page id from config long_form.pages>"}' \
     --target '{"page": "<page name>", "page_chosen_by": "Dorian Cougias", "url": "<Article URL>"}' \
     --sequence "blog:<slug>" --reason "Teaser for <title>, long form live on <page>"
   ```
   The ledger refuses a page post when the page isn't in `long_form.pages`, the name doesn't match the id, or `page_chosen_by` isn't the Release Owner. The first comment is approved in the same batch as text only and added after the post is live (li-publish, First comment). `create_linkedin_comment` has no page identity, so that comment posts from Dorian's own profile; say so when you present it.
5. **Hand off.** li-approval-batch presents the teaser and the comment text with everything else. li-publish posts on the teaser day.

## What this never does

- Pick a page for Dorian, or post anything to a page he didn't name for that piece.
- Publish the Article (GTM API can't; Dorian does).
- Post a blog-derived item that skipped the blog engine's Release Owner Gate.
- Put a link in the post body. Links live in the first comment.
