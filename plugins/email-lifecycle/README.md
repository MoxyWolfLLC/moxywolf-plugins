# email-lifecycle

Stage-sharded `/email-*` commands for the product email lifecycle. Invoke the stage you're working on and get its best practices, the tooling to build it, a benchmark of where the product stands, recommendations, and a drafted sequence — the whole thing in one call.

## Commands

| Command | Stage | KPI |
|---|---|---|
| `/email-activation [product]` | Post-signup onboarding → first value (verify + activation nudges) | activation rate |
| `/email-nurture [product]` | Keep free users engaged; deepen usage; education | usage depth / return |
| `/email-convert [product]` | Make the upgrade case; free → paid (PQL-triggered) | free→paid conversion |
| `/email-retain [product]` | Welcome-to-paid → retention → expansion; dunning; win-back | net revenue retention |
| `/email-lifecycle [product]` | The whole arc, all four stages + a unified trigger/measurement map | full-funnel |

## What each command returns

1. **Best practices** for the stage — from our installed authoring skills plus live external research (sourced, current).
2. **Tooling** — which installed skills to use, and adoption candidates queried live from the Workforce Automation catalog (~580K catalogued Claude tools, de-duped against our installed set).
3. **Benchmark** — reads the named product's current email setup and grades it honestly against best practice.
4. **Recommendations** — prioritized, aligned to the MoxyWolf reference runtime (PostHog Workflows + Resend + first-party event capture; **no n8n**; one body store per class).
5. **Drafted sequence** — the actual messages: triggers, delays, exit conditions, subjects, and copy in MoxyWolf voice.

## Requirements

- **Supabase MCP** with access to the `workforce-automation` project (`lmhfgsaznbwnnfldpxgc`) for the adoption-candidate query; without it, tooling degrades to the curated `coreyhaines31/marketingskills` pack + external research.
- The stage authoring skills (`growth-engineer-skills:*`, `moxywolf-skills:voice-injection`, `saas-pricing-engine:*`) are invoked by name where installed; ones absent this session surface as adoption candidates and the sequence is drafted directly.
- Benchmark needs the product's repo/MARCOM folder mounted; without it, produces product-agnostic guidance and skips the benchmark.

## Relationship to marcom-audit

`marcom-audit`'s `/marcom-best-practices` is the general, cross-domain sweep. `email-lifecycle` is the deep, stage-sharded email path — same three-tier method (installed → catalog → external), narrowed to lifecycle email and split into one command per stage.
