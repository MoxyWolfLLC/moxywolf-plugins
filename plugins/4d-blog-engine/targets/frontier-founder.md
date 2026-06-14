---
target: frontier-founder
status: wired
project: The Frontier Founder
repo: FrontierFounder
canonical_domain: https://thefrontierfounder.com
post_url_pattern: https://thefrontierfounder.com/blog/<slug>
content_dir: content/blog
hero_dir: public/blog-hero
media_dir: public/blog-media
render_contract: ld-json-body-block
frontmatter_required: [title, date]
entity_author_id: https://moxywolf.com/people/dorian-cougias#author
entity_publisher_id: https://moxywolf.com#publisher
publisher_name: MoxyWolf LLC
hero_style: brand-abstract
pillar_route_pattern: https://thefrontierfounder.com/series/<pillar-slug>
pillar_schema: [Article, FAQPage, Organization]
linking_map_dir: content/blog/_clusters
auto_linker: none
---

# Target — The Frontier Founder

Fully wired. The site already renders everything this descriptor drives, so
publishing a post here needs no site-side work.

## Render contract — `ld-json-body-block`

`FrontierFounder/src/lib/posts.ts` extracts the **first**
`<script type="application/ld+json">…</script>` block from the post body,
validates it as JSON, strips it from the visible body, and renders it as a real
script tag. So every post emits **exactly one** JSON-LD block, last in the body,
as a single `@graph` (BlogPosting + author Person + publisher Organization +
FAQPage when an FAQ exists). `generateMetadata` sets `<meta description>` and
OpenGraph from the frontmatter `excerpt`, and `alternates.canonical` to
`post_url_pattern`. Curly quotes inside the JSON-LD break parsing — keep it ASCII.

The full formatting rules live in the FrontierFounder adapter command
(`plugins/frontier-founder/commands/blog-post.md`), which is the reference
implementation this target's formatting generalizes. AEO thresholds defer to the
canonical `references/aeo-checklist.md`.

## Frontmatter spec

```yaml
title: "..."
slug: the-slug
excerpt: "150–160 char meta description, declarative, keyword-first."
date: YYYY-MM-DD
author: Dorian Cougias
category: ...
heroImage: /blog-hero/the-slug.png
pillar: <pillar-slug>          # set by STEP 1.5 — the post's hub
status: draft | published
```

## Hub / pillar

The hub is a real page at `thefrontierfounder.com/series/<pillar-slug>` carrying
`Article + FAQPage + Organization` schema. **Built in Phase B** — a reusable
route at `src/app/(frontend)/series/[pillar]/page.tsx` driven by
`src/lib/clusters.ts`, which reads the linking maps in `content/blog/_clusters/`.
The route renders the pillar title + intro and lists the spokes ("In this
series") with hub JSON-LD. FrontierFounder has no site-side auto-linker, so
spoke→hub links are explicit in the post bodies (not auto-wired at render).

Linking maps live at `content/blog/_clusters/<pillar-slug>.md`. The machine-
readable fields (`pillar_title`, `hub_intro`, `hub_url`, `spokes[]`) are in the
frontmatter; the markdown body is human documentation.

## First cluster (done in Phase B)

`content/blog/_clusters/ai-fluency-for-founders.md` is the first pillar. Its two
spokes are `content/blog/polish-bias-smb-founders.md` and
`content/blog/eating-our-own-dogfood.md`, backfilled with explicit links to the
hub. New posts attach to this pillar (or start another) via the orchestrator's
STEP 1.5.
