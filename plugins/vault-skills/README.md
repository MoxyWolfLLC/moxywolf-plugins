# vault-skills

Six `vault-*` workflow skills vendored from [az9713/claude-code-obsidian](https://github.com/az9713/claude-code-obsidian) (MIT). These are the daily Obsidian workflows; pair with `obsidian-skills` for the file-format foundation.

## What ships

| Skill | Trigger | What it does |
|---|---|---|
| `vault-capture` | "capture this", "send to inbox" | Drops a quick note into `_Shared Knowledge/_inbox/` with timestamp + source. |
| `vault-save` | "save this to the vault" | Picks the correct folder (project, shared, people) and writes a structured note. |
| `vault-journal` | "journal", "daily note" | Authors today's `Daily Journal/YYYY-MM-DD.md` with the standard template. |
| `vault-synthesize` | "synthesize these notes" | Reads multiple notes, builds a synthesis with citations. |
| `vault-moc` | "make a MOC for X", "map of content" | Builds a `Maps of Content` index page linking related notes. |
| `vault-health` | "vault health", "audit the vault" | Reports orphans, broken links, stale frontmatter, untemplated notes. |

## How they overlap with MoxyWolf plugins (and how we keep them out of each other's way)

- `obsidian-update` remains the **session-end extraction** path — Decision Records, Research Notes, Insights. It is more opinionated and writes to the MoxyWolf folder schema.
- `vault-capture` is the **mid-session quick-drop** path — a single thought into `_inbox/`, not a structured note.
- `vault-journal` runs `Daily Journal/`; `obsidian-update` does not write daily journals.
- `vault-health` is the **audit** path; run it weekly via `/vault-health`.

## Upstream

az9713/claude-code-obsidian — re-sync by pulling and overwriting `skills/`.
