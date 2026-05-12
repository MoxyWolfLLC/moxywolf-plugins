# MoxyWolf Plugin Marketplace

Canonical home for every plugin authored by MoxyWolf LLC, plus a bundle of the standalone skills used across the team. Hosted as a Claude Code / Cowork marketplace at `github.com/MoxyWolfLLC/moxywolf-plugins`.

Adding this marketplace on any Mac gives that machine all 16 plugins in one shot, with updates flowing from `main` whenever someone pushes a fix.

## What's inside

```
moxywolf-plugins/                       ← repo root (this is the marketplace root)
├── .claude-plugin/
│   └── marketplace.json                ← catalog (16 plugins)
├── README.md                            ← this file
├── plugins/                             ← 15 MoxyWolf-owned plugins
│   ├── board-deck/             0.2.0   PPTX board deck from LivePlan/GA4/Taskade/GitHub
│   ├── bibtex-builder/         0.1.0   Build + enrich BibTeX with AI-generated abstracts
│   ├── council/                0.6.0   Multi-model deliberation with vault-aware memory
│   ├── daily-ops/              1.3.0   Energy-aware standup/triage/review + fitness coach
│   ├── dev-infrastructure-skills/ 0.1.0  React/Next/Supabase/TDD/Playwright best practices
│   ├── editorial-forge/        0.1.0   AI content → author-owned via voice + DOB framing
│   ├── gstack-execution/       0.1.0   Code review, security audit, debug, QA, ship
│   ├── obsidian-update/        2.4.0   Vault-native personal OS + Council integration
│   ├── product-orchestrator/   0.2.0   Council-backed product scope/arch/GTM decisions
│   ├── project-init/           0.8.0   /init-project /session-start /session-end
│   ├── research-pipeline/      0.1.0   Literature discovery, verification, synthesis
│   ├── saas-frontend-designer/ 1.0.0   Next/React/Tailwind/shadcn SaaS UI pipeline
│   ├── saas-pricing-engine/    0.1.0   Pricing research, modeling, page copy
│   ├── team-kanban/            0.4.0   Slack Canvas kanban from Obsidian/GDrive/Cal/Gmail
│   └── vtt-to-text/            0.1.0   WebVTT captions → clean text
└── skill-bundles/
    └── moxywolf-skills/        1.0.0   26 standalone skills bundled as one plugin
```

The `moxywolf-skills` bundle contains: `moxywolf`, `voice-injection`, `stigviewer-content-ecosystem`, `sorkin-dob-weekly-blog`, `blog-content-ecosystem`, `market-awareness-analyzer`, `podcast-booking-ladder`, `birds-of-a-feather-outreach`, `linkedin-thought-leadership`, `linkedin-analytics`, `daily-ops`, `refinement-prompts`, plus the Anthropic reference skills (`artifacts-builder`, `canvas-design`, `brand-guidelines`, `theme-factory`, `code-review-pro`, `database-schema-designer`, `api-documentation-writer`, `technical-writer`, `mcp-builder`, `skill-creator`, `dev-create-orchestrator`, `dev-review-orchestrator`, `screenshot-to-code`, `color-palette-extractor`).

## Install on a new computer

### From Cowork (most users)

1. Open Cowork → **Personal plugins** → **+** → **Add marketplace**.
2. Paste:
   ```
   MoxyWolfLLC/moxywolf-plugins
   ```
3. Click **Sync**. The 16 plugins appear in the marketplace list.
4. Install each one you want (or all of them — the easy path).

### From Claude Code CLI

```bash
claude plugin marketplace add MoxyWolfLLC/moxywolf-plugins

# install everything in one go
for p in board-deck bibtex-builder council daily-ops dev-infrastructure-skills \
         editorial-forge gstack-execution obsidian-update product-orchestrator \
         project-init research-pipeline saas-frontend-designer saas-pricing-engine \
         team-kanban vtt-to-text moxywolf-skills; do
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
