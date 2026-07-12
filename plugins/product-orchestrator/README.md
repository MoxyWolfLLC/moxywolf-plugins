# Product Orchestrator Plugin

**Version:** 0.4.0
**Author:** MoxyWolf LLC
**Requires:** Council plugin (v0.7.0+) and the team-shared OpenRouter API key file in the MoxyWolf Vault (see Council's README — no shell-rc edits required)

## Overview

Product decisions kill solo founders quietly. Not the obvious ones — the scope creep that felt reasonable, the architecture choice that seemed fine at month 1 but costs a rewrite at month 6, the positioning that makes sense to the builder but confuses every buyer.

The Product Orchestrator wraps the Council deliberation engine with product-specific intelligence. It triggers structured multi-model friction at the three decision points where products actually fail: **scope**, **architecture**, and **go-to-market positioning**. Then it routes the synthesized decisions to downstream execution skills and persists everything to the Obsidian vault so you never lose the reasoning.

This is not a project management tool. It's a decision quality tool.

## Components

### Commands

| Command | Description |
|---------|-------------|
| `/project-charter` | Create or update a project's `CHARTER.md` — durable principles and boundaries the Council consults before scope and PRD decisions |
| `/product-prd` | Generate a Product Requirements Document through guided interview |
| `/product-clarify` | Scan a PRD for ambiguity/coverage gaps and resolve them with ≤5 targeted questions encoded back into the PRD (before architecture) |
| `/product-scope` | Deliberate on scope decisions (what to build, defer, or cut) |
| `/product-arch` | Deliberate on architecture choices (tech stack, infrastructure, patterns) |
| `/product-gtm` | Deliberate on go-to-market positioning (messaging, pricing, distribution) |
| `/product-analyze` | Read-only cross-artifact consistency check (PRD ↔ architecture ↔ task plan ↔ CHARTER) before execution — DR-004's `/product-analyze` |
| `/product-sprint` | Full sprint orchestration: PRD → clarify → deliberation → task plan → analyze → execute → review |

### Skill

**product-orchestrator** — Core orchestration logic. Classifies product decisions, formats role prompts, invokes Council deliberation, parses outputs, routes to downstream skills, and writes decision records.

### Reference Files

| File | Purpose |
|------|---------|
| `charter-template.md` | Project charter format + interview protocol; how the Council consults the charter; progressive opt-in rigor rules |
| `prd-template.md` | PRD format, interview protocol (14 inputs), section inclusion rules, status lifecycle |
| `scope-templates.md` | Four role prompts for scope deliberation (User Advocate, Business Strategist, Ship-It Pragmatist, Long-Game Architect) |
| `architecture-templates.md` | Four role prompts for architecture deliberation (Scalability Realist, Security & Compliance Advocate, DX Champion, Migration Strategist) |
| `gtm-templates.md` | Four role prompts for GTM deliberation (Customer Voice, Market Analyst, Revenue Architect, Contrarian Advisor) |
| `clarify-protocol.md` | Ambiguity taxonomy, question-selection heuristic (Impact × Uncertainty, ≤5), and encode-back rules for `/product-clarify` |
| `analyze-protocol.md` | Detection passes, severity rubric, and report format for `/product-analyze`; PRD↔architecture↔task-plan↔charter artifact mapping |
| `sprint-protocol.md` | Full sprint sequence, deliberation gating rules, execution routing tables |

## Dependencies

This plugin wraps the Council deliberation engine. It does not duplicate Council's mechanics.

**Required:**
- **Council plugin** (v0.7.0+) — provides the deliberation-engine skill that handles multi-model collection, peer review, and synthesis
- **OpenRouter API key** — stored as a team-shared `.env` file in the vault at `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env`. Council's `scripts/openrouter_key.py` auto-discovers it in either the Cowork bash sandbox vault mount or a native macOS Google Drive mount — no shell-rc edits required. See Council's README for the full lookup order.

**Optional:**
- **Obsidian vault** (via Google Drive or local mount) — for persisting decision records
- **Downstream execution skills** — dev-create-orchestrator, growth-engineer-skills, saas-pricing-engine, etc. The orchestrator routes to these but works without them (just produces decisions and task lists instead)

## Usage

### Quick Decisions

```
/product-scope Should we add SSO to v1 or defer it?
/product-arch Monolith or microservices for a team of one?
/product-gtm Who is the first buyer for STIGViewer Pro?
```

### Full Sprint

```
/product-sprint STIGViewer
```

This walks through the complete cycle: PRD check → scope deliberation → architecture deliberation (if needed) → GTM deliberation (if needed) → execution plan → build → review.

### PRD First

```
/product-prd RegGenome compliance automation platform
```

Generates a structured PRD through guided interview, then suggests which deliberation to run next.

## How It Works

1. **Classify** the product question (scope / architecture / GTM / execute-only)
2. **Load** the appropriate role templates from reference files
3. **Format** the Council invocation with product-specific roles and context
4. **Deliberate** via the Council deliberation-engine (multi-model collection → peer review → synthesis)
5. **Extract** structured decisions from the synthesis
6. **Route** to downstream execution skills
7. **Persist** decision records to the vault

The key insight: Council handles the deliberation mechanics (model calls, peer review, synthesis). This plugin handles the product intelligence (which roles argue about what, how to frame the question, where to send the answer).

## Decision Records

Every deliberation produces a decision record:

- **Local:** Presented in conversation for immediate review
- **Vault:** Written to `_Shared Knowledge/Product Decisions/PD-{NNN}-{slug}.md`
- **PRD:** Updated with decisions and status progression (Draft → Scoped → Architected → Positioned → Ready)

## Deliberation Roles by Decision Type

### Scope Decisions
| Role | Argues For |
|------|-----------|
| User Advocate | Features users actually need (not what builders want to build) |
| Business Strategist | Features that drive revenue and competitive positioning |
| Ship-It Pragmatist | Smallest possible scope that tests the thesis |
| Long-Game Architect | Scope decisions that prevent expensive rework later |

### Architecture Decisions
| Role | Argues For |
|------|-----------|
| Scalability Realist | Simplest architecture for actual current scale |
| Security & Compliance | Security built in from day one, not bolted on |
| DX Champion | Developer velocity and maintainability for actual team size |
| Migration Strategist | Preserving optionality and affordable future changes |

### GTM Decisions
| Role | Argues For |
|------|-----------|
| Customer Voice | Buyer's actual decision process, not builder's assumptions |
| Market Analyst | Category strategy, competitive dynamics, timing |
| Revenue Architect | Pricing, unit economics, path to sustainable revenue |
| Contrarian Advisor | The strongest case against the positioning (steel-man opposition) |

## Version History

- **0.5.0** — Add `/product-clarify` and `/product-analyze`, concept-ported from [spec-kit](https://github.com/github/spec-kit) (MIT) — the same origin as the charter/constitution primitive. `/product-clarify` scans a PRD against an ambiguity taxonomy and resolves gaps with ≤5 Impact×Uncertainty-ranked questions encoded back into the PRD, before architecture. `/product-analyze` is DR-004's anticipated read-only cross-artifact consistency check (PRD ↔ architecture ↔ task plan ↔ CHARTER): duplication, ambiguity, underspecification, charter-alignment (auto-CRITICAL), coverage gaps, and inconsistency, as a severity-ranked report + coverage map — it reports, never edits or gates. Both wired into the sprint protocol (clarify after PRD, analyze before execute). Ideas only; no spec-kit code vendored. The paired implementation-time check (`/gstack-verify`, built code vs spec) remains a gstack-execution follow-on.
- **0.2.0** — Enhanced PRD template. Added User Personas (required, conditional), Non-Functional Requirements, Dependencies & Integrations, Risks & Mitigations, and Verification Approach sections (all optional). New deliberation routing rules for NFR/dependency-driven architecture questions and unmitigated risk-driven scope reconsideration. Section inclusion rules keep lean PRDs lean.
- **0.1.0** — Initial release. Scope, architecture, and GTM deliberation templates. PRD generation. Sprint orchestration. Vault persistence via memory-system.

## Composio fallback

For apps with no native MCP connector, this plugin can reach them through Composio's Tool Router when the Composio connector is installed. See the `composio` plugin.
