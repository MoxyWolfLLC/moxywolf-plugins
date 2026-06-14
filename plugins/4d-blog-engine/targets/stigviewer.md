---
target: stigviewer
status: register-only
project: STIGViewer
repo: stigviewer
canonical_domain: https://stigviewer.com
post_url_pattern: https://stigviewer.com/blog/<slug>
content_dir: apps/web/blog-posts
hero_dir: apps/web/blog-posts/images
media_dir: apps/web/blog-posts/images
render_contract: csv-row
frontmatter_required: [title, date]
entity_author_id: https://moxywolf.com/people/dorian-cougias#author
entity_publisher_id: https://moxywolf.com#publisher
publisher_name: MoxyWolf LLC
hero_style: stigviewer-brand
pillar_route_pattern: https://stigviewer.com/<pillar-slug>
pillar_schema: [TechArticle, FAQPage, Organization]
linking_map_dir: apps/web/blog-posts/_clusters
auto_linker: apps/web/lib/blog-methodology-link.tsx
---

# Target — STIGViewer

Register-only. The post pipeline + linking map work here, but STIGViewer's
site-side rendering needs Phase C work before a new post renders with full
SEO/AEO.

## Why register-only

- **Content model is CSV-driven** — posts live as rows in
  `apps/web/blog-posts/stigviewer-blog-posts.csv`, not as markdown files with a
  body JSON-LD block. The engine drafts markdown; landing it requires a
  CSV-row adapter (Phase C).
- **Post route lacks per-post `generateMetadata` + JSON-LD** — the blog `[slug]`
  route needs the same canonical + structured-data treatment FrontierFounder
  already has.

## What already exists (the methodology reference)

STIGViewer is where the hub-and-spoke methodology was first built — see
`Taskade/Team Plugins/11 - Project Knowledge/methodology-hub-and-spoke-linking-map-2026-06-14.md`.
Already shipped:

- **The hub page** `stigviewer.com/methodology` (`apps/web/app/(public)/methodology/`),
  carrying `TechArticle + FAQPage + Organization` schema. (Built, committed,
  pushed; deploy is Michael's call.)
- **The auto-linker** `apps/web/lib/blog-methodology-link.tsx` — auto-links the
  first mention of "multi-lensatic methodology" / "multi-lensatic" in any post
  body to `/methodology`. This is the reference implementation for
  `auto_linker`.
- **On-site internal links** plan and **OG card** per the linking map.

So STIGViewer's *first* pillar (the multi-lensatic methodology) is real and
mostly wired on the site side; what's register-only is the **blog post → CSV**
landing and the per-post structured data. New pillars on STIGViewer follow the
same shape as `/methodology`.

## Phase C wiring checklist

- CSV-row adapter for `apps/web/blog-posts/stigviewer-blog-posts.csv`.
- `generateMetadata` (canonical, OG) + JSON-LD on the blog `[slug]` route.
- A shared pillar-route template (or reuse the `/methodology` pattern) for new hubs.
- Point the linking map at `apps/web/blog-posts/_clusters/` (confirm location with Michael).
