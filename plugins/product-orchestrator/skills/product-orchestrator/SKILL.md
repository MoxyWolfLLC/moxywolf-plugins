---
name: product-orchestrator
description: >
  This skill should be used when the user asks to "deliberate on a product decision",
  "scope this feature", "evaluate this architecture", "deliberate on positioning",
  "product council", "should we build this", "sprint planning with deliberation",
  "what should we ship", "product scope review", "architecture decision",
  "GTM strategy deliberation", or any request that involves making a product
  decision that would benefit from structured multi-model friction before execution.
  Also trigger when the user uses /product-scope, /product-arch, /product-gtm,
  or /product-sprint. This plugin wraps the Council deliberation engine with
  product-specific role prompts and routes outputs to downstream execution skills.
version: 0.2.0
---

# Product Orchestrator

Transform product decisions into structured multi-model deliberations, then route the synthesized output to downstream execution skills. This plugin does not duplicate Council. It wraps it with product-specific intelligence.

## Core Principle

Most product work doesn't need a committee. Writing a component, fixing a bug, drafting copy — just do it. But three categories of product decisions reliably destroy solo founders when made by a single mind: **scope decisions**, **architecture choices**, and **go-to-market positioning**. These are the moments where motivated reasoning, confirmation bias, and sunk-cost thinking kill products quietly.

The Product Orchestrator triggers multi-model deliberation only at these decision points, then gets out of the way so execution can happen fast.

## How It Works

```
Product Question
    │
    ▼
┌──────────────────────┐
│ CLASSIFY DECISION     │  What type of product decision is this?
│ scope / arch / gtm /  │  Route to the right deliberation template
│ execute-only          │
└──────────┬───────────┘
           │
     ┌─────┴──────┐
     │             │
  Needs         Execute
  Deliberation  Directly
     │             │
     ▼             ▼
┌──────────────┐  ┌──────────────┐
│ FORMAT ROLES │  │ HAND TO      │
│ Load template│  │ DOWNSTREAM   │
│ for decision │  │ SKILL        │
│ type         │  │ (no council) │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌──────────────────────┐
│ CALL COUNCIL          │  Invoke deliberation-engine skill
│ Pass role prompts +   │  with product-specific role assignments
│ decision context      │  and structured output requirements
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ EXTRACT DECISIONS     │  Parse Council's synthesis into
│ Structured output:    │  actionable product decisions with
│ - Decision + rationale│  explicit tradeoffs and confidence
│ - Tradeoffs accepted  │
│ - Risks flagged       │
│ - Next actions        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ROUTE TO EXECUTION    │  Hand off to downstream skills:
│ Connect decision to   │  dev-create, growth-engineer,
│ the right skill for   │  pricing-engine, content pipeline,
│ implementation         │  or manual task list
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ WRITE DECISION RECORD │  Persist to vault via memory-system
│ Product decision log  │  for institutional memory
└──────────────────────┘
```

## Decision Classification

When the user brings a product question, classify it before doing anything else.

### Scope Decisions (use `references/scope-templates.md`)

Trigger words: "should we add", "feature creep", "MVP", "scope", "cut this", "expand", "phase", "prioritize features", "what ships in v1"

The question underneath: **What do we build and what do we deliberately not build?**

These kill products because the builder's instinct is always to add. Every feature feels justified in isolation. Multi-model friction surfaces the features that feel necessary but aren't, and the cuts that feel painful but are correct.

### Architecture Decisions (use `references/architecture-templates.md`)

Trigger words: "monolith or microservices", "build or buy", "tech stack", "database choice", "auth approach", "API design", "infrastructure", "should this be a service", "scaling strategy"

The question underneath: **What technical foundation do we commit to, knowing it's expensive to change later?**

These kill products because architecture decisions compound. The wrong call at month 1 becomes a rewrite at month 6. Multiple models with different training data genuinely see different failure modes in technical foundations.

### GTM / Positioning Decisions (use `references/gtm-templates.md`)

Trigger words: "who is this for", "positioning", "messaging", "pricing model", "go to market", "launch strategy", "target market", "value proposition", "competitive angle", "how do we sell this"

The question underneath: **Who cares about this, why, and how do we reach them?**

These kill products because builders are terrible at seeing their product from the buyer's perspective. The features you're proud of are not the features that sell. Multi-model deliberation externalizes the buyer's voice.

### Execute-Only (no deliberation needed)

If the question is clearly implementation ("build this component", "write this copy", "fix this bug", "deploy this"), skip deliberation entirely. Route directly to the appropriate downstream skill.

Signs it's execute-only:
- The decision has already been made. They're asking for the work, not the choice.
- It's reversible in under a day. Wrong answer costs hours, not months.
- There's an obvious right answer that doesn't depend on perspective.

## Invoking Council Deliberation

When deliberation is needed, format the Council invocation with product-specific structure. Do NOT call `RUBE_MULTI_EXECUTE_TOOL` directly. Instead, trigger the `deliberation-engine` skill, which handles the full pipeline (routing, collection, peer review, synthesis).

### Preparing the Council Call

