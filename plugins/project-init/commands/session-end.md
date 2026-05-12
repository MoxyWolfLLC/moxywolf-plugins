---
description: End a Cowork session — write the project handoff that /session-start will read tomorrow, refresh each writable GitHub repo's README.md, then run /obsidian-update to capture durable knowledge into the MoxyWolf vault.
---

Run the session-end skill to wrap a Cowork session and persist a handoff for next time. Then automatically run `/obsidian-update` to capture durable knowledge into the MoxyWolf Obsidian vault.

The skill assumes the project has a saved `cowork-project-instructions.md` in its `00 – Project Hub/` folder (i.e. it was set up via `/init-project`). It then:

1. Resolves which project — uses the argument after `/session-end` if provided, otherwise infers from currently-mounted folders, or lists candidates and asks.
2. Scans the current Cowork conversation to extract: what shipped this session, what's still open in priority order, what's uncommitted in the active repo(s) (with full commit messages drafted ready to paste into GitHub Desktop), production-data state changes, procedural reminders.
3. Composes a handoff document in the canonical structure (frontmatter + `What landed` + `Open work` + `Uncommitted code` + `Procedural reminders` + `Suggested opening line`).
4. Writes it to **`[project]/00 – Project Hub/cowork-session-handoff.md`** — single canonical filename, overwritten each session, Drive versioning preserves history.
5. (Optional) `--archive` flag also writes a dated archive copy to `00 – Project Hub/Session Handoffs/handoff-YYYY-MM-DD-HHMM.md`.
6. **Refreshes each writable GitHub repo's `README.md`** (Step 5c) against the canonical 16-section structure — Header + badges, TOC, Environments, Quick Start, Architecture (Mermaid), Database Schema (ERD), Data Initialization, Key Features, API / Server Actions, Common Workflows, Troubleshooting, Security, Technology Stack (TECH-STACK-V4.3), Project Structure, Deployment, License. Read-only repos are skipped. The README diff is surfaced as a separate commit block in the handoff.
7. Updates the Cowork session-memory layer if the session surfaced cross-project feedback/references.
8. **Runs `/obsidian-update:obsidian-update`** to extract durable knowledge — decisions, research findings, meeting discussions, cross-project insights, action items, new contacts — into the MoxyWolf vault. This is automatic; you no longer need to remember to run `/obsidian-update` separately at the end of every session.
9. Reports the handoff path, the top of next-session stack, README files refreshed, and what the vault update captured, so you can spot-check before signing off.

Pairs with `/session-start`, which reads `cowork-session-handoff.md` and surfaces the open-work and suggested-opening-line in the session-start briefing.
