---
description: Best practices, tooling, benchmark, recommendations, and a drafted sequence for the ONBOARDING/ACTIVATION email stage. Usage: /email-activation [product]
---

Run the `email-lifecycle` skill scoped to **stage = activation** (post-signup onboarding → first value; verify-email + activation nudges).

Enroll triggers: `signup_created`, `email_verified=false`+delay, first-value event absent (e.g. `first_stig_view`). KPI: activation rate. Authoring skills: `growth-engineer-skills:onboarding-cro`, `:signup-flow-cro`, `:email-sequence`.

Produce all five: best practices → tooling (installed + catalog adoption candidates) → benchmark of the named product's current setup → prioritized recommendations → an auto-drafted activation sequence. If the user named a product, use it; otherwise ask once (or produce product-agnostic guidance and skip the benchmark). Follow `skills/email-lifecycle/SKILL.md`.
