---
description: Derive social-platform posts (LinkedIn pair, Twitter thread, Facebook post) from a Diligence-signed blog.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:blog-social — multi-platform social derivatives from a signed blog

Invoke the `4d-blog-engine` orchestrator skill and run the social-derivation step on an existing Phase-4-signed piece.

**Argument:** `<piece-slug>` — the per-piece directory. If omitted, picks the most-recently-modified piece whose Release Owner Gate has passed AND signed (`changelog.md` contains a `Verified — <initials>, <date>` line).

**Refuses to run if:**

- `<piece>/04-diligence/preflight-report.json` doesn't show `passed: true`.
- `<piece>/changelog.md` doesn't contain a `Verified — …` line.

Hands off **entirely** to the `blog-social` skill. That skill:

1. Loads `references/hook-library.md` (six named formulas + per-platform formula-fit table) and the writer's voice profile.
2. Reads the signed blog at `<piece>/04-diligence/blog.md`, the angle and earned secret at `<piece>/01-delegation.md`, the voice interview at `<piece>/02-description.md`.
3. **Asks the writer which platforms to derive** via `AskUserQuestion` (multiSelect): LinkedIn pair, Twitter (X) thread, Facebook post. The writer picks one, two, or all three.
4. Generates **3 hook candidates per platform** from the formula library. The writer picks one per platform.
5. Applies **per-platform register shifts** — same voice, different tone per platform (LinkedIn professional; Twitter compressed and declarative; Facebook warmer/conversational).
6. Writes the selected outputs into `<piece>/04-diligence/social/`:
   - **`linkedin-article.md`** — 800-1200 words, more personal/opinion than the blog, hook in first 2-3 lines, LinkedIn-native formatting, blog URL goes in the first comment.
   - **`linkedin-teaser.md`** — ~1,300 chars, hook before character 210, earned-secret line in the middle, specific closing question.
   - **`twitter-thread.md`** — 5-10 connected posts as `## Post 1` / `## Post 2` / … blocks. Each post ≤280 chars (hard cap, script-enforced). Post 1 is the hook; Post N closes with the blog URL + ≤2 hashtags.
   - **`facebook-post.md`** — single post 300-500 chars (sweet spot), blog URL allowed in body (FB renders a preview card), warmer register than LinkedIn.
7. Runs `scripts/social_score.py` per file for deterministic format compliance — length bands, hook position, per-post char limits (Twitter), hashtag rules, link placement, banned-hook check.
8. LLM-fills a **3-axis scorecard per platform** (thought leadership /10, pain /10, audience fit /10), each with a one-sentence justification, saved under `<piece>/04-diligence/social/scorecards/`.
9. Surfaces all scorecards and a `ship | revise | discard` recommendation per platform.

**Reminders the skill prints when handing back to the writer:**

- **LinkedIn:** post the BLOG URL in the **first comment** after publishing, never in the body. LinkedIn deprioritizes link posts by ~25-60% reach. Best window: Tue/Wed/Thu, 7:30-8:30 AM PT.
- **Twitter:** blog URL goes in the **final post** of the thread. Best window: Tue/Wed/Thu, 9:00-11:00 AM PT.
- **Facebook:** blog URL goes in the **body** (FB renders a preview card — this is the only platform where the link belongs inline). Best window: weekdays 1:00-3:00 PM PT.
- The plugin does NOT auto-publish on any platform. Paste and post by hand.

Read `skills/blog-social/SKILL.md` and `references/hook-library.md` for the full workflow.
