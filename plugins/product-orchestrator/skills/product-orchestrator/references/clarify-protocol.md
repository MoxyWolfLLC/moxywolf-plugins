# Clarify Protocol

The disambiguation pass `/product-clarify` runs on a PRD before architecture deliberation. Concept-ported from spec-kit's `/speckit.clarify` (MIT); re-specified for the product-orchestrator PRD flow. The goal: surface and resolve the ambiguities that would otherwise get baked into the architecture as unstated assumptions — with the fewest, highest-impact questions.

## Ambiguity taxonomy

Scan the PRD against these categories. For each, mark **Clear** / **Partial** / **Missing**:

1. **Problem & users** — who exactly this is for, the job they're hiring it to do, the pain being removed.
2. **Functional scope** — what the product does and, explicitly, what it does not do this cycle.
3. **Data model & entities** — the core objects, their relationships, ownership, lifecycle.
4. **Interaction & UX flow** — the primary paths, states, and what happens on the unhappy paths.
5. **Non-functional requirements** — performance, scale, security posture, accessibility, compliance obligations.
6. **Integrations & dependencies** — external systems, APIs, auth, data egress.
7. **Edge cases & failure modes** — what happens when inputs are bad, systems are down, limits are hit.
8. **Success & verification** — how "done" and "working" are measured; acceptance criteria.
9. **Constraints & non-negotiables** — time/money/technical limits, and anything the charter fixes.

Build the coverage map internally. Only output it if no questions will be asked (then show it as evidence the PRD is clear).

## Question selection

- **Cap: 5 questions total** per session. Retries to disambiguate a single question don't count as new questions.
- Queue candidates only for **Partial** or **Missing** categories.
- Rank by **Impact × Uncertainty**. Impact = how much the answer changes architecture, data model, task decomposition, scope, UX behavior, or compliance. Uncertainty = how unresolved the category is.
- Each question must be answerable from **a short option set (2–4 choices)** or **a one-line answer**. Prefer AskUserQuestion option sets.
- **Exclude:** anything already answered in the PRD or prior conversation; stylistic preferences; plan-level execution detail (unless it blocks correctness); speculative tech-stack questions unless the gap blocks functional clarity.
- If more than 5 categories remain unresolved, take the top 5 by the heuristic and defer the rest explicitly.

## Asking loop

- Present **exactly one** question at a time. Never reveal the queue.
- Record each answer in working memory; don't write to disk mid-loop.
- **Stop** when: all critical ambiguities are resolved (remaining queued items become unnecessary), the user declines further questions, or 5 questions have been asked.
- If no valid questions exist at the start, report no critical ambiguities and suggest advancing.

## Encode-back rules

After the loop, write answers into the PRD:

- Put each answer in the **correct PRD section** (functional answer → Functional Requirements; NFR answer → Non-Functional Requirements; etc.), not a scratch block.
- Append a `## Clarifications ({YYYY-MM-DD})` block with one `- Q: <question> → A: <final answer>` bullet per accepted answer.
- If an answer **invalidates** an earlier ambiguous statement, replace that statement — don't duplicate. Leave no obsolete or contradictory text.
- Keep terminology canonical: if an answer settles a term, use it consistently across every section touched (note the old term once as `(formerly "X")` only if necessary).

## Validation before finishing

- Clarifications block has exactly one bullet per accepted answer (no duplicates).
- Total accepted questions ≤ 5.
- Same canonical term used across all updated sections.
- Any category still Partial/Missing at quota is listed under **Deferred** with a one-line rationale.

## Reporting

Close with: questions asked/answered, categories resolved, Deferred items (with rationale), and the recommended next step — `/product-scope` if scope is still open, `/product-arch` if the PRD is now crisp enough to settle the architecture.
