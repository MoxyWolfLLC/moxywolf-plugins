---
description: Start or resume a Cowork session on an existing MoxyWolf project — mount the standard folders, load Project Instructions, read the previous session's handoff, surface kanban tasks, recent decisions, and open GitHub PRs/issues.
---

Run the session-start skill to begin or resume a Cowork session on an existing MoxyWolf project.

The skill assumes the project was already set up via `/init-project` and has a saved `cowork-project-instructions.md` in its `00 – Project Hub/` folder. If the previous session ended with `/session-end`, it will also have a `cowork-session-handoff.md` in the same folder — that's the freshest source of state, and the briefing surfaces its open-work and suggested-opening-line at the top.

It then:

1. Resolves which project — without ever showing a picker. It uses the argument after `/session-start` if provided, otherwise auto-detects the project from the launch directory, and failing that auto-resumes the most recently active project (by most recent session handoff). It announces the resolved project; the user switches by naming a different one.
2. Reads the project's saved `cowork-project-instructions.md` to learn the active Taskade subfolder and the active GitHub repo(s).
3. Ensures the three standard MoxyWolf roots — MoxyWolf Vault, GitHub, Taskade — are mounted for this session. On-computer it mounts any missing root via `mcp__cowork__request_cowork_directory` (the user approves each). In the cloud it detects what's mounted via `mcp__remote-devices__get_device_info` and asks the user to **Add folder** for any missing root (mounting is a user-only action in the cloud).
4. Reads the previous session's handoff at `[project]/00 – Project Hub/cowork-session-handoff.md` if it exists. Parses the canonical sections (What landed / Open work / Commit & push state / Procedural reminders / Suggested opening line). Flags the handoff as stale if `session_ended` is more than 14 days old.
5. Reads the project's own `04 – Backlog & Sprints/` folder and the team Jira board (project MOXY), strictly filtering the board to the project's Jira label (`project-<slug>`, from the `Kanban project tag(s)` declared in the project's instructions) — so only this project's tasks surface, never another project's. (Jira is the single board; the vault `KANBAN_VIEW.md` was retired 2026-07-16.)
6. Surfaces recent (≤14 days) decision records (`DR-*.md`) from the project folder.
7. Lists open PRs and recent open issues from each of the project's GitHub repo(s) via the GitHub MCP.
8. Displays a structured briefing in chat with mounted folders, active subfolders, last-session handoff (open work + suggested opening line), top kanban tasks, recent decisions, and open PRs/issues.
9. Asks the user what to focus on first, with options pulled from the handoff's open work first (if found and not stale), falling back to the project-scoped backlog folder and the project-filtered kanban — never an unscoped task.

If the user passed a project name as an argument, use it directly; otherwise the skill auto-resolves the project (launch directory, then most recently active) without asking. If no saved Project Instructions exist for the resolved project, the skill stops and routes the user to `/init-project` first. If no handoff file exists, the briefing simply omits the handoff sections — the rest of the briefing is still useful.

Pairs with `/session-end`, which writes the canonical-named handoff at the end of each session.
