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
3. **Asks the writer which platforms to derive** via `AskUserQuestion` (multiSelect): LinkedIn Post + first comment (recommended default), LinkedIn Article (long-form, optional separate selection), Twitter (X) thread, Facebook post. The writer picks any combination.
4. Generates **3 hook candidates per content platform** from the formula library. The writer picks one per platform. (The first-comment file is utilitarian — no hook selection.)
5. Applies **per-platform register shifts** — same voice, different tone per platform (LinkedIn Post/Article professional; first comment voice-off and utilitarian; Twitter compressed and declarative; Facebook warmer/conversational).
6. Writes the selected outputs into `<piece>/04-diligence/social/`:
   - **`linkedin-post.md`** — feed Post, 1,300-2,500 chars sweet spot, **2,900 hard cap** (LinkedIn rejects >3,000). Hook before character 210. NO body links. Earned-secret line in the middle. Specific closing question.
   - **`linkedin-first-comment.md`** — companion to the Post. Fixed opening line "If you want to do your own research, here are the cited sources in my article:", then the blog URL and the 2-3 sources the Post text quotes inline. Bare URLs only (LinkedIn comments render as plain text). 80-1,200 chars.
   - **`linkedin-article.md`** — optional long-form, only produced if "LinkedIn Article" was selected. 800-1200 words, more personal/opinion than the blog, inline citations allowed (the Article surface isn't penalized like the Post).
   - **`twitter-thread.md`** — 5-10 connected posts as `## Post 1` / `## Post 2` / … blocks. Each post ≤280 chars (hard cap, script-enforced). Post 1 is the hook; Post N closes with the blog URL + ≤2 hashtags.
   - **`facebook-post.md`** — single post 300-500 chars (sweet spot), blog URL allowed in body (FB renders a preview card), warmer register than LinkedIn.
7. Runs `scripts/social_score.py` per file for deterministic format compliance — length bands (including the 2,900-char hard cap on the Post), hook position, per-post char limits (Twitter), hashtag rules, link placement, URL-required for first-comment, banned-hook check.
8. LLM-fills a **3-axis scorecard per content artifact** (thought leadership /10, pain /10, audience fit /10), each with a one-sentence justification, saved under `<piece>/04-diligence/social/scorecards/`. The first-comment file gets a deterministic-check-only scorecard (no 3-axis scoring — it's a service payload, not voice prose).
9. Surfaces all scorecards and a `ship | revise | discard` recommendation per content artifact.

**Reminders the skill prints when handing back to the writer:**

- **LinkedIn Post:** paste the Post body first with NO link in the body. As soon as it publishes, paste the contents of `linkedin-first-comment.md` as the FIRST COMMENT under the post (under your own handle). The first comment is what carries the blog URL and source citations. LinkedIn deprioritizes link-in-body posts by ~25-60% reach. Best window: Tue/Wed/Thu, 7:30-8:30 AM PT.
- **LinkedIn Article (if produced):** published via the "Write article" path — a separate LinkedIn surface that gets its own URL and is indexed by Google. Inline links are fine here.
- **Twitter:** blog URL goes in the **final post** of the thread. Best window: Tue/Wed/Thu, 9:00-11:00 AM PT.
- **Facebook:** blog URL goes in the **body** (FB renders a preview card — this is the only platform where the link belongs inline). Best window: weekdays 1:00-3:00 PM PT.
- The plugin does NOT auto-publish on any platform. Paste and post by hand.

**To ship the social files to your repo** (so a teammate or downstream distribution automation can read them from GitHub), run `/4d-blog-engine:blog-publish <slug>` after `/blog-social` finishes. The publish skill detects the new `social/` directory and includes the .md files + scorecards in the same commit as the post. If the post was already published before social existed, this re-publish ships just the social bundle plus a `dateModified` bump on the post.

Read `skills/blog-social/SKILL.md` and `references/hook-library.md` for the full workflow.
