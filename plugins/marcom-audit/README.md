# marcom-audit

Find the best practices for any MARCOM target — a project, idea, channel, campaign, or funnel stage — and see where MoxyWolf is falling short of them. Built on the premise that *we're probably doing it wrong*, so it consults the full toolbox before we commit to a new direction.

## Command

`/marcom-best-practices [target]`

Examples: `/marcom-best-practices our onboarding email sequence for STIGViewer`, `/marcom-best-practices the OpenControls launch`, `/marcom-best-practices LinkedIn thought-leadership`.

## What it does

1. **Classifies** the target into 13 MARCOM domains. Lifecycle email/outreach is expanded into its stages — onboarding/activation → nurturing → upgrade/expansion → retention/win-back, plus cold outbound — never collapsed into one "email" bucket.
2. **Sweeps three tiers:**
   - **Tier 1 — our toolbox.** A curated domain→skill map of everything we have installed across marketplaces (searchfit-seo, growth-engineer-skills, marketing, moxywolf-skills, linkedin-growth, saas-pricing-engine, 4d-blog-engine, research-pipeline, …), plus the live data MCPs (Ahrefs, PostHog, GA4, Postiz, Apollo, CRM).
   - **Tier 2 — capabilities we don't have.** Queries the Workforce Automation Supabase catalog (`lmhfgsaznbwnnfldpxgc`) — ~580K catalogued Claude skills/plugins/MCPs — for high-signal tools that fit the target and that we haven't installed. Uses the catalog's `installed` source for a real have/don't-have diff, and ranks curated sources (e.g. the Corey Haines 47-skill marketing pack) then by ecosystem prevalence.
   - **Tier 3 — the outside world.** Heavy external research (Perplexity, Firecrawl, Ahrefs, research-pipeline) for current best practices, target metrics, and competitor examples.
3. **Benchmarks** our current practice against all three, using live analytics where available — grading honestly, not on a curve.
4. **Delivers** a prioritized best-practices brief to the target's `12 – MARCOM/` folder: best practices that matter, where we stand, gaps (most costly first), recommendations, adoption candidates, and a "run these next" plan.
5. **Auto-runs** the top applicable installed skills to produce starter deliverables, with human gates on anything that sends, posts, or pushes.

## Requirements

- **Supabase MCP** with access to the `workforce-automation` project (`lmhfgsaznbwnnfldpxgc`) for Tier 2. Without it, Tier 2 degrades to embedded knowledge + Tier-3 research and the brief says so.
- The MARCOM skills referenced in Tier 1 are invoked by `plugin:skill` name; ones not installed in the session surface as adoption candidates rather than erroring.

## Notes

- The catalog is a living index (daily walk + nightly discovery), so Tier 2 is queried live, never cached into the skill.
- No wall-clock time estimates; MoxyWolf is a small team; never fabricate names or numbers.
