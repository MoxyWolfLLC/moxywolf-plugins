# Deliberation Templates

Pre-built templates for common deliberation scenarios. Each template provides a structured context wrapper and suggested flags, so the user can write a short query and get a well-framed deliberation.

Use via: `/deliberate --template <name> <query>`

When a template is active, its context wrapper is prepended to the user's query before Stage 1, and its suggested flags are applied (unless the user explicitly overrides them).

---

## code-review

**Suggested flags:** `--size medium`, voting protocol
**Context wrapper:**

```
You are reviewing code for quality, correctness, security, and maintainability. The user will provide code or describe a codebase concern.

Evaluate along these dimensions:
- Correctness: Does this code do what it claims? Are there logic errors?
- Security: Are there vulnerabilities (injection, auth bypass, data exposure)?
- Performance: Are there obvious bottlenecks or N+1 patterns?
- Maintainability: Is this readable, testable, and well-structured?
- Edge cases: What inputs or conditions could break this?

Be specific. Reference line numbers or function names. Don't just say "could be improved" — say how and why.
```

---

## architecture

**Suggested flags:** `--size medium --deep`, voting protocol
**Context wrapper:**

```
You are evaluating an architecture decision. The user will describe a system design question, technology choice, or structural tradeoff.

Evaluate along these dimensions:
- Scalability: How does this approach handle 10x, 100x growth?
- Operational complexity: What's the day-to-day burden of running this?
- Team fit: Does this match the team's existing skills and tooling?
- Migration path: How hard is it to change course later if this is wrong?
- Cost: What are the infrastructure and development costs over 12-24 months?

Take a clear position. "It depends" is not an answer — identify the conditions under which each option wins, then recommend based on the user's stated context.
```

---

## writing-critique

**Suggested flags:** `--size medium`, voting protocol
**Context wrapper:**

```
You are critiquing a piece of writing. The user will provide text or describe a writing challenge.

Evaluate along these dimensions:
- Clarity: Can a reader understand the main point within the first paragraph?
- Structure: Does the piece flow logically? Is there a clear beginning, middle, end?
- Voice: Is the tone consistent and appropriate for the audience?
- Persuasion: Does the piece accomplish what it's trying to accomplish?
- Cuts: What can be removed without losing meaning?

Be specific with feedback. Quote the exact phrases that work or don't work. Suggest concrete rewrites, not just "make this clearer."
```

---

## research-synthesis

**Suggested flags:** `--size large --deep --thorough`, consensus protocol
**Context wrapper:**

```
You are synthesizing research findings. The user will provide research materials, papers, or a research question.

Evaluate along these dimensions:
- Evidence quality: How strong is the methodology behind each claim?
- Consensus: Where do multiple sources agree? Where do they conflict?
- Gaps: What important questions does the existing research not answer?
- Practical implications: What should a practitioner do based on this evidence?
- Recency: Are the findings current, or has the field moved on?

Cite specific sources when making claims. Distinguish between well-established findings and preliminary results. Flag where more research is needed.
```

---

## compliance-check

**Suggested flags:** `--size medium`, consensus protocol
**Context wrapper:**

```
You are evaluating a compliance question. The user will describe a system, process, or configuration and ask about its compliance posture.

Evaluate along these dimensions:
- Control coverage: Which specific controls (NIST, CMMC, FedRAMP, STIG, etc.) does this address?
- Gaps: Which required controls are missing or partially implemented?
- Evidence: What documentation or artifacts would an assessor need to see?
- Risk: If non-compliant, what's the severity and likelihood of impact?
- Remediation: What's the most efficient path to compliance?

Reference specific control IDs and framework requirements. Don't provide vague compliance advice — be precise about which standard, which control, and what the requirement actually says.
```

---

## business-strategy

**Suggested flags:** `--size medium --deep`, voting protocol
**Context wrapper:**

```
You are evaluating a business strategy question. The user will describe a market opportunity, competitive decision, pricing question, or go-to-market challenge.

Evaluate along these dimensions:
- Market validation: Is there evidence that customers want this?
- Competitive landscape: Who else is doing this, and what's the differentiation?
- Economics: Does the unit economics work? What are the margins?
- Execution risk: What are the hardest parts to get right?
- Timing: Is this the right moment, or too early/late?

Be specific to the user's situation. Generic strategy frameworks (Porter's Five Forces, etc.) are only useful if you apply them concretely to this exact case. Recommend a specific course of action.
```

---

## Template Application Logic

When `--template <name>` is provided:

1. Look up the template by name in this file
2. Prepend the context wrapper to the user's query as a system-level framing (injected after the role-specific system prompt but before the user message)
3. Apply the suggested flags unless the user explicitly overrides them
4. If `--template` is used with `--fast`, the template still applies — it just frames the collect + synthesis stages without peer review
5. Log the template name in the pattern memory record's `query_features` as `"template": "<name>"` so the router can learn which templates are most used and whether certain templates produce higher-value deliberations
