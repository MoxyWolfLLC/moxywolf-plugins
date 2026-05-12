# Sprint Protocol

Full sprint orchestration that sequences multiple deliberation rounds across a complete build cycle. Use this when the user triggers `/product-sprint` and wants end-to-end coordination from idea through shipping.

## Sprint Philosophy

A sprint is not a feature factory. It's a decision-execution loop. Every sprint has three phases:

1. **Decide** — What are we building and why? (Deliberation)
2. **Execute** — Build the thing. (Downstream skills)
3. **Validate** — Did it work? What did we learn? (Review + next sprint input)

The Product Orchestrator adds structured deliberation to Phase 1 and review gates between phases. Execution (Phase 2) is handled by downstream skills or manual work. The orchestrator gets out of the way during execution and comes back for validation.

## Sprint Sequence

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 0: PRD CHECK                                       │
│ Does a PRD exist for this product? If not, generate one. │
│ Load references/prd-template.md                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1A: SCOPE DELIBERATION                             │
│ What ships this sprint?                                  │
│ Load references/scope-templates.md                       │
│ Council deliberation → scope decision record             │
│                                                          │
│ Output: SHIP / DEFER / CUT lists                         │
│ Update PRD with scope decisions                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1B: ARCHITECTURE DELIBERATION (if needed)          │
│ Trigger: new product, new technical domain, or scope     │
│ includes features requiring architectural decisions       │
│ Load references/architecture-templates.md                │
│ Council deliberation → architecture decision record      │
│                                                          │
│ Skip if: architecture already decided and scope doesn't  │
│ challenge existing assumptions                           │
│                                                          │
│ Output: Technology choices, boundaries, evolution plan    │
│ Update PRD with architecture decisions                   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1C: GTM DELIBERATION (if needed)                   │
│ Trigger: first launch, pivot, pricing change, new market │
│ Load references/gtm-templates.md                         │
│ Council deliberation → GTM decision record               │
│                                                          │
│ Skip if: positioning already validated and sprint is     │
│ incremental feature work                                 │
│                                                          │
│ Output: Positioning, messaging, pricing, distribution    │
│ Update PRD with GTM decisions                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: EXECUTION PLAN                                  │
│ Convert deliberation outputs into concrete tasks.        │
│ No deliberation here — just planning.                    │
│                                                          │
│ For each item in the SHIP list:                          │
│   1. Identify the downstream skill or manual work needed │
│   2. Estimate effort (hours, not story points)           │
│   3. Identify dependencies and sequencing                │
│   4. Flag items that need user input or decisions        │
│                                                          │
│ Output: Ordered task list with skill routing             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: EXECUTE                                         │
│ User confirms the plan. Orchestrator hands off to        │
│ downstream skills one at a time or in parallel.          │
│                                                          │
│ The orchestrator does NOT micromanage execution.         │
│ It presents the next task, confirms the user wants to    │
│ proceed, and invokes the appropriate skill.              │
│                                                          │
│ Between tasks, check:                                    │
│   - Did the previous task complete successfully?         │
│   - Did anything change that affects remaining tasks?    │
│   - Does the user want to adjust the plan?              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: REVIEW GATE                                     │
│ Sprint review. No deliberation — just structured review. │
│                                                          │
│ What shipped:                                            │
│   - List of completed items with links/artifacts         │
│ What didn't ship:                                        │
│   - Deferred items and why                               │
│ What we learned:                                         │
│   - Surprises, blockers, changed assumptions             │
│ Input for next sprint:                                   │
│   - Carry-over items                                     │
│   - New items surfaced during execution                  │
│   - Assumptions that need re-evaluation                  │
│                                                          │
│ Write sprint summary to vault as decision record.        │
│ Update PRD status.                                       │
└─────────────────────────────────────────────────────────┘
```

## Sprint Duration

The orchestrator doesn't enforce sprint length. Some sprints are a single session (idea → deliberate → build → ship in one sitting). Some span a week. The protocol is the same regardless.

Ask the user at sprint start: "Is this a single-session sprint or multi-day?" This determines how much deliberation to front-load.

- **Single session:** Compress Phase 1 into a quick 5-minute deliberation per decision type. Bias toward action.
- **Multi-day:** Full deliberation rounds with complete analysis. Take time to get the decisions right.

## Deliberation Gating

Not every sprint needs all three deliberation types. The orchestrator should recommend which deliberations to run based on what's changing:

| Sprint Context | Scope | Architecture | GTM |
|---------------|-------|-------------|-----|
| New product from scratch | ✅ | ✅ | ✅ |
| New feature for existing product | ✅ | Maybe | No |
| Technical rebuild / migration | No | ✅ | No |
| Launch or repositioning | No | No | ✅ |
| Incremental iteration | Quick scope check | No | No |
| Pricing change | No | No | ✅ |
| Post-pivot | ✅ | ✅ | ✅ |

"Maybe" means: ask the user if the feature requires architectural decisions. If yes, deliberate. If it fits within existing architecture, skip.

## Execution Routing Table

After deliberation, the orchestrator routes tasks to the right skill. When the gstack-execution plugin is installed, prefer its commands for build/review/test tasks — they provide the most structured execution workflows.

### Build Tasks
| Task Type | gstack Command | Fallback Skill |
|-----------|---------------|----------------|
| Code review | `/gstack-review` | `code-review-pro` |
| Bug investigation | `/gstack-investigate` | Manual debugging |
| Security audit | `/gstack-cso` | `code-review-pro` (limited) |
| Ship / PR creation | `/gstack-ship` | Manual git + gh |
| Design system | `/gstack-design` | `frontend-design` |
| Browser QA | `/gstack-qa` | `playwright-testing` |
| Deploy verification | `/gstack-browse` | Manual browser check |
| Database schema | `database-schema-designer` | `supabase-postgres` |
| New application | `dev-create-orchestrator` | Manual coding |
| React components | `react-best-practices` | `frontend-design` |
| Next.js pages | `next-best-practices` | `dev-create-orchestrator` |
| API design | `api-documentation-writer` | Manual spec |
| Tests | `test-driven-development` | `playwright-testing` |

### Marketing Tasks
| Task Type | Primary Skill | Fallback |
|-----------|--------------|----------|
| Landing page copy | `copywriting` | `page-cro` |
| Pricing page | `pricing-copywriter` | `pricing-strategy` |
| Email sequences | `email-sequence` | `cold-email` |
| Social content | `social-content` | Manual |
| SEO | `seo-audit` | `ai-seo` |
| Launch plan | `launch-strategy` | `marketing-brief` |

### Analysis Tasks
| Task Type | Primary Skill | Fallback |
|-----------|--------------|----------|
| Competitor research | `pricing-research` | `competitor-alternatives` |
| CRO audit | `page-cro` | `cro-audit` |
| Content strategy | `content-strategy` | Manual |

### Recommended Execution Sequence (with gstack)

For a typical build sprint, the natural flow is:

```
Deliberation output (scope/arch decisions)
    │
    ▼
