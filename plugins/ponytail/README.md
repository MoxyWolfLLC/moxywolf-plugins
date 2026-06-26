# ponytail

The marketplace's horizontal **restraint layer** for coding work. An always-on "lazy senior dev" ruleset, injected before every coding turn, that runs a YAGNI ladder before the agent writes code, then a few audit commands. Lazy means efficient, not careless: it shortens the solution, never the reading, and never cuts validation, error handling, security, or accessibility.

## What it does

Before writing code, the agent stops at the first rung that holds:

1. Does this need to exist at all? (YAGNI)
2. Already in this codebase? Reuse it.
3. Stdlib does it? Use it.
4. Native platform feature covers it? Use it (`<input type="date">` over a picker lib).
5. Already-installed dependency solves it? Use it.
6. Can it be one line? One line.
7. Only then: the minimum that works.

Deliberate simplifications get a `ponytail:` comment naming the ceiling and the upgrade path, so a shortcut reads as intent, not ignorance.

## Surface

- **`ponytail` skill** — the core ruleset. Always-on via the session hooks, and **referenceable by other plugins**: a coding command can cite the `ponytail` skill the way `github-repo-analyzer` cites `graphify-core` to pull the restraint into its own flow.
- **`/ponytail [lite|full|ultra|off]`** — set intensity (default `full`).
- **`/ponytail-review`** — over-engineering review of the current diff; hands back a delete-list.
- **`/ponytail-audit`** — whole-repo over-engineering audit.
- **`/ponytail-debt`** — harvest `ponytail:` shortcuts into a tracked ledger so "later" doesn't become "never".
- **`/ponytail-gain`** — measured-impact scoreboard from the upstream benchmark.
- **`/ponytail-help`** — quick reference.

## Levels

`lite` names the lazier alternative and lets you pick. `full` enforces the ladder (default). `ultra` is the YAGNI extremist for cleanup sprints. Set a session default with `PONYTAIL_DEFAULT_MODE` (off|lite|full|ultra) or `~/.config/ponytail/config.json`.

## How it fits the MoxyWolf stack

ponytail is a posture, not a task plugin, so it enhances the other coding plugins while active:

| Pairs with | Effect |
|---|---|
| `gstack-execution` | Trim then harden: run `/ponytail-review` before `/gstack-review` and `/gstack-codex-review` so you don't harden code that shouldn't exist. |
| `dev-infrastructure-skills` | Keeps generated React/Next/Supabase output minimal and native-first. |
| `saas-frontend-designer` (+ impeccable) | Restraint on generated UI volume; impeccable supplies the taste, ponytail the restraint. |
| `github-repo-analyzer:suggest-fixes` | Keeps proposed fix diffs minimal. |
| `product-orchestrator:product-scope` | Rung 1 (YAGNI) feeds the scope deliberation. |
| `team-kanban` / `obsidian-update` | `/ponytail-debt` ledger feeds deferred shortcuts onto the board as tech-debt cards. |

It does not apply to non-coding plugins (content, marketing, research) — its value is entirely in the coding stack.

## Requirements

The session hooks run two tiny Node lifecycle scripts, so `node` should be on PATH. If it isn't, the skills still work; the always-on activation just stays quiet instead of erroring.

## Attribution

Vendored from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) v4.8.3, MIT License, Copyright (c) 2026 DietrichGebert. The full upstream license is in `LICENSE`. MoxyWolf adaptation: trimmed to the Claude Code surface (skills, hooks, commands), multi-harness adapters and site/benchmark assets dropped, and the six commands rendered as Claude Code markdown from the upstream `.toml`. Skill and hook logic are unchanged from upstream.
