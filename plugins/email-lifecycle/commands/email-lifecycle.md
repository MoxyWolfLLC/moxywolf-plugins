---
description: Run the WHOLE email lifecycle arc — activation → nurture → convert → retain — end to end: best practices, tooling, benchmark, recommendations, and drafted sequences per stage plus a unified trigger map. Usage: /email-lifecycle [product]
---

Run the `email-lifecycle` skill scoped to **stage = full** — all four stages in order (activation → nurture → convert-to-paid → retain/expand).

For each stage produce the five outputs (best practices → tooling → benchmark → recommendations → drafted sequence), then add a cross-stage section: one unified **event/trigger map** (the shared event spine), the **measurement layer** (email_sent + Resend webhooks → PostHog, per-stage funnels, MRR attribution), and the **body-store / ownership** rules — deduped so shared recommendations aren't repeated four times.

Write one combined document to the product's `12 – MARCOM/` and deliver it. If the user named a product, use it; otherwise ask once (or produce a product-agnostic reference and skip the benchmark). Follow `skills/email-lifecycle/SKILL.md`.