1. **Load the decision template.** Read the appropriate reference file (`scope-templates.md`, `architecture-templates.md`, or `gtm-templates.md`) to get the role prompts for this decision type.

2. **Build the context block.** Assemble what the models need to deliberate:

```
[PRODUCT CONTEXT]
Product: {product name and one-line description}
Stage: {idea / building / launched / scaling}
Team: {solo / small team / growing}
Current users: {none / early adopters / established base}
Revenue: {pre-revenue / early revenue / established}
Key constraint: {time / money / technical / market}

[DECISION REQUIRED]
Type: {scope / architecture / gtm}
Question: {the specific decision, framed as a question}
Options considered: {what the user has already thought about}
Stakes: {what happens if we get this wrong}

[ADDITIONAL CONTEXT]
{any relevant details: existing tech stack, competitive landscape,
user feedback, metrics, prior decisions on this topic}
```

3. **Format the deliberation request.** Present the context block and role prompts to the deliberation-engine skill. The key instruction:

> "Run a Council deliberation on the following product decision. Use these role assignments instead of the default model roles. Each model should argue from its assigned product perspective, not just its natural reasoning style. The synthesis should produce a specific recommendation with explicit tradeoffs, not a balanced summary."

### Role Assignment Override

The default Council assigns roles based on model reasoning styles (analytical, creative, practical, contrarian). For product decisions, override with product-specific roles. Each decision type has four roles defined in its template file.

The friction comes from assigning models perspectives that naturally conflict:
- The user advocate vs. the business strategist
- The "ship it now" pragmatist vs. the "do it right" architect
- The market analyst vs. the technical feasibility expert

### Structured Output Requirement

Tell the Council synthesis to format its output as:

```
## Decision
{One clear recommendation in 1-2 sentences}

## Confidence
{strong / moderate / low} — {why this confidence level}

## Rationale
{The 2-3 strongest arguments that won the deliberation}

## Tradeoffs Accepted
{What we're giving up. Be specific.}

## Risks Flagged
{What could go wrong with this decision. Include dissenting views.}

## Next Actions
{3-5 concrete next steps to execute this decision}

## Downstream Routing
{Which skills/tools should execute the next actions}
```

## Routing to Downstream Skills

After deliberation, parse the "Next Actions" and "Downstream Routing" section and connect to the right execution skill. Common routing patterns:

| Decision Type | Typical Downstream Skills |
|--------------|--------------------------|
| Scope → Build | `dev-create-orchestrator`, `database-schema-designer` |
| Scope → Content | `content-strategy`, `blog-content-ecosystem` |
| Scope → Cut | Manual task list (no skill needed, just decisions to document) |
| Architecture → Stack | `dev-infrastructure-skills`, `supabase-postgres` |
| Architecture → Design | `database-schema-designer`, `dev-create-orchestrator` |
| GTM → Positioning | `copywriting`, `product-marketing-context` |
| GTM → Pricing | `saas-pricing-engine` (research → model → copy) |
| GTM → Launch | `launch-strategy`, `email-sequence`, `social-content` |
| GTM → Growth | `growth-engineer-skills` (various) |

Don't auto-execute downstream skills. Present the routing recommendation and let the user confirm. The deliberation output often changes what the user thought they'd do next.

## Decision Records

After every product deliberation, write a decision record. Two destinations:

### 1. Local Session (always)
Present the full decision record in conversation so the user can react, push back, or redirect.

### 2. Vault Persistence (when available)
If the Obsidian vault is accessible (via memory-system's vault discovery), write a product decision record:

**Path:** `_Shared Knowledge/Product Decisions/PD-{NNN}-{slug}.md`

**Format:**
```markdown
---
type: product-decision
id: PD-{NNN}
date: {YYYY-MM-DD}
product: {product name}
decision_type: {scope | architecture | gtm}
confidence: {strong | moderate | low}
status: active
---

# PD-{NNN}: {Decision Title}

## Context
{Why this decision was needed}

## Decision
{The recommendation}

## Rationale
{Key arguments}

## Tradeoffs
{What we gave up}

## Risks
{What could go wrong}

## Dissenting Views
{Models that disagreed and why}

## Next Actions
- [ ] {action 1}
- [ ] {action 2}
- [ ] {action 3}

## Related
- {Links to related vault notes, prior decisions, project files}
```

Number PD records sequentially. Check existing records in the vault folder to find the next number.

## Sprint Protocol

For full sprint orchestration (`/product-sprint`), see `references/sprint-protocol.md`. This coordinates multiple deliberation rounds across a complete build cycle: scope → architecture → implementation plan → review gates.

## What This Plugin Is NOT

- **Not a replacement for Council.** Council handles the deliberation mechanics. This plugin handles the product-specific framing and downstream routing.
- **Not a project management tool.** It produces decisions and next actions. Tracking those actions is the user's domain (Obsidian Kanban, task lists, whatever).
- **Not a code generator.** When architecture decisions need implementation, this plugin routes to `dev-create-orchestrator` or similar. It doesn't write code itself.
- **Not needed for every product question.** If you already know what to build and just need to build it, skip this entirely. The value is in the hard calls, not the obvious ones.
