# obsidian-skills

Steph Ango's five official Obsidian agent skills, vendored into the MoxyWolf marketplace.

## What ships

| Skill | What it does |
|---|---|
| `obsidian-markdown` | Renders wiki-links `[[foo]]`, callouts `> [!note]`, transclusion `![[foo#section]]`, footnotes, and frontmatter correctly. |
| `obsidian-bases` | Writes valid `.base` Bases queries (Obsidian's new query language that replaced Dataview for most use cases). |
| `json-canvas` | Reads and writes JSON Canvas (`.canvas`) files — the open spec for Obsidian's visual boards. |
| `obsidian-cli` | Drives Obsidian from the shell via the `obsidian://` URL scheme and the `obsidian-cli` package. |
| `defuddle` | Cleans web pages into readable Markdown for vault clipping (replaces Readability). |

## Why vendor instead of installing per-Mac

One marketplace version bump pushes all five skills to every team Mac at once. No drift between machines.

## Upstream

[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) — Apache-2.0. Re-sync by pulling that repo and overwriting `skills/` here.

## Pairs with

- `vault-skills` — six `vault-*` workflow skills (capture, save, journal, synthesize, MOC, health).
- `vault-code-learn` — extracts code patterns from your repos into `_Shared Knowledge/Code Patterns/`.
- `obsidian-update` — end-of-session knowledge extraction.
