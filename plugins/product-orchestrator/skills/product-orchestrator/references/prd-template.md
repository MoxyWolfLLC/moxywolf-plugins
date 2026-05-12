# PRD Template

Generate a Product Requirements Document before deliberation begins. The PRD is the shared artifact that all Council models argue against. Without it, deliberation devolves into abstract debate. With it, models have concrete constraints to push on.

## When to Generate

- User says "write a PRD", "product requirements", "spec this out", "define the product"
- Before any `/product-scope` deliberation if no PRD exists yet
- When `/product-sprint` starts and the product hasn't been defined
- When the user describes a product idea but hasn't structured their thinking

## PRD Interview

Before writing the PRD, extract these inputs. Ask only what the user hasn't already provided. Use AskUserQuestion for multiple-choice items. Free-text for the rest.

### Required Inputs

1. **Problem Statement** -- What pain exists today? Who feels it? How do they cope without your product?
2. **Target User** -- Be specific. Not "developers" but "solo SaaS founders shipping their first product with no dedicated ops team." One sentence, maximum specificity.
3. **Proposed Solution** -- What are you building? One paragraph. If you can't describe it in one paragraph, you haven't scoped it yet.
4. **Success Criteria** -- How do you know this worked? 2-3 measurable outcomes. Revenue, usage, retention, time-saved. Not "users love it."
5. **Non-Goals** -- What are you explicitly NOT building? This is the most important section. Forces scope discipline before deliberation starts.
6. **User Personas** -- If the product serves more than one role, who are they? For each: role, what they need from the product, and what frustrates them today. Skip this if there's genuinely one persona -- the Target User sentence covers it.

### Optional Inputs (ask if the user has opinions, skip if not)

