# saas-frontend-designer — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

This plugin generates and audits UI code locally. It does not deploy, push, or publish.

| Skill / command | risk_tier | note |
|---|---|---|
| `design` (command) | generate | Generates a SaaS UI page or component from a description (local code). |
| `design-tokens` (command) | generate | Generates/updates design tokens and Tailwind config (local files). |
| `polish` (command) | generate | Runs the full UI polish pipeline on existing code (local edits). |
| `a11y-audit` (command) | read-only | Runs an accessibility audit on UI code and reports findings; analysis only. |
| `frontend-design` (skill) | generate | Core UI-generation protocol; produces local code/components. |
| `baseline-ui` (skill) | generate | Baseline UI scaffolding/components (local). |
| `design-system` (skill) | generate | Design-system generation (tokens, components) — local artifacts. |
| `figma-to-code` (skill) | generate | Converts Figma designs into local UI code; reads design source, writes code locally. |
| `accessibility-audit` (skill) | read-only | A11y audit/reporting protocol; analysis only, no writes. |
| `performance-optimization` (skill) | generate | Produces local code edits / optimization recommendations; no deploy. |
