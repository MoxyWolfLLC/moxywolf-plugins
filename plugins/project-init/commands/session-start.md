---
description: Start or resume a Cowork session on an existing MoxyWolf project — mount the standard folders, load Project Instructions, read the previous session's handoff, surface kanban tasks, recent decisions, and open GitHub PRs/issues.
---

Run the session-start skill to begin or resume a Cowork session on an existing MoxyWolf project.

The skill assumes the project was already set up via `/init-project` and has a saved `cowork-project-instructions.md` in its `00 – Project Hub/` folder. If the previous session ended with `/session-end`, it will also have a `cowork-session-handoff.md` in the same folder — that's the freshest source of state, and the briefing surfaces its open-work and suggested-opening-line at the top.

It then:

1. Resolves which project — uses the argument after `/session-start` if provided, otherwise lists candidate projects (subfolders of `Taskade/` and `MoxyWolf Vault/Projects/` that have saved Project Instructions, sorted by recency) and asks the user to pick.
2. Reads the project's saved `cowork-project-instructions.md` to learn the active Taskade subfolder and the active GitHub repo(s).
3. Mounts the three standard MoxyWolf roots — MoxyWolf Vault, GitHub, Taskade — for this session by calling `mcp__cowork__request_cowork_directory` with each explicit path. The user approves each one (or skips if already mounted).
4. Reads the previous session's handoff at `[project]/00 – Project Hub/cowork-session-handoff.md` if it exists. Parses the canonical sections (What landed / Open work / Uncommitted code / Procedural reminders / Suggested opening line). Flags the handoff as stale if `session_ended` is more than 14 days old.
5. Reads the kanban view at `MoxyWolf Vault/Tasks/KANBAN_VIEW.md` and filters to this project's P0 / P1 / Waiting items.
6. Surfaces recent (≤14 days) decision records (`DR-*.md`) from the project folder.
7. Lists open PRs and recent open issues from each of the project's GitHub repo(s) via the GitHub MCP.
8. Displays a structured briefing in chat with mounted folders, active subfolders, last-session handoff (open work + suggested opening line), top kanban tasks, recent decisions, and open PRs/issues.
9. Asks the user what to focus on first, with options pulled from the handoff's open work first (if found and not stale), falling back to the top of the kanban.

If the user passed a project name as an argument, use it directly; otherwise the skill lists candidate projects and asks the user to pick. If no saved Project Instructions exist for the named project, the skill stops and routes the user to `/init-project` first. If no handoff file exists, the briefing simply omits the handoff sections — the rest of the briefing is still useful.

Pairs with `/session-end`, which writes the canonical-named handoff at the end of each session.