7. **Competitive Landscape** -- Who else solves this? How? What's your angle?
8. **Technical Constraints** -- Existing stack, infrastructure limits, API dependencies, compliance requirements.
9. **Timeline** -- When does this need to ship? Hard deadline or aspirational?
10. **Revenue Model** -- How does this make money? Free, freemium, paid, usage-based?
11. **Non-Functional Requirements** -- Any performance, uptime, or scalability expectations? Response time targets, concurrent user estimates, compliance mandates? For early-stage products this is often "not yet" -- that's a valid answer. For infrastructure-heavy products (multi-service platforms, API products, anything with SLAs), this matters before architecture deliberation.
12. **Known Risks** -- What could kill this? Technical risks, market risks, dependency risks, regulatory risks. Different from Open Questions -- risks are known threats with uncertain impact, questions are genuine unknowns. If the user draws a blank, skip it. But if they say "well, the API we depend on has been flaky" or "our competitor ships in 6 weeks" -- that's a risk.
13. **Dependencies & Integrations** -- What external systems, services, APIs, or internal components does this depend on? What depends on this? For a standalone product this may be empty. For a feature in an existing platform, this is critical -- it surfaces the things that have to exist before this can ship.
14. **Verification Approach** -- How will you know this actually works in production? Not test cases (that's sprint-level), but the verification strategy: what types of testing matter (functional, performance, security, compliance), and who signs off. Lightweight is fine. "We'll run integration tests and do a manual walkthrough" is a valid answer.

## PRD Document Format

Generate as a markdown file saved to the workspace. This becomes the anchor document that all subsequent deliberations reference.

```markdown
# PRD: {Product/Feature Name}

**Author:** {user name}
**Date:** {current date}
**Status:** Draft -- pending deliberation

---

## Problem

{Problem statement. 2-3 sentences max. State the pain, who feels it, and what they do today without your product.}

## Target User

{One sentence. Maximum specificity. If you wrote "developers" you haven't narrowed enough.}

## User Personas

{Include only if multiple personas exist. If the product serves a single user type, omit this section -- the Target User sentence covers it.}

| Persona | Role | Needs from This Product | Current Pain Points |
|---------|------|------------------------|---------------------|
| {name} | {role and responsibilities} | {what they need} | {what frustrates them today} |
| {name} | {role and responsibilities} | {what they need} | {what frustrates them today} |

## Proposed Solution

{One paragraph. What you're building and how it addresses the problem. No implementation details -- that's for architecture deliberation.}

## Success Criteria

| Metric | Target | Timeframe |
|--------|--------|-----------|
| {metric 1} | {target} | {when} |
| {metric 2} | {target} | {when} |
| {metric 3} | {target} | {when} |

## Non-Goals

These are explicitly out of scope. If someone suggests adding these, point them here.

- {non-goal 1}
- {non-goal 2}
- {non-goal 3}

## Competitive Landscape

| Competitor | Approach | Our Angle |
|-----------|----------|-----------|
| {name} | {how they solve it} | {why we're different} |

## Constraints

- **Technical:** {stack, infrastructure, compliance}
- **Timeline:** {when this ships}
- **Resources:** {team size, budget}
- **Revenue model:** {how this makes money}

## Non-Functional Requirements

{Include when the product has performance, uptime, or compliance expectations. Omit for early-stage products where these haven't been defined yet.}

- **Performance:** {response time targets, throughput expectations}
- **Availability:** {uptime target, e.g. 99.9%}
- **Scalability:** {concurrent users, data volume expectations}
- **Security & Compliance:** {auth requirements, encryption, regulatory mandates}

## Dependencies & Integrations

{Include when the product depends on or is depended upon by other systems. Omit for fully standalone greenfield products.}

| Dependency | Type | Status | Risk if Unavailable |
|-----------|------|--------|---------------------|
| {system/service/API} | {internal / external / infrastructure} | {exists / in progress / planned} | {what breaks if this isn't ready} |

## Risks & Mitigations

{Include when known risks exist. Omit if genuinely none have been identified -- but revisit after deliberation.}

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {what could go wrong} | {high / medium / low} | {what happens if it does} | {how to reduce or contain it} |

## Verification Approach

{Include when the product needs explicit verification planning. Omit for early-stage explorations where "ship and see" is the honest answer.}

- **Functional:** {how you verify it works as specified}
- **Performance:** {how you verify it meets NFR targets}
- **Security:** {how you verify it meets compliance/security requirements}
- **Sign-off:** {who confirms this is ready for production}

## Open Questions

{Questions that need deliberation. These become inputs to /product-scope, /product-arch, and /product-gtm.}

1. {question}
2. {question}
3. {question}

---

*This PRD is a living document. Updated after each deliberation round.*
```

## After the PRD

Once the PRD is written, present it to the user and suggest the next deliberation:

- If the PRD reveals scope ambiguity --> suggest `/product-scope`
- If technical constraints are undefined --> suggest `/product-arch`
- If target user or positioning is fuzzy --> suggest `/product-gtm`
- If NFRs or dependencies surface architecture questions --> suggest `/product-arch`
- If risks are high-likelihood and unmitigated --> suggest `/product-scope` to reconsider scope
- If the PRD is crisp and the user wants to move --> suggest `/product-sprint`

The PRD's "Open Questions" section is a direct feed into deliberation topics. Each open question is a potential Council session. Unmitigated risks from the Risks table are also candidates for deliberation.

## PRD Updates After Deliberation

After any product deliberation, update the PRD to reflect the decision. Change the status from "Draft" to the appropriate state:

- **Draft** -- initial version, no deliberation yet
- **Scoped** -- scope deliberation complete, non-goals confirmed
- **Architected** -- architecture decisions made, technical approach locked
- **Positioned** -- GTM deliberation complete, target user and messaging confirmed
- **Ready** -- all critical decisions made, ready for sprint execution

Add a "Decision Log" section at the bottom of the PRD linking to each PD record:

```markdown
## Decision Log

| ID | Date | Type | Decision | Confidence |
|----|------|------|----------|------------|
| PD-001 | 2026-03-28 | scope | Ship auth with SSO only, defer custom RBAC | strong |
| PD-002 | 2026-03-28 | arch | Monolith with Supabase, extract services at 1K users | moderate |
```

## Section Inclusion Rules

Not every PRD needs every section. The interview protocol handles this -- if the user has nothing for a section, omit it from the generated document. The template above shows the maximum structure. The minimum viable PRD is:

- Problem
- Target User
- Proposed Solution
- Success Criteria
- Non-Goals
- Open Questions

Everything else is included when the interview surfaces relevant inputs. A lean PRD for a simple feature should stay lean. A PRD for a multi-service platform feature should use the full template. Let the product's complexity dictate the document's weight.
