# Project Charter — Template & Protocol

The charter is a project's **constitution**: the durable principles, hard constraints, and architectural boundaries that hold across every feature. The Council loads it as context before `/product-scope` and `/product-prd` so deliberation starts from the project's established invariants instead of relitigating them each time.

Adapted from GitHub spec-kit's `constitution` primitive (see DR-004 for the borrow/skip rationale). One difference is deliberate: the MoxyWolf charter is **passive governance** — it informs decisions, it never blocks them.

## What belongs in a charter (and what doesn't)

A charter holds **invariants** — things that should stay true across the whole project:

- Mission: one line on what the project is for.
- Principles: 3–7 durable commitments that shape how decisions get made.
- Technical constraints: stack, runtime, or platform facts that are expensive to change.
- Architectural boundaries: what owns what; seams that must not be crossed; things that must never happen.
- Non-negotiables: compliance, security, and data-egress rules that override convenience.

It does **not** hold anything that changes feature-to-feature. Requirements, milestones, and per-feature tradeoffs live in PRDs and sprint plans, not the charter. If a line would be edited on the next feature, it isn't a charter line.

**Litmus test:** every principle should be falsifiable enough that the Council can hold a proposed decision up against it and say "this violates principle 3." Vague aspirations ("build great software") fail the test; concrete invariants ("the importer owns all lexicon Supabase writes; extractors emit packages only") pass it.

## Interview protocol

Ask only for what isn't already evident from the arguments, the repo, prior conversation, or an existing charter. Pull candidate principles from the project's decision records (`DR-*.md`, `PD-*.md`) and ask the user to confirm rather than asking cold.

1. **Mission** — "In one sentence, what is this project for?"
2. **Principles** — "What 3–7 commitments should hold no matter which feature we're building?" Offer candidates harvested from decision records and existing docs.
3. **Technical constraints** — "What stack/runtime/platform facts are fixed and expensive to change?"
4. **Architectural boundaries** — "What owns what? What seam must never be crossed? What must never happen?"
5. **Non-negotiables** — "Any compliance, security, or data-handling rules that override convenience?"

Keep the whole charter to roughly one screen. Long charters get ignored; short ones get honored.

## File format

Write to `CHARTER.md` at the project root:

```markdown
---
type: project-charter
project: {project name}
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
status: active
---

# {Project} Charter

## Mission
{One line.}

## Principles
1. {Durable commitment — falsifiable, not aspirational.}
2. {...}
3. {...}

## Technical Constraints
- {Fixed stack/runtime/platform fact and why it's fixed.}

## Architectural Boundaries
- {What owns what / seam that must not be crossed / what must never happen.}

## Non-Negotiables
- {Compliance, security, data-egress rule that overrides convenience.}

## Version History
- {YYYY-MM-DD}: {what changed and why.}
```

On an **update**, preserve the existing `## Version History` block and append a new dated entry; bump `updated` in the frontmatter.

## How the Council consults the charter

When `/product-scope` or `/product-prd` runs and a `CHARTER.md` exists at the project root, load it and inject it into the deliberation context block as a `[PROJECT CHARTER]` section, placed above `[DECISION REQUIRED]`:

```
[PROJECT CHARTER — load-bearing invariants for this project]
Mission: {mission line}
Principles: {numbered principles}
Constraints: {technical constraints}
Boundaries: {architectural boundaries}
Non-negotiables: {non-negotiables}
[END CHARTER]
```

Instruct the models to **check the proposed decision against the charter** and flag any principle or boundary it would violate — but to treat the charter as binding context, not a veto. A decision that needs to break a charter principle is allowed; it just has to say so explicitly and justify it, which is also the signal that the charter itself may need a versioned update.

## Progressive opt-in rigor

The charter scales with the stakes of the change (DR-004):

- **Tiny / reversible changes** — ignore the charter; proceed straight through the existing path.
- **Medium changes** — charter informs the Council deliberation.
- **Large / hard-to-reverse changes** — charter is load-bearing; a violation should stop and force either a redesign or an explicit, justified charter amendment.

Absent a `CHARTER.md`, every command behaves exactly as it did before this feature existed.
