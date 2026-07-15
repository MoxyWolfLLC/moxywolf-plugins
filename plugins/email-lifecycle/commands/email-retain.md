---
description: Best practices, tooling, benchmark, recommendations, and a drafted sequence for the RETAIN/EXPAND email stage (post-upgrade, dunning, win-back, expansion). Usage: /email-retain [product]
---

Run the `email-lifecycle` skill scoped to **stage = retain** (welcome-to-paid → retention → expansion, plus dunning and win-back).

Enroll triggers: `upgraded` (welcome-to-paid), `usage_milestone`, `renewal_upcoming`, `payment_failed` (dunning recovery), `churn_risk` (save offer). KPI: net revenue retention, dunning recovery rate. Authoring skills: `growth-engineer-skills:churn-prevention`, `:revops`. Don't upsell the newly-paid until they've felt value (gate expansion on `usage_milestone`).

Produce all five: best practices → tooling (installed + catalog adoption candidates) → benchmark of the named product's current setup → prioritized recommendations → an auto-drafted retention/expansion sequence. If the user named a product, use it; otherwise ask once (or produce product-agnostic guidance and skip the benchmark). Follow `skills/email-lifecycle/SKILL.md`.
