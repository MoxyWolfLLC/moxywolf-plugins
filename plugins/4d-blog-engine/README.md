# 4D Blog Engine

A Cowork plugin that turns a base document into a publication-ready blog post, a long-form LinkedIn article, and a short hook-led LinkedIn teaser — under the four-D discipline from MoxyWolf's *Beyond the Prompt* whitepaper.

The whitepaper's claim: the company that wins the AI era isn't the one with the best models or the best prompts; it's the one built so human judgment is the thing it scales. The 4D AI Fluency Framework — Delegation, Description, Discernment, Diligence — is how that judgment gets engineered into the workflow rather than left as good intentions. This plugin is that framework, applied to content.

## What it does

Given a base document (uploaded file or referenced URL) and an angle or question chosen by the author, the plugin runs four phases:

- **Delegation** — Triages whether the topic warrants a post. Picks the angle from 3-5 candidates. Forces you to name the "earned secret" — something from direct experience the audience doesn't have. Stalls if you can't.
- **Description** — Runs the per-post 8-question voice interview (Trigger / Evidence / Contrarian Take / Authority / Specific Reader / Business Connection / Call to Action / Emotional Core). Loads the writer's standing voice profile from `<blog-project-dir>/<author-slug>-voice.md` (created once via `/4d-blog-engine:blog-voice`). Lays out structure (Sorkin DOB by default), per-section word budget, the "At a Glance" 60-90 word AI-citation block, and the AEO-shaped outline.
- **Discernment** — Runs a 30-day discourse sweep across reddit, X, Hacker News, Substack, Facebook, Quora, podcasts, and academic sources. Layers a `/council:deliberate` synthesis pass to separate consensus from noise. Builds a verified bibliography with AI-generated abstracts via `bibtex-builder`. Drafts the post in the writer's voice (from `<author-slug>-voice.md`) via `research-pipeline/content-writer`. Runs a two-tier anti-AI-slop pass (deterministic linter + LLM structural review). Runs a second-pass audit on the rewrite to catch survivors.
- **Diligence** — The Release Owner Gate: a nonce-bound 5-stage contract scored against a 100-point rubric. A BLOCKING reviewer agent must echo a CSPRNG nonce verbatim and end its verdict with `BLOCKING: true|false (reason)`. Only on a clean gate does the plugin generate the LinkedIn article (full mirror, blog stays canonical) plus a short hook-led teaser, each with a 3-axis scorecard (thought leadership / pain / audience fit). The Release Owner signs the changelog by hand. Nothing auto-publishes.

## Commands

**Lifecycle** (run these to set up and resume blog work):

| Command | What it does |
|---|---|
| `/4d-blog-engine:blog-init` | One-time setup — two folder picks, author name, hero vibe, optional live URL. Writes `blog-project-instructions.md`. |
| `/4d-blog-engine:blog-voice` | Voice capture — 8-question interview that produces `<author-slug>-voice.md`. Run more than once for additional authors (guest contributors, co-writers). The pipeline globs `*-voice.md` and asks which voice to use when multiple exist. |
| `/4d-blog-engine:blog-start` | Open or resume a session — mounts the blog project dir + GitHub repo, surfaces in-progress and unpublished pieces, proposes the next step. |
| `/4d-blog-engine:publish <slug>` | Ship a signed post to your live site. Copies the post + hero into the GitHub repo, commits, and pushes — no git words required from the writer. |

**Pipeline** (run these to actually write a post):

| Command | What it does |
|---|---|
| `/4d-blog-engine:blog <base-doc> [--angle "..."]` | Runs the full 4-phase pipeline end-to-end |
| `/4d-blog-engine:delegate` | Phase 1 only — triage, angle pick, earned-secret stall |
| `/4d-blog-engine:describe` | Phase 2 only — voice interview, structure, outline |
| `/4d-blog-engine:discern` | Phase 3 only — discourse sweep + draft + slop pass |
| `/4d-blog-engine:diligence` | Phase 4 only — Release Owner Gate against an existing draft |
| `/4d-blog-engine:linkedin` | Derive the LinkedIn article + teaser from a Diligence-passed blog |
| `/4d-blog-engine:status` | Print the current piece's phase, gates passed, next step |

## Working directory layout

The plugin saves into the **active project's** directory under a standardized structure. The active project is auto-detected by walking up from CWD looking for one of two marker files (MoxyWolf-internal marker first):

- **MoxyWolf-internal:** `00 – Project Hub/cowork-project-instructions.md` → pieces land at `<project>/12 – MARCOM/Posts/<slug>/`
- **External blog (slim):** `blog-project-instructions.md` at the project root, created by `/4d-blog-engine:blog-init` → pieces land at `<project>/Posts/<slug>/`

If neither is found, the plugin falls back to `~/4d-blog-engine-work/` and recommends running `/4d-blog-engine:blog-init`.

