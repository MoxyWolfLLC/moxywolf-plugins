# MoxyWolf Plugin Marketplace

Canonical home for every plugin authored by MoxyWolf LLC, plus a bundle of the standalone skills used across the team. Hosted as a Claude Code / Cowork marketplace at `github.com/MoxyWolfLLC/moxywolf-plugins`.

Adding this marketplace on any Mac gives that machine all 17 plugins in one shot, with updates flowing from `main` whenever someone pushes a fix.

## Contents

- [What's inside](#whats-inside)
- [Install on a new computer](#install-on-a-new-computer)
  - [From Cowork (most users)](#from-cowork-most-users)
  - [From Claude Code CLI](#from-claude-code-cli)
  - [Fallback: drag-drop a single plugin](#fallback-drag-drop-a-single-plugin)
- [How we work together — handoff protocol](#how-we-work-together--handoff-protocol)
  - [The short version](#the-short-version)
  - [What syncs through Drive vs. what doesn't](#what-syncs-through-drive-vs-what-doesnt)
  - [Ending a session](#ending-a-session)
  - [Starting a session](#starting-a-session)
  - [Handoff frontmatter — author and baton-pass fields](#handoff-frontmatter--author-and-baton-pass-fields)
  - [Conflict rules](#conflict-rules)
  - [Beyond the marketplace — what else a new teammate needs](#beyond-the-marketplace--what-else-a-new-teammate-needs)
  - [Memory — per-Mac, per-user, and that's the right design](#memory--per-mac-per-user-and-thats-the-right-design)
  - [Failure modes](#failure-modes)
- [Updating](#updating)
- [Adding a new plugin](#adding-a-new-plugin)
- [Adding a new standalone skill](#adding-a-new-standalone-skill)
- [What is NOT in this marketplace (and why)](#what-is-not-in-this-marketplace-and-why)
- [Reserved-name note](#reserved-name-note)
- [Related](#related)

## What's inside

```
moxywolf-plugins/                       ← repo root (this is the marketplace root)
├── .claude-plugin/
│   └── marketplace.json                ← catalog (17 plugins)
├── README.md                            ← this file
├── plugins/                             ← 16 MoxyWolf-owned plugins
│   ├── board-deck/             0.3.0   PPTX board deck from LivePlan/GA4/Taskade/GitHub
│   ├── bibtex-builder/         0.1.0   Build + enrich BibTeX with AI-generated abstracts
│   ├── council/                0.7.0   Multi-model deliberation with vault-aware memory
│   ├── daily-ops/              1.4.0   Energy-aware standup/triage/review + fitness coach
│   ├── dev-infrastructure-skills/ 0.1.0  React/Next/Supabase/TDD/Playwright best practices
│   ├── editorial-forge/        0.1.0   AI content → author-owned via voice + DOB framing
│   ├── github-repo-analyzer/   0.5.0   Repo health, security issue review, PRD reverse-engineering, fix verification
│   ├── gstack-execution/       0.2.0   Code review, security audit, debug, QA, ship
│   ├── obsidian-update/        2.5.0   Vault-native personal OS + Council integration
│   ├── product-orchestrator/   0.3.0   Council-backed product scope/arch/GTM decisions
│   ├── project-init/           0.9.0   /init-project /session-start /session-end
│   ├── research-pipeline/      0.2.0   Literature discovery, verification, synthesis
│   ├── saas-frontend-designer/ 1.0.0   Next/React/Tailwind/shadcn SaaS UI pipeline
│   ├── saas-pricing-engine/    0.1.1   Pricing research, modeling, page copy
│   ├── team-kanban/            0.4.0   Slack Canvas kanban from Obsidian/GDrive/Cal/Gmail
│   └── vtt-to-text/            0.1.0   WebVTT captions → clean text
└── skill-bundles/
    └── moxywolf-skills/        1.1.0   25 standalone skills bundled as one plugin
```

The `moxywolf-skills` bundle contains: `moxywolf`, `voice-injection`, `stigviewer-content-ecosystem`, `sorkin-dob-weekly-blog`, `blog-content-ecosystem`, `market-awareness-analyzer`, `podcast-booking-ladder`, `birds-of-a-feather-outreach`, `linkedin-thought-leadership`, `linkedin-analytics`, `refinement-prompts`, plus the Anthropic reference skills (`artifacts-builder`, `canvas-design`, `brand-guidelines`, `theme-factory`, `code-review-pro`, `database-schema-designer`, `api-documentation-writer`, `technical-writer`, `mcp-builder`, `skill-creator`, `dev-create-orchestrator`, `dev-review-orchestrator`, `screenshot-to-code`, `color-palette-extractor`). The `daily-ops` skill that previously shipped here was moved out in v1.1.0 — install the standalone `daily-ops` plugin instead.

## Install on a new computer

### From Cowork (most users)

1. Open Cowork → **Personal plugins** → **+** → **Add marketplace**.
2. Paste:
   ```
   MoxyWolfLLC/moxywolf-plugins
   ```
3. Click **Sync**. The 17 plugins appear in the marketplace list.
4. Install each one you want (or all of them — the easy path).

### From Claude Code CLI

```bash
claude plugin marketplace add MoxyWolfLLC/moxywolf-plugins

# install everything in one go
for p in board-deck bibtex-builder council daily-ops dev-infrastructure-skills \
         editorial-forge github-repo-analyzer gstack-execution obsidian-update \
         product-orchestrator project-init research-pipeline saas-frontend-designer \
         saas-pricing-engine team-kanban vtt-to-text moxywolf-skills; do
  claude plugin install "$p@moxywolf-plugins"
done
```

### Fallback: drag-drop a single plugin

If you need a one-off install without adding the whole marketplace, build a `.plugin` zip from any plugin folder and drag it into Cowork's **Upload plugin** dialog. No auto-updates this way.

```bash
cd plugins
zip -r ../board-deck.plugin board-deck/
# then drag board-deck.plugin into Cowork → Personal plugins → + → Upload plugin
```

## How we work together — handoff protocol

The marketplace gets the plugins installed. The protocol below is how the MoxyWolf team (Dorian, Michael, Phil, Steven) hands work off across Macs, projects, and humans.

### The short version

1. Every project gets configured with `/init-project` once. That writes a `cowork-project-instructions.md` to the project's Drive folder.
2. At the end of every session, run `/session-end`. That writes a `cowork-session-handoff.md` to the same folder.
3. The next person to work on that project — same Mac, different Mac, different human — runs `/session-start [Project]` and Claude reads the handoff and briefs them.
4. Drive carries the protocol (instructions + handoff + vault knowledge). GitHub carries the code. Slack carries the "I'm picking this up now" ping.

### What syncs through Drive vs. what doesn't

| Thing | Lives in | Synced across the team? |
|---|---|---|
| Project Instructions, session handoff, decision records | Drive — project's `00 – Project Hub/` | Yes |
| Vault notes, kanban, daily journal | Drive — `MoxyWolf Vault/` | Yes |
| Plugin code (this repo) | GitHub | Yes (after marketplace update) |
| Repo working trees (`~/Documents/GitHub/<repo>`) | Local clone | **No — sync via `git push` / `git pull`** |
| Cowork plugin installs, mounted folders, MCP OAuth tokens, memory | Per Mac, per user | **No — each person sets up their own** |

Rule of thumb: if it's about a project's state, it's in Drive. If it's about how *your* Claude has learned to work with *you*, it's on your machine.

### Ending a session

1. **Commit and push** any code in `~/Documents/GitHub/<repo>`. Don't leave a working tree dirty; the next person can't `git pull` over it cleanly.
2. **Run `/session-end`.** Writes the handoff to Drive, refreshes writable repo READMEs against the canonical 16-section structure, optionally chains into `/obsidian-update` for vault knowledge capture.
3. **Ping in Slack** if you're explicitly handing off to a teammate. If you're just stopping for the day, no ping needed.

### Starting a session

1. **Confirm Drive sync is current.** Check the project folder's modification timestamp.
2. **`git pull`** on the repos the project's instructions list as active. Read-only repos: still pull, just don't push.
3. **`/session-start [Project]`.** Claude mounts the three roots, reads the handoff, briefs you.
4. **Read the "Procedural reminders for next-Claude" section.** That's where the previous session captured things like "the sandbox can't run tsx" or "this commit's title is cosmetically garbled, don't fix it." Skip it and you'll re-learn it the hard way.

### Handoff frontmatter — author and baton-pass fields

Every handoff carries `title`, `date`, `session_ended`, `project`, `type`, `status`, plus two team-handoff fields that `/session-end` (project-init ≥ v0.9.0) auto-writes:

- `author: dorian | michael | phil | steven` — who wrote this handoff
- `for: michael` *(optional)* — explicit baton-pass target. Omitted entirely when you're just stopping for the day.

How they get written:

- **Default flow** — `/session-end` asks two questions in a single prompt: *"Who authored this handoff?"* and *"Is this a baton-pass to a teammate, or are you just stopping for the day?"* The second question defaults to *"Just stopping for the day"* — answering it as-is writes no `for` field.
- **Flag overrides** — to skip the prompts, pass them inline:
  - `/session-end <project> --author=<name>` — skips the author question.
  - `/session-end <project> --handoff-to=<name>` — skips the baton-pass question; implies an active handoff.
  - `/session-end <project> --solo` — skips the baton-pass question and writes no `for:` field.
- **When `for` is set**, the wrap-up report ends with a one-line Slack-ping reminder: *"Baton passed to **[name]** — ping them in Slack so they know to pick this up."* Per "Ending a session" above, the Slack ping is required when handing off explicitly.

`/session-start` reads both fields and surfaces them in the briefing as an *Authored by …* line, with an "explicit baton-pass to …" suffix when `for` is present. Older handoffs without these fields fall back to "author unknown, no explicit baton-pass" — the briefing keeps working either way.

### Conflict rules

The handoff file is "last writer wins." With four people that's a real risk:

1. **One project, one active session at a time.** Check the handoff's `session_ended` timestamp and Slack before starting.
2. **Use `--archive`** on long-lived work. `/session-end --archive` keeps a dated copy in `00 – Project Hub/Session Handoffs/`.
3. **If you do overlap, reconcile in Slack — not in the handoff.** Two people editing the handoff in Drive produces a merge conflict nobody wants to resolve.

For genuinely parallel work — Dorian on Nexus, Michael on STIGViewer, Phil on SAMS, Steven on Nexus infrastructure — there's no conflict because the handoffs live in separate project folders.

### Beyond the marketplace — what else a new teammate needs

The marketplace install above is one of five setup steps. The rest:

- **Google Drive desktop client**, signed in as your `@moxywolf.com` account, with "Available offline" set on the projects you'll work on (otherwise reads through Cowork are slow).
- **`~/Documents/GitHub`** with clones of the repos the projects you'll touch need. For Nexus: `nexus-main` (read-only) + `lexicon-workbench` (read/write during Phase 2). For SAMS: ask Michael. Anyone editing plugins: this repo.
- **MCP OAuth** in Cowork → Connectors: Slack, Gmail, Calendar, GitHub, Supabase, Drive — each needs its own auth flow per Mac.
- **Claude in Chrome extension** installed and signed in — used by gstack-execution for browser QA, by `moxywolf-skills` for LinkedIn scraping, and by saas-pricing-engine for JS-rendered pricing pages.
- **`OPENROUTER_API_KEY`** env var set in your shell rc (`~/.zshrc` or `~/.bashrc`) for Council, research-pipeline, and product-orchestrator — ask Dorian for the team-shared key.

First-session test: run `/session-start Nexus` (or any initialized project). The briefing surfaces the missing piece by name if something isn't right.

### Memory — two layers: per-Mac for personal, Drive-shared for team-wide

There are two memory layers and they exist on purpose.

**Layer 1 — per-Mac, per-user (default).** Each Mac has its own memory directory at `~/Library/Application Support/Claude/.../memory/`. It holds `user_*` (facts about you), `feedback_*` (guidance you gave Claude), `project_*` (your slice of project work), and `reference_*` (where you keep things) memories. This layer **does not sync**. Dorian's "no em-dashes" preference is his, not Phil's. Michael's "verify handoff claims against git" was learned by his Claude through an incident his Claude saw. If this layer synced, every Claude would inherit every preference from every teammate and the model would slowly become a worst-common-denominator of everyone's quirks.

**Layer 2 — team-shared behavioral memory (Drive).** Some rules really should apply to everyone — e.g. "format GitHub Desktop commit messages as plain text, not markdown." Those live in:

```
Taskade/_Shared Files/_shared-memory/
├── INDEX.md
└── feedback_<rule>.md            ← one file per rule, frontmatter carries scope: team-shared
```

This directory is on the shared Drive, so every team member's Cowork session can read it. Files carry `scope: team-shared` in their frontmatter. The Taskade copy is the source of truth; a local mirror in your per-Mac memory is fine but the Taskade copy wins on conflict.

**Wiring each Mac to read it.** The vault's `CLAUDE.md` (in `MoxyWolf Vault/CLAUDE.md`) already instructs Claude to read `Taskade/_Shared Files/_shared-memory/INDEX.md` at session start — that covers any session run inside the vault. For sessions run **outside the vault** (plugin dev work in this repo, ad-hoc Claude Code sessions, etc.), each teammate needs to add the same instruction to their **user-level `~/.claude/CLAUDE.md`**:

```markdown
## Team-shared behavioral memory

At the start of every session, read the team-shared memory index at:

`~/Library/CloudStorage/GoogleDrive-<you>@moxywolf.com/Shared drives/MoxyWolf Shared Files/Taskade/_Shared Files/_shared-memory/INDEX.md`

Apply any rules listed there. They take precedence over local per-Mac memory when the two conflict. When the user gives behavioral feedback that should apply team-wide, write it to that directory (not just local memory) and add a one-line entry to its `INDEX.md`.
```

Substitute your own `@moxywolf.com` Google account in the path. If you've put your Drive mount somewhere non-default, fix the prefix accordingly.

**Promotion path — local rule → team rule.** When a feedback memory in your local store is something the whole team should follow (not a personal quirk), copy it into `Taskade/_Shared Files/_shared-memory/` with `scope: team-shared` in frontmatter, add a one-line entry to that directory's `INDEX.md`, and leave a pointer in your local memory. Conversely, durable *project* knowledge — decisions, research findings, conventions — still belongs in the vault, not memory; `/obsidian-update` is the right tool for that.

### Failure modes

**"No saved Project Instructions for [Project]"** — that project hasn't been initialized. Run `/init-project` first.

**Handoff is >14 days old** — `/session-start` flags it stale and falls back to kanban-driven priorities. Trust the kanban.

**Handoff says "uncommitted code" but git says you're clean** — the previous session pushed after the handoff was written. Skip the paste step.

**Plugin missing on your Mac** — install from this marketplace, retry the command.

**Drive sync lag** — wait or refresh Finder. "Available offline" makes this near-instant for files already opened locally.

**MCP server disconnected mid-session** — re-authorize in Cowork → Connectors. Don't try shell-call workarounds; the WebFetch / curl / requests fallbacks are deliberately disabled.

**Two people ran `/session-end` close together** — the second overwrote the first. Recover from `00 – Project Hub/Session Handoffs/` if `--archive` was used; otherwise from Drive's version history. Reconcile in Slack so it doesn't repeat.

## Updating

This repo is the **source of truth**. The flow is:

1. Edit a plugin in your local clone: `~/Documents/GitHub/moxywolf-plugins/plugins/<name>/`.
2. Bump the `version` in that plugin's `.claude-plugin/plugin.json`. Without a bump Cowork won't notice the change — the `version` field is what gates updates.
3. Commit and push via GitHub Desktop (or `git push`).
4. On every consumer machine, run `claude plugin marketplace update moxywolf-plugins`. Cowork has a **Refresh** button that does the same thing.

**Watch out for**: don't set `version` in both `plugin.json` and `marketplace.json`. The `plugin.json` value silently wins, so a stale manifest version will mask the bump you made in the catalog.

## Adding a new plugin

1. Drop the plugin folder into `plugins/<new-name>/`. It needs `.claude-plugin/plugin.json` at its root.
2. Add a matching entry to `.claude-plugin/marketplace.json` → `plugins[]`:
   ```json
   {
     "name": "new-name",
     "source": "./plugins/new-name",
     "description": "What it does",
     "version": "0.1.0",
     "author": { "name": "MoxyWolf LLC" },
     "category": "...",
     "keywords": ["..."]
   }
   ```
3. Clean noise: `find plugins/new-name -name .DS_Store -delete`.
4. Validate: `claude plugin validate .` (or `/plugin validate .` inside Claude Code).
5. Commit, push, done. Consumer machines pick it up on the next marketplace update.

## Adding a new standalone skill

1. Drop the skill folder into `skill-bundles/moxywolf-skills/skills/<new-skill>/` with a `SKILL.md` at root.
2. Bump `version` in `skill-bundles/moxywolf-skills/.claude-plugin/plugin.json`.
3. Commit, push. No marketplace.json edit needed — the bundle is already listed there.

## What is NOT in this marketplace (and why)

These plugins live on Dorian's source machine but are maintained by other authors and update on their own cadence. To install them, add their upstream marketplaces too:

| Plugin                      | Upstream                                              | Command                                                                |
| --------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------- |
| `productivity`              | `knowledge-work-plugins` (Anthropic)                  | `claude plugin marketplace add anthropics/knowledge-work-plugins`      |
| `slack-by-salesforce`       | `knowledge-work-plugins`                              | (same)                                                                 |
| `cowork-plugin-management`  | `knowledge-work-plugins`                              | (same)                                                                 |
| `growth-engineer-skills`    | user upload (`local-desktop-app-uploads`)             | Drag the `.plugin` zip into Cowork → Upload plugin                     |
| `linkedin-growth`           | user upload                                           | (same)                                                                 |
| `ui-ux-pro-max`             | third-party                                           | Find upstream Git URL and `marketplace add` it                         |

If you want to vendor any of them here too, drop them into `plugins/` and add the matching entry to `marketplace.json`.

## Reserved-name note

`knowledge-work-plugins` is a reserved marketplace name (Anthropic uses it). Our marketplace name is `moxywolf-plugins`, which is what users see in install paths like `board-deck@moxywolf-plugins`.

## Related

- [Anthropic docs: plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- DR-004 (in the MoxyWolf Vault) — original decision on the `.plugin` zip vs. directory format