Code the feature (manual or dev-create-orchestrator)
    │
    ▼
/gstack-review (catch issues before they compound)
    │
    ▼
/gstack-cso (security check — especially for auth, payments, data)
    │
    ▼
/gstack-qa (browser testing via Rube Playwright)
    │
    ▼
/gstack-ship (test suite + PR creation)
    │
    ▼
/gstack-browse (verify deploy)
```

Not every sprint needs every step. A content-only sprint skips everything except the marketing routing. A bug fix might only need `/gstack-investigate` → fix → `/gstack-review` → `/gstack-ship`.

## Sprint Decision Record

At sprint completion (Phase 4), write a sprint summary to the vault:

**Path:** `_Shared Knowledge/Product Decisions/sprint-{YYYY-MM-DD}-{product-slug}.md`

```markdown
---
type: sprint-summary
date: {YYYY-MM-DD}
product: {product name}
sprint_type: {single-session | multi-day}
deliberations_run: {scope, architecture, gtm — list which ran}
status: completed
---

# Sprint Summary: {Product} — {Date}

## Deliberation Decisions
{Link to each PD record created during this sprint}

## Shipped
- {item 1} — {skill used or manual}
- {item 2}

## Deferred
- {item} — {reason}

## Learnings
- {what surprised us}
- {what we'd do differently}

## Next Sprint Input
- {carry-over items}
- {new items discovered}
- {assumptions to re-evaluate}
```
