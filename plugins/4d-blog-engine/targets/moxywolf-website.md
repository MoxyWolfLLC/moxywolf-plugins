---
target: moxywolf-website
status: register-only
project: MoxyWolf Website
repo: moxywolf-website
canonical_domain: https://moxywolf.com
post_url_pattern: https://moxywolf.com/blog/<slug>
content_dir: TBD
hero_dir: TBD
media_dir: TBD
render_contract: unknown
frontmatter_required: [title, date]
entity_author_id: https://moxywolf.com/people/dorian-cougias#author
entity_publisher_id: https://moxywolf.com#publisher
publisher_name: MoxyWolf LLC
hero_style: moxywolf-brand
pillar_route_pattern: https://moxywolf.com/<pillar-slug>
pillar_schema: [Article, FAQPage, Organization]
linking_map_dir: TBD
auto_linker: none
---

# Target — MoxyWolf Website

Register-only. The target is selectable now; its concrete contract is unconfirmed.

## Confirm before wiring

The `moxywolf-website` repo is under `GitHub/`. Before this target can publish,
confirm by reading that repo:

- **Content model + content_dir** — is the blog markdown, MDX, Directus, or
  CMS-backed? Where do post files / records live?
- **post_url_pattern** — `moxywolf.com/blog/<slug>`? Confirm the live route.
- **render_contract** — how does the site emit per-post metadata + JSON-LD? Does a
  blog `[slug]` route with `generateMetadata` exist?
- **hero_dir / media_dir** — asset locations.
- **pillar_route_pattern + linking_map_dir** — where hubs live and where linking
  maps get committed.

Note the entity-id overlap: `moxywolf.com` is also the host of the shared
author/publisher `@id`s used by every target. That's fine — the entity ids are
identifiers, not this site's page URLs — but keep the page `@id`
(`mainEntityOfPage`) on this target's own `post_url_pattern`, distinct from the
entity `@id`s.

Until confirmed, the engine will draft + format the post and write the linking
map, then stop and print this checklist rather than guess the contract.
