# Publishing targets

A **target** is a blog property the engine can publish to. One descriptor file per
target lives in this directory. At the start of every post the orchestrator
(SKILL.md STEP 1.5) loads these descriptors, asks the writer **which target** and
**which folder**, then **new pillar or existing pillar** — and everything
downstream (canonical URLs, JSON-LD entities, frontmatter, hero style, the
linking map) is driven by the chosen descriptor.

This is the registry the unified-blog-plugin PRD describes
(`Taskade/Team Plugins/02 – Product Strategy/Research & Discovery/PRD-unified-blog-plugin-hub-spoke-2026-06-14.md`).
The hub-and-spoke methodology every target follows is generalized from
`Taskade/Team Plugins/11 - Project Knowledge/methodology-hub-and-spoke-linking-map-2026-06-14.md`.

## Descriptor schema

Each `targets/<name>.md` carries YAML frontmatter plus prose notes:

```yaml
---
target: frontier-founder              # registry key (kebab-case)
status: wired | register-only         # wired = full end-to-end; register-only = site-rendering deferred
project: The Frontier Founder         # human project name
repo: FrontierFounder                 # folder under the mounted GitHub root
canonical_domain: https://thefrontierfounder.com
post_url_pattern: https://thefrontierfounder.com/blog/<slug>
content_dir: content/blog             # where post markdown lands
hero_dir: public/blog-hero            # where hero images land
media_dir: public/blog-media          # inline media
render_contract: ld-json-body-block   # how the site consumes structured data (see notes)
frontmatter_required: [title, date]   # fields the site/build requires
entity_author_id: https://moxywolf.com/people/dorian-cougias#author
entity_publisher_id: https://moxywolf.com#publisher
publisher_name: MoxyWolf LLC
hero_style: brand-abstract            # named hero-image style (notes carry the prompt)
voice_profile: <blog-project>/<author-slug>-voice.md
# --- hub / pillar conventions ---
pillar_route_pattern: https://thefrontierfounder.com/series/<pillar-slug>   # where hubs live
pillar_schema: [Article, FAQPage, Organization]   # richer than a post's BlogPosting
linking_map_dir: content/blog/_clusters           # where linking maps are committed
auto_linker: none | lib/blog-methodology-link.tsx # site render-pipeline first-mention auto-linker
---
```

## Field notes

- **status** — `wired` means the descriptor fully drives publish (frontmatter,
  JSON-LD, canonical, hero) and the site already renders it. `register-only`
  means the target is selectable but its site-side rendering (per-post metadata,
  JSON-LD, pillar route, auto-linker) is deferred to PRD Phase C; the engine
  still formats the post and writes the linking map, and flags what the site
  needs before the post can go live.
- **render_contract** — the agreed mechanism the target site uses to surface
  structured data. `ld-json-body-block`: a single `<script type="application/ld+json">`
  block at the end of the body that the site extracts (FrontierFounder's
  `src/lib/posts.ts`). `csv-row`: the post is a row in a CSV the site renders
  (STIGViewer) — JSON-LD/meta need site work. `directus` / `mdx` / `unknown` as
  applicable.
- **entity ids** — author `Person` and publisher `Organization` `@id`s are stable
  identifiers, intentionally shared across MoxyWolf properties on `moxywolf.com`
  for entity consolidation. They are NOT page URLs; the page URL is the
  `post_url_pattern` (per-target canonical domain).
- **hub / pillar** — every post is a spoke on exactly one pillar. The pillar is a
  real canonical page at `pillar_route_pattern`, carrying `pillar_schema`. The
  linking map for each pillar lives in `linking_map_dir`. `auto_linker` names the
  site module that auto-links a spoke's first mention of the pillar term to the
  hub, if the site has one.

## How the engine uses a descriptor

1. **STEP 1.5** asks target → loads `targets/<name>.md` → asks folder (default
   `content_dir`) → asks new/existing pillar.
2. **Formatting** (the FrontierFounder adapter logic, generalized) reads the
   descriptor for frontmatter schema, canonical/`post_url_pattern`, entity ids,
   and `render_contract` to emit the right structured data.
3. **Publish** writes/updates the pillar's linking map in `linking_map_dir`, wires
   the spoke→hub link per the methodology rules, and (for `register-only` targets)
   prints the site-side gaps that must close before the post renders correctly.

## Registered targets

| Target | Domain | Status | Render contract |
|---|---|---|---|
| frontier-founder | thefrontierfounder.com | wired | ld-json-body-block |
| stigviewer | stigviewer.com | register-only | csv-row |
| moxywolf-website | moxywolf.com | register-only | confirm on wiring |
| prfaq | (confirm) | register-only | confirm on wiring |
