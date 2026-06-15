---
description: Add, edit, list, or remove a cross-property pillar term in the shared @moxywolf/hub-links map — the single file that controls what auto-links across every MoxyWolf blog. Rebuilds dist; the writer commits/pushes/tags.
argument-hint: '[list | add "<term>" | edit "<term>" | remove "<term>"]'
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:blog-term — manage shared auto-link terms

A **term** is a phrase whose first mention in *any* blog post auto-links to a
canonical page, across every MoxyWolf property. All terms live in **one**
cross-property file — the published `@moxywolf/hub-links` package:

`<GitHub root>/hub-links/src/map.ts` → the `HUB_LINKS` array.

Each entry keys a term to its **owning property** and a **path**; the adapters
wired into every site render a relative link on the owner and an absolute
cross-property link everywhere else (see DR-079). This command edits that array
safely, rebuilds `dist`, and tells the writer what to commit. **Never hand-edit
`dist/` — rebuild it.**

Load `references/linking-map-template.md` and the target registry (`targets/*.md`)
first — the target descriptors supply each property's `hub_links_site_slug`
(the `owner` value) and `canonical_domain`.

## Locate the map

Resolve `<GitHub root>` (the mounted GitHub root the other repos live under) and
read `hub-links/src/map.ts`. If it's missing, stop and tell the writer the
`hub-links` repo isn't mounted/cloned. Parse the `SITES` object (valid owners)
and the `HUB_LINKS` array.

## Modes

### `list` (default when no mode given)

Print a table from `HUB_LINKS`: term (the human phrase / the `pattern`), `owner`,
`path`, and the resolved full URL (`SITES[owner] + path`). This is the canonical
inventory of what auto-links everywhere.

### `add "<term>"`

1. **Owner** — ask which property owns the destination page (`AskUserQuestion`,
   options = the `SITES` slugs / registered targets). This is the `owner` value;
   it's also each target's `hub_links_site_slug`.
2. **Page** — ask the destination. Accept a path (`/methodology`) or a full URL
   (derive the path; confirm the host matches the owner's `canonical_domain`).
   The page should be a **real canonical page** — warn if it's a blog post rather
   than a pillar hub (a post will self-link the term on its own page).
3. **Pattern** — derive a tolerant, **case-insensitive, non-global** regex from
   the term: escape regex metacharacters, allow obvious spacing/hyphen variants
   (e.g. `multi-?lensatic`, `4-?d`), and require enough surrounding context to
   avoid false positives (e.g. require `framework` after `4D`). **Show the writer
   the generated regex and confirm it** before writing.
4. **De-dupe** — scan existing `HUB_LINKS`; warn if the new pattern overlaps an
   existing term, and confirm intended ordering (entries are tested in array
   order — put the most specific first).
5. **Insert** the entry just before the `// future pillar terms` comment:
   ```ts
   {
     pattern: /<derived>/i,
     owner: '<owner-slug>',
     path: '<path>',
   },
   ```
6. **Rebuild** — in the `hub-links` repo: `npm install` if `node_modules` is
   absent, then `npm run build`. Confirm `npm test` stays green.
7. **Report** — the term is live only after the package is committed, pushed, and
   tagged, and each site rebuilds (the plugin-sync bumps the dep). Print the
   commit one-liner and remind the writer to push (per the repo's commit norm).

### `edit "<term>"`

Find the entry (match the writer's phrase against the patterns), apply the
requested change (owner, path, or a tighter/looser pattern — re-confirm the
regex), rebuild, and report. Use this to repoint a term once its page moves
(e.g. a post-URL term promoted to a real pillar page).

### `remove "<term>"`

Delete the entry, rebuild, and note that sites stop auto-linking it on their next
build. The per-pillar linking map (if any) is left alone — removing a term does
not delete a pillar.

## Rules to enforce

- **One source of truth.** This file is it. Don't add per-site copies; don't
  hand-link first mentions in post bodies (the build-time adapter does that).
- **Owner = the property that hosts the page.** The link is relative on the
  owner, absolute everywhere else — that's automatic from `owner`.
- **Patterns:** case-insensitive, non-global, specific enough to avoid stray
  matches, most-specific first in the array.
- **Real pages over posts.** Prefer pointing a term at a canonical pillar page;
  flag when it points at a post (self-link on that post).

## What this command does NOT do

- Does not build the hub *page* (site-code).
- Does not create a pillar or its per-pillar linking map (use `/blog-pillar` —
  which calls this same registration as one of its steps).
- Does not commit, push, or tag — the writer commits/pushes the `hub-links`
  change and tags a release (per the repo's commit norm), after which the sites
  pick the term up on their next build.
- Does not draft a post (use `/blog-pipeline`).
