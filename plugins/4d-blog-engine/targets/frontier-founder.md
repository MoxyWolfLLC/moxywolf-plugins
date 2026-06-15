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
auto_linker: "@moxywolf/hub-links/rehype"         # rehypeHubLinks wired in src/components/PostBody/index.tsx
hub_links_site_slug: frontierfounder              # the { site } arg passed to the adapter
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
series") with hub JSON-LD. FrontierFounder's spoke→hub auto-linker is now the
shared **`@moxywolf/hub-links`** package (`rehypeHubLinks` in
`src/components/PostBody/index.tsx`, `{ site: 'frontierfounder' }`): the first
mention of any registered pillar term auto-links at build time. So the engine
must **not** hand-insert the first-mention link in the body — the post only needs
to *mention* the term, plus an explicit closing CTA. The term must be registered
in `GitHub/hub-links/src/map.ts` for the link to fire on any property.

Linking maps live at `content/blog/_clusters/<pillar-slug>.md`. The machine-
readable fields (`pillar_title`, `hub_intro`, `hub_url`, `spokes[]`) are in the
frontmatter; the markdown body is human documentation.

## First cluster (done in Phase B)

`content/blog/_clusters/ai-fluency-for-founders.md` is the first pillar. Its two
spokes are `content/blog/polish-bias-smb-founders.md` and
`content/blog/eating-our-own-dogfood.md`, backfilled with explicit links to the
hub. New posts attach to this pillar (or start another) via the orchestrator's
STEP 1.5.