The per-piece directory layout is the same regardless of mode:

```
<posts-dir>/<YYYY-MM-DD-slug>/
├── state.md                          # current_phase, gates_passed, target_words, modality
├── 01-delegation.md                  # base doc, angle, earned secret, audience persona
├── 02-description.md                 # voice interview answers, outline, At-a-Glance block
├── 03-discernment/
│   ├── discourse.md                  # 30-day sweep, ranked + themed
│   ├── draft.md                      # MoxyWolf-voice draft with FLOW citations
│   ├── bibliography.bib              # bibtex-builder output, abstracts included
│   ├── sources-verification.md       # [V]/[S]/[F]-tagged sources
│   ├── slop-findings.md              # first-pass slop linter output
│   └── slop-findings-pass2.md        # second-pass audit (survivors)
├── 04-diligence/
│   ├── blog.md                       # publish-ready blog post + JSON-LD schema
│   ├── linkedin-article.md           # 800-1200w full mirror
│   ├── linkedin-teaser.md            # ~1,300-char hook-led teaser
│   ├── linkedin-scorecards.md        # 3-axis: thought leadership / pain / audience fit
│   ├── og-hero.png                   # 16:9 brand-aligned hero
│   ├── og-hero-prompt.md             # AI-transparency prompt artifact
│   └── release-owner.signed.md       # the audit trail
├── .review-nonce                     # CSPRNG, fresh per Diligence pass
└── changelog.md                      # Verified — <initials>, <YYYY-MM-DD>
```

## Reuse vs new

The plugin is **mostly composition** over existing MoxyWolf plugins. It calls:

- `research-pipeline/content-writer` — voice interview + Sorkin DOB drafting + Chicago bibliography
- `research-pipeline/literature-discovery` — academic search (OpenAlex, Semantic Scholar, arXiv)
- `research-pipeline/citation-verifier` — 4-layer citation verification
- `bibtex-builder/bibtex-from-urls` — bibliography with AI-generated abstracts
- `blog-voice` (in this plugin) — 8-question voice interview, produces `<author-slug>-voice.md`
- `council/deliberate` — multi-model synthesis on the discourse harvest
- Any connected image-generation MCP (Krea, HuggingFace Spaces, Gemini, etc.) — hero image generation, with the brand-style spec read from each project's `blog-project-instructions.md`
- Writer's voice anchor: `<blog-project-dir>/<author-slug>-voice.md` (per-writer, produced by `/4d-blog-engine:blog-voice`)

What's genuinely new in this plugin: the 30-day discourse sweep (`scripts/discourse_sweep.py` + `skills/discourse-sweep/`), the engineered Release Owner Gate (`scripts/preflight.py` + `scripts/prose_lint.py` + the BLOCKING reviewer sub-agent), the 3-axis LinkedIn scorecard, the AEO checklist, and the orchestrator that sequences everything under the 4D discipline.

## Important rules

- **Plugin never auto-publishes to LinkedIn.** It writes the article and teaser to disk; you paste / use Buffer / use the LinkedIn editor.
- **Plugin never fabricates citations.** Unverified data gets `[CITATION NEEDED]` placeholders, not invented text.
- **The Release Owner Gate is load-bearing.** Disabling it or auto-passing it defeats the whole framework. The whole point of the plugin is that one named human signs for every AI output before it ships.
- **Publishing is one explicit command, not automatic.** `/4d-blog-engine:publish <slug>` is the only path that touches the GitHub repo. It refuses to run on an unsigned piece. The MoxyWolf-internal one-aggregated-commit-per-push workflow still applies if you're committing other repo changes outside of `/publish`.

## Install

This plugin lives in the `moxywolf-plugins` marketplace.

**In Claude Cowork:**

1. Open **Browse plugins** from the sidebar.
2. Switch to the **Personal** tab.
3. Click **Add Marketplace** and paste: `MoxyWolfLLC/moxywolf-plugins`.
4. Find **4d-blog-engine** in the listed plugins and click **Install**.

**In Claude Code CLI:**

```bash
claude plugin marketplace add MoxyWolfLLC/moxywolf-plugins
claude plugin install 4d-blog-engine@moxywolf-plugins
```

After install, run `/4d-blog-engine:blog-init` once to set up your blog project. After that, `/4d-blog-engine:blog-start` opens any future session and `/4d-blog-engine:publish` ships finished posts.

## Source

- Architecture doc: `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/release-owner-plugin-architecture-2026-05-25.md`
- Research synthesis: `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/blog-linkedin-tooling-findings-2026-05-25.md`
- Build log: `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/release-owner-plugin-build-log-2026-05-25.md`
- Whitepaper: `Taskade/Frontier Founder/11 - Project Knowledge/Papers/Beyond the Prompt – Editorial Forge/04-whitepaper/Beyond the Prompt - MoxyWolf Whitepaper.docx`
