---
description: Compatibility entry point — runs /gstack-peer-review with builder=claude (Codex reviews); review unavailable when codex is absent, never a same-tool substitute
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, AskUserQuestion
argument-hint: [--base <ref>] [commit-ref] [focus ...]
---

Kept for muscle memory. Since 0.10.0 this is `/gstack-peer-review --builder claude`: Codex reviews the pinned commits against `references/peer-review-contract.md`, with the bounded loop, stable finding IDs, and explicit outcomes.

What changed from the 0.9.x behavior, and why:

- **No approach challenges.** "Challenge the approach" reopened settled design after implementation. That review belongs in `/gstack-plan-review`, before code. Here the approach is an exclusion.
- **Direct-dependency scope, not touched lines.** A changed function can break an unchanged caller; the contract lets the reviewer follow direct callers, immediate helpers, the boundary the change crosses, and the tests for it, with a stated reason.
- **The loop closes itself.** Blockers are substantiated, fixed within scope, and re-verified by the reviewer, up to the round limit; only unresolved disagreements come back to the user.
- **No Claude fallback.** When `codex` is not installed, the outcome is `review_unavailable`. A same-tool pass is still available as `/gstack-review`, labeled as such; it is not presented as independent review.

Parse `$ARGUMENTS` as before (`--base <ref>`, a bare commit ref, trailing focus text goes into the packet's `changed_behavior`), then follow `/gstack-peer-review` from Step 1 with `--builder claude`.
