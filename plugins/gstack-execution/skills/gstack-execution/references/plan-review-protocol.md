# Plan-Review Loop Protocol

The shared protocol behind `/gstack-plan-review`. Both engines — real Codex (`codex exec`) and the Claude fallback — run the same loop against the same standard; the only difference is which model plays the critic.

Concept-ported from the Act 2 review loop in [grill-me-codex](https://github.com/chaseai-yt/grill-me-codex) (Chase AI, MIT; itself building on Matt Pocock's `grill-me`, MIT). The loop discipline is theirs; the hybrid-engine execution and the house arbitration rules are gstack's. No code copied.

## The point

`codex-review-methodology.md` catches expensive mistakes *after* they're committed. This protocol catches them earlier, where they're nearly free to fix: in the plan. The most expensive class of mistake — sound code implementing the wrong approach — is fully visible in a good plan and fully invisible in a green test suite. So the plan gets the argument, before the code exists.

Three properties make the loop work. **Iteration with memory:** the critic sees its own prior objections each round and checks only whether they were addressed — no re-litigating settled points, no fresh-eyes drift. **Bounded rounds:** the loop always terminates at `MAX_ROUNDS` (default 5); unbounded model-vs-model argument converges on nothing. **Deadlock as a first-class outcome:** a cap-out with live disagreements is surfaced as exactly that. A flagged disagreement beats a fake "approved" — the human breaks the tie with both positions in front of them.

## Roles

- **Builder (Claude, this session):** drafts the plan, revises it each round, and arbitrates the critiques — incorporating the ones that hold, rejecting the ones that don't, with a logged reason for every rejection. Neither caving to the critic on everything (which defeats the second perspective) nor ignoring it (which defeats the review).
- **Critic (Codex or a fresh-context Claude subagent):** adversarial, read-only, specific. Its job is to find what breaks, not to be agreeable.
- **Human:** enters exactly twice — kickoff, and final sign-off on the converged or deadlocked result. No round-by-round approvals.

## The review prompt (both engines)

> You are an adversarial reviewer of an implementation plan. Be skeptical and specific — find what breaks. Read the plan at `<PLAN_FILE>` (and any repo files you need; you are read-only). Report **every finding you have**, each tagged `[MATERIAL]` (would change what gets built) or `[MINOR]` (worth noting) — do not withhold small findings; the builder filters, you don't. Look for: wrong or missing assumptions, simpler designs that do the same job, unhandled failure modes and edge cases, schema or API conflicts with the existing code, security holes, sequencing errors, scope creep, unstated tradeoffs. For each finding give a one-line concrete fix. Do not modify any files. End with EXACTLY one line: `VERDICT: APPROVED` if the plan is sound enough to implement, or `VERDICT: REVISE` if material problems remain.

The severity split matters: the critic reports everything and tags it; filtering happens at the builder's arbitration step, never inside the critic. A critic told to report only serious problems silently drops real ones.

## Real-Codex mechanics (codex-ready path)

Verified mechanics — each one exists because its absence produced a real failure:

- **Round 1** creates the session: `codex exec -s read-only --json -o /tmp/codex-verdict.txt "<prompt>" < /dev/null` — parse `thread_id` from the `{"type":"thread.started",...}` stream line. The critique lands in the `-o` file; read that, never parse the JSONL for content.
- **Rounds 2..N** resume the SAME session: `codex exec resume "$THREAD_ID" -c sandbox_mode="read-only" --json -o /tmp/codex-verdict.txt "<re-review prompt>" < /dev/null`.
  - `resume` rejects `-s` — read-only MUST be forced via `-c sandbox_mode="read-only"`, or the critic inherits the user's config default (possibly `danger-full-access`) and can write files mid-loop. This is the single most important safety detail in the protocol.
  - Resume by **explicit thread id**, never `--last` — a wrong or missing id can silently land in a different session and look like a successful run.
- `< /dev/null` on every call — `codex exec` reads stdin in addition to the prompt arg and hangs forever waiting for EOF under a non-TTY driver.
- **Timeout ceiling** on every call — 10 minutes (Bash tool `timeout: 600000`); a tripped ceiling is a failed run to surface, not a retry.
- Don't pin a model (`-m`) — ChatGPT-account auth rejects pinned `-codex` variants. Echo the active model from `~/.codex/config.toml` before Round 1 so the user can object before a round is spent.
- On auth/model errors, surface them and offer the Claude fallback — never silently retry, never silently fall through.

## Claude-fallback mechanics (the Cowork-sandbox path)

The point of a second model is that it didn't write the plan. Without Codex, approximate that with **context isolation**:

- Each round's critic is a **fresh subagent** (Agent tool) whose entire input is: the review prompt, `PLAN_FILE`, `LOG_FILE` (so settled points aren't re-litigated — this substitutes for session memory), and read access to the repo. It never sees the builder's conversation, and it has no Write access.
- Label the output honestly — `Engine: Claude fallback (fresh-context critic)` — so the user can weigh it. Same-family review catches less than cross-model review; it still catches what the builder can't see about its own work.
- Return the critic's findings verbatim into the log; the builder's arbitration is a separate, clearly-marked entry.

## The log

`PLAN-REVIEW-LOG.md` is the deliverable — the argument transcript. Per round: the critic's full critique, then the builder's response (what changed, what was rejected, why). On deadlock: the final side-by-side of unresolved positions and the human's ruling. A plan whose contested decisions have a written argument behind them is a different asset than a plan that was merely written.

## Hard rules

- The critic never writes a file — either engine, any round.
- The loop always terminates at `MAX_ROUNDS`.
- Every rejection of a critique gets a logged reason.
- No code until the human gate. The plan converging is not permission to build.
- Deadlock is surfaced, never smoothed over.
