---
target: opencontrols
status: wired
project: OpenControls
repo: oc-website
canonical_domain: https://opencontrols.ai
post_url_pattern: https://opencontrols.ai/blog/<slug>
content_dir: content/blog
hero_dir: public/blog-hero
media_dir: public/blog-media
render_contract: ld-json-body-block
frontmatter_required: [title, date]
entity_author_id: https://moxywolf.com/people/dorian-cougias#author
entity_publisher_id: https://moxywolf.com#publisher
publisher_name: MoxyWolf LLC
hero_style: author-supplied
pillar_route_pattern: https://opencontrols.ai/series/<pillar-slug>
pillar_schema: [Article, FAQPage, Organization]
linking_map_dir: content/blog/_clusters
auto_linker: "@moxywolf/hub-links/rehype"         # rehypeHubLinks in src/components/PostBody/index.tsx
hub_links_site_slug: opencontrols                 # the { site } arg passed to the adapter
auto_linker_file: src/components/PostBody/index.tsx
default_branch_protected: true
required_checks: [unit, e2e]                      # GitHub also requires "Supabase Preview", which skips on content-only PRs
---

# Target — OpenControls

Wired. `OpenControls-AI/oc-website` (Next.js + Payload) renders file-based blog
posts with the same contract as FrontierFounder, so a post needs no site-side
work. First published spoke: `two-permission-tables-disagree` (PR #88,
2026-10-16), on the `permission-engineering` pillar.

## Render contract — `ld-json-body-block`

`src/lib/posts.ts` reads `content/blog/*.md` (README and `_`-prefixed files are
skipped), extracts the **first** `<script type="application/ld+json">` block from
the body and renders it as a real script tag. Emit exactly one JSON-LD block,
last in the body, as a single `@graph` (BlogPosting + Person + Organization +
FAQPage when an FAQ exists), ASCII only, with opencontrols.ai URLs for
`@id`, `image` and `mainEntityOfPage`. `generateMetadata` sets the canonical to
`/blog/<slug>` and the meta description from `excerpt`.

`pnpm build` runs `scripts/validate-blog.mjs` first: every published post must
have `title` and `date`, and every `heroImage` and `media[].file` must exist
under `public/`. A missing upload fails the build.

## Frontmatter spec

```yaml
title: "..."
slug: the-slug
excerpt: "150–160 char meta description."
date: YYYY-MM-DD
author: Dorian Cougias
category: ...
heroImage: /blog-hero/the-slug.png
status: draft | published
media:                      # optional
  - file: /blog-media/x.pdf
    caption: "..."
```

## Hub / pillar

Hubs render at `/series/<pillar-slug>` from `src/app/(frontend)/series/[pillar]/page.tsx`
via `src/lib/clusters.ts`, which reads `content/blog/_clusters/<pillar-slug>.md`
(`pillar_title`, `hub_intro`, `hub_url`, `hub_term`, `spokes[]`). Creating the
map makes the hub page live on the next deploy.

The auto-linker is `@moxywolf/hub-links` with `{ site: 'opencontrols' }`.
oc-website pins hub-links by commit in `pnpm-lock.yaml`, so a new hub term needs
a hub-links commit **and** `pnpm update @moxywolf/hub-links --lockfile-only` in
oc-website before it links.

## Publishing

`main` is protected. GitHub requires `e2e` and `Supabase Preview` (the second
skips on a content-only change); `unit` runs on every PR. `/blog-publish` ships
through `ship.py merge`, which waits for `unit` and `e2e` to conclude success.
Pushing straight to `main` is refused.

## Hero

Author-supplied artwork has been used so far. The shared Vault rule prefers
diagram heroes; follow the author's choice per post.

## Attribution

OpenControls content (CKI, the Living Lexicon, the decision record) is an
OpenControls project. Don't attribute it to MoxyWolf in post copy.
