---
read_when: "STEP 1.5 creates a NEW pillar, or /blog-pillar creates/edits one. Copy this template into the target's linking_map_dir as <pillar-slug>.md and fill it."
status: template
based_on: "Taskade/Team Plugins/11 - Project Knowledge/methodology-hub-and-spoke-linking-map-2026-06-14.md (the Multi-Lensatic Methodology linking map — the reference exemplar)."
---

# Linking map (cluster manifest) — template

A **linking map** is the versioned source of truth for one pillar and its spokes.
One file per pillar, committed in the target's `linking_map_dir` (e.g.
`content/blog/_clusters/<pillar-slug>.md`). The engine reads it to list existing
pillars (STEP 1.5 "existing pillar"), and updates it in the same pass whenever a
spoke is published. Copy everything below the line and fill the `<…>` slots.

Modeled field-for-field on the reference exemplar. Keep the section order — the
engine parses by heading.

---

```yaml
---
pillar_slug: <kebab-slug>
pillar_title: "<Pillar title>"
why: "We believe <one-sentence belief this pillar exists to argue — a cause, not a capability>"
target: <target-key>                  # e.g. frontier-founder
hub_url: <canonical hub page URL>     # e.g. https://thefrontierfounder.com/ai-fluency-for-founders
hub_term: "<key term that auto-links to the hub>"   # e.g. "AI fluency" — MUST be registered in hub-links/src/map.ts (via /blog-term or /blog-pillar) or it never links
hub_schema: [Article, FAQPage, Organization]
hub_status: planned | built | deployed
hub_owner: <who owns the hub build/deploy>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---
```

## The why

`<why>` is the pillar's belief statement — the cause every spoke on this pillar is
evidence for (Sinek's Golden Circle: WHY → HOW → WHAT, communicated inside-out).
Rules for a valid `why`:

- **A cause, not a capability.** "We believe compliance evidence should be
  machine-verifiable" — not "we believe our platform is great."
- **Arguable.** Someone reasonable could disagree. A belief nobody disputes
  differentiates nothing.
- **Survives product deletion.** Delete every product name from the sentence and
  it still means something.

If the property has a brand belief file
(`MoxyWolf Vault/_Shared Knowledge/Brand and Voice/belief-<property>.md`), the
pillar's `why` should derive from it — one brand WHY, many pillar expressions.
Spokes inherit the `why`: drafts open from the belief (or its villain), and
Phase 4's Release Owner runs the Celery Test against it.

## The hub

`<hub_url>` is the pillar page — the single canonical URL for `<pillar_title>`.
Everything points at it; it points back at the highest-value surfaces. The hub is
the definitive, citable explainer and carries `<hub_schema>` so AI engines can
lift a clean answer. Built at `<repo path of the hub route>`. Status:
`<hub_status>` — owner `<hub_owner>`.

**Rule of the model: link to the URL, never a screenshot.** Visual companions
(infographics, one-sheets) are assets; the page is what ranks and gets cited.

## Spoke inventory

| Spoke | Where it lives | Direction | Anchor / treatment | Action |
|---|---|---|---|---|
| **<spoke title>** | `<path or route>` | spoke → hub | First mention auto-links; add one explicit "<CTA>" near the close | <open action / Done> |
| ... | ... | hub → spoke / companion | ... | ... |

## On-site internal links

Add a contextual link to the hub from existing pages that already rank. Vary the
anchor text.

| Page | Suggested placement | Anchor text (vary it) |
|---|---|---|
| `<route>` | <where> | "<anchor>" |

## Hub → spoke "Related reading"

The hub carries a short "Related reading" block linking down to the best spokes.
Hold until real spokes publish — linking down to generic posts dilutes relevance.
Wire it when these exist:

- <best spoke 1>
- <best spoke 2>

## Anchor-text guidance

Vary anchors across spokes — mix exact ("<exact term>"), partial ("<partial>"),
and natural ("read the full <thing>"). Identical repeated anchors read as spam to
search and AI engines.

## Current state (<YYYY-MM-DD>)

- Hub page: <built/committed/deployed?>
- Auto-linker: `@moxywolf/hub-links/<adapter>` wired? + is the `hub_term` registered in `hub-links/src/map.ts`?
- Spokes live: <count + which>
- Open actions: <from the inventory>
