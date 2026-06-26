# vault-code-learn

The missing **code-learning loop** for the MoxyWolf uber-brain.

The vault already captures Decision Records, Research Notes, Insights, and Operating Norms — the *knowledge* axis. This plugin closes the **code axis**: it reads the team's repos and writes a per-repo *Code Patterns* digest into `_Shared Knowledge/Code Patterns/<repo>.md`. Future Claude sessions consult that digest before suggesting code, so suggestions match the team's existing style instead of generic boilerplate.

## How it runs

| Mode | Trigger |
|---|---|
| Manual, single repo | `/code-learn <repo>` |
| Manual, whole project | `/code-learn --project <slug>` |
| Manual, every repo | `/code-learn --all` |
| Auto | `/session-start` invokes it for the active project's repos |

The digest is **incremental**: only files modified since the digest's `last-learned:` frontmatter timestamp are re-read on subsequent runs. First run on a big repo is capped at the 300 most-recent tracked files.

## What goes into the digest

Tech stack signature, build & test commands, naming conventions, error-handling style, test patterns, type/lint rules, file layout, frequent imports (internal + third-party), recurring helpers, and **what this repo intentionally does NOT use** — the negative signals that stop future-Claude from proposing rejected tools.

See `skills/vault-code-learn/SKILL.md` for the full extraction recipe.

## Pairs with

- `obsidian-update` — when a new Decision Record touches code style or tooling, it auto-cross-links to the relevant Code Patterns digest.
- `project-init` / `session-start` / `session-end` — the Code Patterns digest is referenced in the session-start briefing, so next-Claude sees the digest's freshness on every session resume.
- `obsidian-skills` + `vault-skills` — markdown rendering, MOC building, and vault-health for the digests.

## Safety

The script is read-only against the repo. It never commits, opens PRs, or modifies code. The only write target is `MoxyWolf Vault/_Shared Knowledge/Code Patterns/<repo>.md`.
