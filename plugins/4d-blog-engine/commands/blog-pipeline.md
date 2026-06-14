---
description: Run the full 4D pipeline end-to-end — base document to publication-ready blog post. Social derivatives (LinkedIn / Twitter / Facebook) are opt-in via /blog-social after sign-off.
argument-hint: <path-or-url-to-base-doc> [--angle "<one-sentence question>"]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:blog-pipeline — end-to-end pipeline

Invoke the `4d-blog-engine` orchestrator skill in full-pipeline mode. The skill will:

1. Load `references/4d-discipline.md`, `references/ai-anti-patterns.md`, and the writer's voice profile at `<blog-project-dir>/<author-slug>-voice.md` (STEP 0). The voice profile is created by `/4d-blog-engine:blog-voice` — if it's missing, the orchestrator halts and points the user there before proceeding.
2. Detect the active Cowork project (walk up from CWD looking for `00 – Project Hub/cowork-project-instructions.md`) and compute the per-piece working directory at `<active-project>/12 – MARCOM/Posts/<YYYY-MM-DD-slug>/`. Report the resolved active project before doing anything else.
3. Choose the publishing **target** and the **pillar** (STEP 1.5). Ask which target (`targets/*.md`) and which folder, then **new pillar or existing pillar** — mandatory; every post is a spoke on exactly one pillar. New pillars get a linking map from `references/linking-map-template.md`. Record `target` + `pillar` (+ `hub_url`) to `state.md`. For a `register-only` target, surface the descriptor's site-side checklist now.
4. Run Phase 1 (Delegation) — capability triage, angle pick, earned-secret stall, modality decision. Writes `01-delegation.md`.
5. Run Phase 2 (Description) — 8-question voice interview, structure pick (Sorkin DOB default), outline with question-H2s and per-section evidence needs, At-a-Glance block. Writes `02-description.md`. Gate-checks with the user.
6. Run Phase 3 (Discernment) — invoke the `discourse-sweep` skill for the 30-day platform-targeted sweep; layer a `/council:deliberate` synthesis pass; build the bibliography via `bibtex-builder/bibtex-from-urls`; verify citations via `research-pipeline/citation-verifier`; draft via `research-pipeline/content-writer`; run `prose_lint.py` (Layer 1) + Tier-2 LLM scan; second-pass audit on the rewrite. Ensure the pillar's hub term appears so the spoke→hub link wires. Writes `03-discernment/*`.
7. Run Phase 4 (Diligence) — invoke the `release-owner-gate` skill: nonce rotation, hero image generation, BLOCKING reviewer subagent (restricted tools, no Bash, no Edit), preflight.py 5-stage gate, iteration loop (max 3 rounds), human Release Owner sign-off. Registers the spoke in the pillar's linking map. Writes `04-diligence/blog.md` and the signed `changelog.md`.
8. On signature, the pipeline ends with the blog signed and staged to `<blog-project-dir>/drafts/<slug>.md`. It surfaces the writer's next-step options — `/4d-blog-engine:blog-publish` to ship the post, and `/4d-blog-engine:blog-social` (opt-in) to derive social posts for any subset of LinkedIn (article + teaser), Twitter (X) (5-10 post thread), and Facebook (single post). Social derivation is **not** auto-invoked.

**Arguments:**
- `$1` — the base document. Can be a file path (`.md`, `.txt`, `.pdf`, `.docx`), a URL, or "paste" to use content from a prior message.
- `--angle "<text>"` — optional. If omitted, Phase 1 will elicit the angle interactively.

The plugin never auto-commits, never auto-publishes, never auto-signs the Release Owner gate, and never auto-derives social posts. Those are human actions, by design.

Read `skills/4d-blog-engine/SKILL.md` for the full orchestration logic.
