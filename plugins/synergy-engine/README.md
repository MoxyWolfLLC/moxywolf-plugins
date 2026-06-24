# Synergy Engine

Topic-synergy outreach, comment-first. Find the people writing about your topics and join their conversations by adding something — never by pitching.

## The idea

Match **what you've published** against **what targets are posting**, then engage where the overlap is real. A like + a practitioner comment, the cite-then-tell lever (cite their work, or your anchor paper, in your content), and a warm connection note. The product or paper is the contribution, never the ask. The plugin **never auto-posts** — every public action goes through your own logged-in browser with an explicit OK.

## The loop

1. **Fingerprint** — distill your content (an `/answers` library, an anchor paper, repo posts, a keyword study) into themes + signature phrases. (`/synergy-fingerprint`)
2. **Discover** — two centers: AUTHOR (named profiles via `harvestapi/linkedin-profile-posts`) and CONTENT (keyword/hashtag search via `harvestapi/linkedin-post-search`). Score against the fingerprint, dedupe, queue. (`/synergy-discover`)
3. **Run the cycle** — the comment-first decision tree (Path A / Path B / cite-then-tell) in your logged-in browser, human-gated. (`/synergy-run`)
4. **Track + automate** — an xlsx tracker is the memory/dedupe/queue; an every-other-day prep task stages drafts and books a calendar block, never posting. (`/synergy-schedule`, `/synergy-status`)

## Commands

| Command | Does |
|---|---|
| `/synergy-engine:synergy-init` | Configure: tracker location, fingerprint sources, anchor paper, LinkedIn channels. Creates the tracker. |
| `/synergy-engine:synergy-fingerprint` | Build/refresh the topic fingerprint. |
| `/synergy-engine:synergy-discover` | Discover + score + queue on-theme posts (author and/or content center). |
| `/synergy-engine:synergy-run` | Run the comment-first cycle via Claude in Chrome, human-gated. |
| `/synergy-engine:synergy-schedule` | Stand up the every-other-day prep task (drafts + calendar block; never posts). |
| `/synergy-engine:synergy-status` | Show the tracker: engaged / queued / due. |

## Guardrails (see `references/cadence-and-guardrails.md`)

- Never auto-posts; every public action and live content edit is human-gated.
- Watch LinkedIn's "Post as" identity selector — it sits next to the like button and can silently switch your comment to a company page. Verify the actor before each comment.
- Cite, don't pitch (competitor-founders get idea-level engagement, never the product). Verified citations only.
- Voice: no em-dashes, contractions, practitioner register. Cadence: <=5 fresh/run, comment same-day, connect 2-3 days later.
- The tracker is the source of truth for dedupe and the queue.

## Layout

```
synergy-engine/
├── .claude-plugin/plugin.json
├── README.md
├── skills/synergy-engine/SKILL.md       # orchestrator + routing
├── commands/                            # synergy-init|fingerprint|discover|run|schedule|status
├── references/                          # methodology, cadence-and-guardrails, apify-actors, tracker-schema
└── scripts/                             # tracker_init.py, flatten_posts.py
```

## Relationship to other plugins

Pairs with `4d-blog-engine` (which produces the posts and anchor content this engine cites). Distinct from `linkedin-growth` (analytics + generic engagement) and `apollo` (cold B2B sequences) — synergy-engine is warm, content-anchored, comment-first.

MoxyWolf LLC. v0.1.0.
