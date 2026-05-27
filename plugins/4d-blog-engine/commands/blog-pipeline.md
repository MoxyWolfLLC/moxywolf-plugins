---
description: Run the full 4D pipeline end-to-end — base document to publication-ready blog post + LinkedIn pair.
argument-hint: <path-or-url-to-base-doc> [--angle "<one-sentence question>"]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:blog-pipeline — end-to-end pipeline

Invoke the `4d-blog-engine` orchestrator skill in full-pipeline mode. The skill will:

1. Load `references/4d-discipline.md`, `references/ai-anti-patterns.md`, and the writer's voice profile at `<blog-project-dir>/<author-slug>-voice.md` (STEP 0). The voice profile is created by `/4d-blog-engine:blog-voice` — if it's missing, the orchestrator halts and points the user there before proceeding.
2. Detect the active Cowork project (walk up from CWD looking for `00 – Project Hub/cowork-project-instructions.md`) and compute the per-piece working directory at `<active-project>/12 – MARCOM/Posts/<YYYY-MM-DD-slug>/`. Report the resolved active project before doing anything else.
3. Run Phase 1 (Delegation) — capability triage, angle pick, earned-secret stall, modality decision. Writes `01-delegation.md`.
4. Run Phase 2 (Description) — 8-question voice interview, structure pick (Sorkin DOB default), outline with question-H2s and per-section evidence needs, At-a-Glance block. Writes `02-description.md`. Gate-checks with the user.
5. Run Phase 3 (Discernment) — invoke the `discourse-sweep` skill for the 30-day platform-targeted sweep; layer a `/council:deliberate` synthesis pass; build the bibliography via `bibtex-builder/bibtex-from-urls`; verify citations via `research-pipeline/citation-verifier`; draft via `research-pipeline/content-writer`; run `prose_lint.py` (Layer 1) + Tier-2 LLM scan; second-pass audit on the rewrite. Writes `03-discernment/*`.
6. Run Phase 4 (Diligence) — invoke the `release-owner-gate` skill: nonce rotation, hero image generation, BLOCKING reviewer subagent (restricted tools, no Bash, no Edit), preflight.py 5-stage gate, iteration loop (max 3 rounds), human Release Owner sign-off. Writes `04-diligence/blog.md` and the signed `changelog.md`.
7. On signature, invoke the `linkedin-deriver` skill to produce `04-diligence/linkedin-article.md` and `04-diligence/linkedin-teaser.md` with 3-axis scorecards.

**Arguments:**
- `$1` — the base document. Can be a file path (`.md`, `.txt`, `.pdf`, `.docx`), a URL, or "paste" to use content from a prior message.
- `--angle "<text>"` — optional. If omitted, Phase 1 will elicit the angle interactively.

The plugin never auto-commits, never auto-publishes, and never auto-signs the Release Owner gate. Those are human actions, by design.

Read `skills/4d-blog-engine/SKILL.md` for the full orchestration logic.
