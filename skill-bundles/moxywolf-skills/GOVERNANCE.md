# moxywolf-skills — Governance & Risk Tiers

This bundle is held to the MoxyWolf conformance standard defined in
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md),
which derives from the MoxyWolf AI Governance Manifesto. Every skill in the fleet is
judged against **the five tests**:

1. **Gate sized to stakes** — a human checkpoint exists before any high-stakes / irreversible action (sending, posting, publishing, moving money, deleting, writing to customer systems, e-signature).
2. **A named human signs** — high-tier output requires one *named* human to approve, and the approval is recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations; unverifiable claims are flagged, not shipped.
4. **Anti-rubber-stamp** — the skill refuses to ship below a defined threshold, and the oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome regardless of how much was automated.

**Risk tiers:** `read-only` (reads/reports only) · `generate` (produces local artifacts/drafts that don't auto-ship) · `side-effectful-gated` (can send/write only behind a confirm checkpoint) · `high-stakes` (money, e-signature, public broadcast, customer-reaching, deletion).

This bundle's risk surface is low: every skill produces local artifacts (files, drafts, code, designs, reports). **No skill in this bundle auto-sends, auto-posts, auto-publishes, or moves money.** Outreach and comment skills draft only — a named human reviews and sends. Content-ecosystem skills carry a provenance gate routing claims through the research-pipeline citation-verifier before anything is published.

## Per-skill risk tiers

| Skill | risk_tier | gate / note |
|---|---|---|
| api-documentation-writer | generate | Produces docs/specs locally; no side effects. |
| artifacts-builder | generate | Builds local HTML/React artifacts; no auto-deploy. |
| birds-of-a-feather-outreach | generate | Drafts outreach copy only — human-sends-it; nothing auto-sent or auto-posted. |
| blog-content-ecosystem | generate | Content generator — provenance gate: route every stat/claim through citation verification before publishing. |
| brand-guidelines | generate | Applies brand styling to artifacts; no side effects. |
| canvas-design | generate | Produces .png/.pdf visual art locally; no side effects. |
| code-review-pro | read-only | Reviews/audits code and reports; no writes. |
| color-palette-extractor | read-only | Extracts/derives palettes from inputs; reports only. |
| daily-ops | read-only | Redirect stub — moved to standalone `daily-ops` plugin; does not execute. |
| database-schema-designer | generate | Designs schemas/migrations as local artifacts; does not apply to any DB. |
| dev-create-orchestrator | generate | Orchestrates generation skills; produces local code/artifacts only. |
| dev-review-orchestrator | read-only | Orchestrates review/analysis skills; reports only, no writes. |
| linkedin-analytics | read-only | Scrapes LinkedIn analytics pages and reports; never modifies LinkedIn content. |
| linkedin-thought-leadership | generate | Drafts comments into an artifact only — human-sends-it; nothing auto-posted. |
| market-awareness-analyzer | generate | Web/research analysis producing a report; claim-bearing output should carry source + date. |
| mcp-builder | generate | Generates MCP server scaffolding/code locally; no side effects. |
| moxywolf | generate | Applies MoxyWolf brand voice/styling to content; no side effects. |
| podcast-booking-ladder | generate | Drafts pitch copy and booking plan only — human-sends-it; nothing auto-sent. |
| refinement-prompts | read-only | Diagnostic prompts for refining drafts; advisory, no writes. |
| screenshot-to-code | generate | Converts screenshots to local code; no auto-deploy. |
| skill-creator | generate | Creates/edits skill files as local artifacts; no side effects. |
| sorkin-dob-weekly-blog | generate | Content generator — provenance gate: route every stat/claim through citation verification before publishing. |
| stigviewer-content-ecosystem | generate | Content generator — provenance gate: route every stat/claim through citation verification before publishing. |
| technical-writer | generate | Produces technical documentation locally; no side effects. |
| theme-factory | generate | Applies themes to artifacts; no side effects. |
| voice-injection | generate | Rewrites content into Dorian's voice; produces local drafts only. |

**Total: 26 skills.**
