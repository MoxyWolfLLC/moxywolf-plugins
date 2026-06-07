# Codex Adversarial Review Methodology

The shared protocol behind `/gstack-codex-review`. Both engines — real Codex (`codex exec`) and the Claude fallback — review against this same standard, so the only difference between them is *which model* applies it, not *what* it applies.

Adapted from the review framing in OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (`/codex:adversarial-review`), restructured for gstack and for a just-committed-code scope.

## The point

A normal code review hunts for defects: bugs, missing null checks, untested paths. That's the floor. An **adversarial** review goes a layer up — it asks whether this change should have been built this way at all. The most expensive mistakes aren't typos; they're sound code implementing the wrong approach. This review is built to catch those before they're pushed.

So: spot the defects, but lead with the approach.

## The four adversarial lenses

Apply all four to the committed change. Each is a question you press until it yields or holds.

### 1. Approach
Is this the right way to solve the problem the commit claims to solve?

- Would a simpler construct do the same job with less surface area?
- Is the commit solving a symptom when the cause is elsewhere?
- Does it add a dependency, abstraction, or layer that the problem didn't demand?
- If you described this approach to the author out loud, what's the first objection they'd have to defend?

### 2. Design & tradeoffs
Every design buys something and pays for something. Name both.

- What did this design optimize for (speed, simplicity, flexibility), and what did it trade away (clarity, performance, testability)?
- Is the tradeoff stated anywhere, or is it silent — a cost a future reader inherits without knowing it was chosen?
- Coupling: does this commit tie two things together that will need to change independently later?
- Is there a materially different design (different data model, different boundary, different ownership) that would've been safer or simpler? Say what it is.

### 3. Assumptions
Find the things the code takes for granted and test whether they hold.

- What must be true about inputs, ordering, timing, or external state for this to work? Are those guaranteed or merely usual?
- Does it assume single-threaded execution, a warm cache, a non-empty list, a trusted caller, a fast network, a clock that only moves forward?
- What happens the first time an assumption is false in production — error, silent wrong answer, or corruption?

### 4. Failure modes under real conditions
Move the code out of the happy path and into the world.

- Concurrency: two of these running at once — what races, what double-writes, what deadlocks?
- Partial failure: the operation half-completes — is the state recoverable, or wedged?
- Scale: 100x the data, 100x the requests — what's the first thing that falls over?
- Rollback & data loss: if this ships and has to be reverted, is the change reversible? Does it destroy data that can't be rebuilt?
- Trust boundaries: user input, LLM output, or third-party data flowing somewhere privileged (SQL, a system prompt, a shell, the DOM)?

## The defect floor

Beneath the four lenses, still run the blocking-defect checks from `review-checklist.md`. A finding here is CRITICAL regardless of approach:

- Raw/interpolated SQL (injection)
- Concurrent state mutation without locking (race conditions)
- User or LLM input reaching a system prompt, eval, shell, or `dangerouslySetInnerHTML` without sanitization (trust-boundary breach)
- New routes missing permission checks (auth bypass)
- Destructive operations without confirmation or backout (data loss)
- Unhandled enum/switch cases introduced by the change

## Scope discipline (just-committed)

This review is scoped to *the commit under review*, not the whole branch and not the working tree.

- Findings must point at lines the commit actually touched. If something's wrong in code the commit didn't change, note it once as context, not as a finding against this commit.
- Treat the commit's message as a claim: does the diff deliver what the message says, no more (scope creep) and no less (incomplete)?
- "Nothing to review" is only true when the resolved range is genuinely empty. A small commit still gets the full four-lens pass.

## Output discipline

- **Review-only.** Describe fixes; never apply them. Surfacing a problem and patching it are different jobs — this command does the first only.
- **Concrete always.** File, line, exact condition. "This could race" is not a finding; "two callers of `enqueue()` at worker.ts:42 can both pass the `if (!locked)` check before either sets `locked`" is.
- **Verbatim from the real engine.** When real Codex runs, return its output unedited and labeled — don't blend in Claude's own opinions.
- **Lead with the point.** Severity, then what, then why it matters to the user, then the fix.
- **No AI vocabulary.** No "delve", "crucial", "robust", "comprehensive", "landscape."
