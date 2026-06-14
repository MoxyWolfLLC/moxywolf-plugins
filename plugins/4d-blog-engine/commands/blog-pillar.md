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
4. Copy `references/linking-map-template.md` into
   `<repo>/<linking_map_dir>/<pillar_slug>.md` and fill the frontmatter +
   "The hub" section. Set `hub_status: planned`, `hub_owner` (ask).
5. Report the hub route that still needs building if the target has no pillar
   route yet (e.g. FrontierFounder), and whether the target's `auto_linker` is
   present.

Do **not** scaffold the hub *page* itself here — that's site-code (PRD Phase C).
This command owns the linking map; the hub page is built per target.

### `edit <pillar-slug>`

Open `<linking_map_dir>/<pillar-slug>.md` and apply the requested change: add a
spoke to the inventory, add an on-site internal link, promote a spoke into the
hub's "Related reading," update `hub_status`, or revise anchor-text guidance.
Bump the frontmatter `updated` date. Keep the section order intact — the engine
parses by heading.

## Methodology rules to enforce (from the reference exemplar)

- **Link to the URL, never a screenshot.**
- **Vary anchor text** across spokes (exact / partial / natural).
- **Hold the hub's "Related reading"** until real spokes exist — don't link down
  to generic posts.
- The pillar is a **real page**, not a tag or footer.

## What this command does NOT do

- Does not draft a post (use `/blog-pipeline` or `/blog-delegate`).
- Does not build the hub *page* route (site-code, Phase C).
- Does not commit — the writer commits/pushes (per the repo's commit norm).
