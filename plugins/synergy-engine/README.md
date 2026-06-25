# Synergy Engine

Topic-synergy outreach. Reach the people writing about your topics — and the people you cited — by adding something, never by pitching.

## The idea

Match **what you've published** against **what targets are posting**, then engage where the overlap is real. A like + a practitioner comment, the cite-then-tell lever (cite their work, or your anchor paper, in your content), and a warm connection note. The product or paper is the contribution, never the ask. And when the overlap is one you already made — you cited them — start there: the **citation center** turns your own bibliography into warm, earned outreach. The plugin **never auto-sends** — every public action goes through your own logged-in browser (or, for email, your verified sender) with an explicit OK.

## The loop

1. **Fingerprint** — distill your content (an `/answers` library, an anchor paper, repo posts, a keyword study) into themes + signature phrases. (`/synergy-fingerprint`)
2. **Discover** — two comment-first centers: AUTHOR (named profiles via `harvestapi/linkedin-profile-posts`) and CONTENT (keyword/hashtag search via `harvestapi/linkedin-post-search`). Score against the fingerprint, dedupe, queue. (`/synergy-discover`)
3. **Run the cycle** — the comment-first decision tree (Path A / Path B / cite-then-tell) in your logged-in browser, human-gated. (`/synergy-run`)
4. **Track + automate** — an xlsx tracker is the memory/dedupe/queue; an every-other-day prep task stages drafts and books a calendar block, never posting. (`/synergy-schedule`, `/synergy-status`)

## The citation center (start from who you cited)

The third center inverts the cite-then-tell lever into a front-to-back pipeline. Instead of discovering who's posting, it starts from the authors you already cited in your own paper, then reaches out to thank them — email first, then a LinkedIn connect.

1. **Harvest** — parse the paper's bibliography, triage by reachability (only named people proceed), resolve authors via OpenAlex/ORCID, dedupe against Clarify, enrich person + org via Apollo (LinkedIn-first match + a verify gate that catches wrong-person matches), verify LinkedIn identity via Apify, and draft a "we cited you" email + a hook-free connect note into a **citation registry** xlsx. (`/synergy-cite-harvest`)
2. **Run** — send email first (Mailtrap, as you, BCC you; lead with their reference, then how you used it, then your paper once), then the LinkedIn connect note. Human-gated, with the send discipline that beats the focus-race truncation bug (separate click+type, zoom-verify the note's start and end before Send) and the button-by-degree + email-gate handling. (`/synergy-cite-run`)
3. **Follow through** — detect accepted invites and fire any staged accept-reply, gated. Schedulable daily. (`/synergy-cite-accept-check`)

See `references/citation-center.md`, `references/outreach-channels.md`, and `references/citation-registry-schema.md`. Validated end to end on the Governed Autonomy paper (243 cited authors -> 68 enriched -> 157 LinkedIn-verified; 42 emails + 22 connects sent).

## Commands

| Command | Does |
|---|---|
| `/synergy-engine:synergy-init` | Configure: tracker location, fingerprint sources, anchor paper, LinkedIn channels. Creates the tracker. |
| `/synergy-engine:synergy-fingerprint` | Build/refresh the topic fingerprint. |
| `/synergy-engine:synergy-discover` | Discover + score + queue on-theme posts (author and/or content center). |
| `/synergy-engine:synergy-run` | Run the comment-first cycle via Claude in Chrome, human-gated. |
| `/synergy-engine:synergy-schedule` | Stand up the every-other-day prep task (drafts + calendar block; never posts). |
| `/synergy-engine:synergy-status` | Show the tracker: engaged / queued / due. |
| `/synergy-engine:synergy-cite-harvest` | **Citation center.** Bibliography -> OpenAlex/ORCID -> Clarify dedup -> Apollo enrich + verify gate -> Apify verify -> drafted citation registry. Never sends. |
| `/synergy-engine:synergy-cite-run` | Send the "we cited you" email (Mailtrap) then the LinkedIn connect, with the send discipline. Human-gated. |
| `/synergy-engine:synergy-cite-accept-check` | Detect accepts, fire staged accept-replies (gated), advance the registry. Schedulable. |

## Guardrails (see `references/cadence-and-guardrails.md` + `references/outreach-channels.md`)

- Never auto-sends; every public action, email, and live content edit is human-gated.
- Watch LinkedIn's "Post as" identity selector — it sits next to the like button and can silently switch your comment to a company page. Verify the actor before each comment.
- **Connect-note send discipline:** type the note in separate click+type calls (batching drops the opening characters), zoom-verify the note's start and end before Send, confirm "Pending"; never withdraw to re-send (3-week lockout); non-connections can't be free-messaged.
- **Email:** lead with their reference, then how you used it, then your paper once; BCC yourself; Mailtrap sends as the verified domain (Gmail connector is draft-only).
- Cite, don't pitch. Verified citations only — the Apollo verify gate exists because name+org matching produces wrong-person matches.
- Voice: no em-dashes, contractions, practitioner register. Cadence: <=5 fresh/run for comment centers; ~20-25 connects/day, ~100/week for the citation center.
- The tracker (post centers) and the citation registry (citation center) are the source of truth for dedupe and the queue.

## Layout

```
synergy-engine/
├── .claude-plugin/plugin.json
├── README.md
├── skills/synergy-engine/SKILL.md       # orchestrator + routing
├── commands/                            # synergy-init|fingerprint|discover|run|schedule|status
│                                        # + synergy-cite-harvest|cite-run|cite-accept-check
├── references/                          # methodology, cadence-and-guardrails, apify-actors, tracker-schema,
│                                        # citation-center, outreach-channels, citation-registry-schema
└── scripts/                             # tracker_init.py, flatten_posts.py, citation_registry.py
```

## Relationship to other plugins

Pairs with `4d-blog-engine` (which produces the posts and anchor content this engine cites) and `apollo` (the citation center uses Apollo for enrichment, but as a verify-gated lookup, not a cold sequence). Distinct from `linkedin-growth` (analytics + generic engagement) — synergy-engine is warm and content-anchored: comment-first from who's posting, or citation-first from who you cited.

MoxyWolf LLC. v0.2.0.
