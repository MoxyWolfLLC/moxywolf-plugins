# Product Orchestrator Plugin

**Version:** 0.2.0
**Author:** MoxyWolf LLC
**Requires:** Council plugin (v0.6.0+), Rube (OpenRouter connection)

## Overview

Product decisions kill solo founders quietly. Not the obvious ones — the scope creep that felt reasonable, the architecture choice that seemed fine at month 1 but costs a rewrite at month 6, the positioning that makes sense to the builder but confuses every buyer.

The Product Orchestrator wraps the Council deliberation engine with product-specific intelligence. It triggers structured multi-model friction at the three decision points where products actually fail: **scope**, **architecture**, and **go-to-market positioning**. Then it routes the synthesized decisions to downstream execution skills and persists everything to the Obsidian vault so you never lose the reasoning.

This is not a project management tool. It's a decision quality tool.

## Components

### Commands

| Command | Description |
|---------|-------------|
| `/product-prd` | Generate a Product Requirements Document through guided interview |
| `/product-scope` | Deliberate on scope decisions (what to build, defer, or cut) |
| `/product-arch` | Deliberate on architecture choices (tech stack, infrastructure, patterns) |
| `/product-gtm` | Deliberate on go-to-market positioning (messaging, pricing, distribution) |
| `/product-sprint` | Full sprint orchestration: PRD → deliberation → execute → review |

### Skill

**product-orchestrator** — Core orchestration logic. Classifies product decisions, formats role prompts, invokes Council deliberation, parses outputs, routes to downstream skills, and writes decision records.

### Reference Files

| File | Purpose |
|------|---------|
| `prd-template.md` | PRD format, interview protocol (14 inputs), section inclusion rules, status lifecycle |
| `scope-templates.md` | Four role prompts for scope deliberation (User Advocate, Business Strategist, Ship-It Pragmatist, Long-Game Architect) |
| `architecture-templates.md` | Four role prompts for architecture deliberation (Scalability Realist, Security & Compliance Advocate, DX Champion, Migration Strategist) |
| `gtm-templates.md` | Four role prompts for GTM deliberation (Customer Voice, Market Analyst, Revenue Architect, Contrarian Advisor) |
| `sprint-protocol.md` | Full sprint sequence, deliberation gating rules, execution routing tables |

## Dependencies

This plugin wraps the Council deliberation engine. It does not duplicate Council's mechanics.

**Required:**
- **Council plugin** (v0.6.0+) — provides the deliberation-engine skill that handles multi-model collection, peer review, and synthesis
- **Rube** (rube.sh) — provides OpenRouter connection for multi-model calls
- **OpenRouter** connection via Rube — access to multiple LLM providers

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

- **0.2.0** — Enhanced PRD template. Added User Personas (required, conditional), Non-Functional Requirements, Dependencies & Integrations, Risks & Mitigations, and Verification Approach sections (all optional). New deliberation routing rules for NFR/dependency-driven architecture questions and unmitigated risk-driven scope reconsideration. Section inclusion rules keep lean PRDs lean.
- **0.1.0** — Initial release. Scope, architecture, and GTM deliberation templates. PRD generation. Sprint orchestration. Vault persistence via memory-system.
