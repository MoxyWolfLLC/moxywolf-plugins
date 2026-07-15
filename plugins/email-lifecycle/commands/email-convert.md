---
description: Best practices, tooling, benchmark, recommendations, and a drafted sequence for the CONVERT-TO-PAID email stage. Usage: /email-convert [product]
---

Run the `email-lifecycle` skill scoped to **stage = convert** (make the upgrade case; free → paid).

Enroll triggers: product-qualified signals — `feature_gate_hit`, `usage_limit_hit`, `viewed_pricing`, repeat high-value use (define the PQL event). Trigger on behavior, not a calendar. KPI: free→paid conversion. Authoring skills: `growth-engineer-skills:paywall-upgrade-cro`, `:pricing-strategy`, `saas-pricing-engine:tier-builder`.

Produce all five: best practices → tooling (installed + catalog adoption candidates) → benchmark of the named product's current setup → prioritized recommendations → an auto-drafted upgrade sequence. If the user named a product, use it; otherwise ask once (or produce product-agnostic guidance and skip the benchmark). Follow `skills/email-lifecycle/SKILL.md`.
