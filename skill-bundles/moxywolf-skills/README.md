# moxywolf-skills

A single plugin that bundles all 26 standalone skills the team uses day-to-day, so a new machine can install one thing and pick up the full set.

## What's inside

**MoxyWolf-owned skills**
- `moxywolf` — brand voice and writing/visual style
- `voice-injection` — turn AI drafts into Dorian's voice via structured interview
- `stigviewer-content-ecosystem` — full STIGViewer weekly content system
- `sorkin-dob-weekly-blog` — Sorkin Desire–Obstacle–Battle narrative for STIG+CMMC content
- `blog-content-ecosystem` — turn a blog post into lead magnets, bibliography, LinkedIn posts
- `market-awareness-analyzer` — PR/FAQ → content-strategy via web + Reddit + YouTube + Trends
- `podcast-booking-ladder` — phased podcast outreach from debut to top-tier
- `birds-of-a-feather-outreach` — complementary-author research and outreach
- `linkedin-thought-leadership` — comment drafting for LinkedIn engagement
- `linkedin-analytics` — weekly LinkedIn analytics report
- `daily-ops` — energy-aware standup / triage / review (standalone form)
- `refinement-prompts` — diagnostic prompts for refining drafts

**Anthropic-shipped reference skills** (bundled here so they travel with the marketplace)
- `artifacts-builder`, `canvas-design`, `brand-guidelines`, `theme-factory`
- `code-review-pro`, `database-schema-designer`, `api-documentation-writer`, `technical-writer`
- `mcp-builder`, `skill-creator`
- `dev-create-orchestrator`, `dev-review-orchestrator`
- `screenshot-to-code`, `color-palette-extractor`

## Why bundle them?

Cowork ships some of these by default, but the standalone-skills set on this machine drifts (custom edits, new MoxyWolf-built ones, occasional renames). Bundling everything into one installable plugin means a new computer gets the same set we actually use, not "whatever Cowork ships this week."

If Cowork already ships a skill with the same name, the plugin-namespaced version wins inside agent invocations; you can disable individual entries with `/plugin disable moxywolf-skills`.
