---
description: Create or edit a pillar (hub) and its linking map. Pillars are the hubs of the hub-and-spoke model — every blog post is a spoke on exactly one pillar.
argument-hint: [target] [new "<Pillar title>" | edit <pillar-slug> | list]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:blog-pillar — manage pillars + linking maps

A **pillar** is a real canonical hub page; its **linking map** is the versioned
manifest of the pillar and every spoke that points at it. This command creates or
edits those directly, outside the post pipeline. The post pipeline (STEP 1.5)
also creates/attaches pillars inline — use this command when you want to set up or
revise a pillar on its own.

Load `skills/4d-blog-engine/SKILL.md` (STEP 0, STEP 1, STEP 1.5) and
`references/linking-map-template.md` first.

## Resolve the target

If `[target]` is given, load `targets/<target>.md`. Otherwise ask which target via
`AskUserQuestion`, listing the registered targets from `targets/*.md`. The target
descriptor supplies `linking_map_dir`, `pillar_route_pattern`, `pillar_schema`,
and `auto_linker`.

## Modes

### `list` (default when no mode given)

Glob the target's `linking_map_dir` for `*.md`, read each one's frontmatter, and
print a table: pillar title, slug, hub URL, hub_status, spoke count, updated date.
This is the same list STEP 1.5 shows for "existing pillar."

### `new "<Pillar title>"`

1. Derive `pillar_slug` (kebab-case the title).
2. Set `hub_url` from the target's `pillar_route_pattern` (substitute the slug).
3. Ask for the **hub term** — the key phrase whose first mention in any spoke
   auto-links to the hub (e.g. "AI fluency", "multi-lensatic methodology"). This
   drives the spoke→hub auto-link rule.
3.5. Ask for the **why** — the pillar's belief statement, one sentence, "We
   believe …". This is the Golden Circle anchor (Sinek): the cause every spoke
   on this pillar argues for. **Reject and re-ask if** it names a product or
   feature, states a goal ("we believe in helping X do Y"), or nobody could
   reasonably disagree with it. If the property has a brand belief file
   (`MoxyWolf Vault/_Shared Knowledge/Brand and Voice/belief-<property>.md`),
   read it first and propose a derivation the writer can accept or refine.
   Record it in the linking map's `why:` frontmatter field.
4. Copy `references/linking-map-template.md` into
   `<repo>/<linking_map_dir>/<pillar_slug>.md` and fill the frontmatter +
   "The why" + "The hub" sections. Set `hub_status: planned`, `hub_owner` (ask).
5. **Register the hub term in the shared map** — this is what actually makes the
   link fire, across every property. Add a `HubLink` entry to
   `GitHub/hub-links/src/map.ts`:
   `{ pattern: /<term>/i, owner: '<target hub_links_site_slug>', path: '<pillar path>' }`
   — derive a tolerant, case-insensitive `pattern` from the hub term, and `path`
   is the hub page's path on its owner. Then flag that `@moxywolf/hub-links` must
   be rebuilt (`npm run build`), committed, pushed, and tagged, after which each
   site picks the term up on its next build (the plugin-sync bumps the dep). The
   term is **inert until this entry exists**. Never hand-edit `dist/` — rebuild it.
6. Report the hub route that still needs building if the target has no pillar
   route yet (e.g. FrontierFounder), and whether the target's `auto_linker` is
   wired.

Do **not** scaffold the hub *page* itself here — that's site-code (PRD Phase C).
This command owns the linking map; the hub page is built per target.

### `edit <pillar-slug>`

Open `<linking_map_dir>/<pillar-slug>.md` and apply the requested change: add a
spoke to the inventory, add an on-site internal link, promote a spoke into the
hub's "Related reading," update `hub_status`, revise anchor-text guidance, or
set/revise the `why:` belief statement (apply the step-3.5 validity rules; older
maps predating the field get it added on first edit).
Bump the frontmatter `updated` date. Keep the section order intact — the engine
parses by heading.

## Methodology rules to enforce (from the reference exemplar)

- **Link to the URL, never a screenshot.**
- **Vary anchor text** across spokes (exact / partial / natural).
- **Hold the hub's "Related reading"** until real spokes exist — don't link down
  to generic posts.
- The pillar is a **real page**, not a tag or footer.
- **Link at build time, not authoring time.** Every target's `auto_linker` is the
  `@moxywolf/hub-links` adapter, which links the first mention automatically at
  build. So a spoke body only needs to *mention* the hub term — do **not**
  hand-insert the first-mention link (that double-links); add one explicit
  "Read the full X →" CTA near the close instead. (DR-079.)

## What this command does NOT do

- Does not draft a post (use `/blog-pipeline` or `/blog-delegate`).
- Does not build the hub *page* route (site-code, Phase C).
- Does not commit or release — it edits the per-pillar linking map and the shared
  `hub-links/src/map.ts`, but the writer commits/pushes both (per the repo's
  commit norm) and rebuilds + tags `@moxywolf/hub-links` so the sites pick up the
  new term.
