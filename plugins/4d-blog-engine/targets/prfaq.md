---
target: prfaq
status: register-only
project: PRFAQ
repo: prfaq
canonical_domain: TBD
post_url_pattern: TBD
content_dir: TBD
hero_dir: TBD
media_dir: TBD
render_contract: unknown
frontmatter_required: [title, date]
entity_author_id: https://moxywolf.com/people/dorian-cougias#author
entity_publisher_id: https://moxywolf.com#publisher
publisher_name: MoxyWolf LLC
hero_style: moxywolf-brand
pillar_route_pattern: TBD
pillar_schema: [Article, FAQPage, Organization]
linking_map_dir: TBD
auto_linker: "@moxywolf/hub-links/rehype"         # rehypeHubLinks wired in src/pages/BlogPost.tsx
hub_links_site_slug: prfaq                        # the { site } arg passed to the adapter
---

# Target — PRFAQ

Register-only, and the least specified of the four. Dorian named `prfaq` as a
target; the repo `prfaq` is under `GitHub/` (siblings `prasmvp`, `oldPRasMVP`
exist — confirm which is the live blog property).

## Confirm before wiring

- **Canonical domain + post_url_pattern** — what domain does prfaq publish to?
  Dorian to confirm; this is the one field the descriptor can't infer.
- **Which repo** — `prfaq` vs `prasmvp` vs `oldPRasMVP`.
- **Content model + render_contract** — markdown / MDX / CMS? Per-post metadata +
  JSON-LD route?
- **content_dir / hero_dir / media_dir / linking_map_dir / pillar_route_pattern**.

Until the domain and content model are confirmed, the engine drafts + formats the
post and writes the linking map, then stops and prints this checklist rather than
emit a wrong canonical or guess the contract. (A wrong canonical is an SEO
liability, so this target intentionally refuses to publish on guesses.)
