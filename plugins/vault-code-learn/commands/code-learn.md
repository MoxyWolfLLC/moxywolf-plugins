---
description: Walk one or more MoxyWolf repos and extract a durable Code Patterns digest into the MoxyWolf Vault. Incremental — only re-reads files modified since the last run.
argument-hint: "[repo-name | --all | --project <slug>]"
---

# /code-learn

Trigger the `vault-code-learn` skill against the named repo(s).

## Argument forms

- `/code-learn <repo>` — learn from one specific repo (folder name under `~/Documents/GitHub/`).
- `/code-learn --project <slug>` — read the project's `cowork-project-instructions.md`, learn from every GitHub repo listed there.
- `/code-learn --all` — learn from every repo listed under `~/Documents/GitHub/` (slow; use sparingly).
- `/code-learn` (no args) — auto-detect from launch directory the same way `/session-start` does.

## What it does

For each resolved repo:

1. Computes the file set that has changed since `_Shared Knowledge/Code Patterns/<repo>.md` was last updated (its `last-learned:` frontmatter timestamp). On first run, the whole tree is in scope.
2. Extracts the signal dimensions (tech stack, naming conventions, error handling, test patterns, lint/type rules, file layout, frequent imports).
3. Writes or updates `MoxyWolf Vault/_Shared Knowledge/Code Patterns/<repo>.md` with a new `last-learned:` timestamp and a `learned-from-commits:` frontmatter list of the commit SHAs covered.
4. Surfaces a one-paragraph summary in chat: "Learned N new patterns from <repo>; updated digest at <path>."

## Honors

- Read-only against the repo (no commits, no PRs).
- Respects `.gitignore` and `.codepatternsignore` (if present at repo root).
- Will not re-learn during the same session if `<2h` has passed since the last digest update for the same repo (cheap idempotence).

## See also

- The `vault-code-learn` skill SKILL.md for the full extraction recipe.
- `/session-start` auto-invokes this for the project's active repos.
- `/obsidian-update` cross-links new pattern findings into freshly written Decision Records.
