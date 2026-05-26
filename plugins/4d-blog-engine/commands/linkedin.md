---
description: Derive the LinkedIn article (full mirror) + short hook-led teaser from a Diligence-passed blog.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:linkedin — LinkedIn pair from a signed blog

Invoke the `4d-blog-engine` orchestrator skill and run the LinkedIn derivative step on an existing Phase-4-signed piece.

**Argument:** `<piece-slug>` — the per-piece directory. If omitted, picks the most-recently-modified piece whose Release Owner Gate has passed AND signed (`changelog.md` contains a `Verified — <initials>, <date>` line).

Refuses to run if:
- `<piece>/04-diligence/preflight-report.json` doesn't show `passed: true`.
- `<piece>/changelog.md` doesn't contain a `Verified — …` line.

Hands off **entirely** to the `linkedin-deriver` skill. That skill:

1. Loads `references/hook-library.md` and the voice anchor.
2. Reads the signed blog at `<piece>/04-diligence/blog.md`, the angle and earned secret at `<piece>/01-delegation.md`, the voice interview at `<piece>/02-description.md`.
3. Generates **3 distinct hook candidates** from the named-formula library (Stat-Led / Question / Story / Contrarian / Bold Claim / Pattern Interrupt). User picks one via `AskUserQuestion`.
4. Writes the **LinkedIn article** — 800-1200 words, MORE personal/opinion than the blog, hook in first 2-3 lines, LinkedIn-native formatting, 2-3 sourced stats with FLOW triples, **no external links in body** (blog URL goes in the first comment). Saved to `<piece>/04-diligence/linkedin-article.md`.
5. Writes the **LinkedIn teaser** — ~1,300 chars, hook landing before character 210, earned-secret-anchored line in the middle, ending with a specific question (never "What do you think?" or "Agree?"). Saved to `<piece>/04-diligence/linkedin-teaser.md`.
6. Runs `scripts/linkedin_score.py` on both files for format compliance — char count band, hook position, hashtag rules, link placement, banned-hook check.
7. LLM-fills the **3-axis scorecard** (thought leadership /10, pain /10, audience fit /10), each with a one-sentence justification.
8. Surfaces the scorecards and a `ship | revise | discard` recommendation.

**Reminders the skill prints when handing back to the user:**

- Post the BLOG URL in the **first comment** after publishing — never in the body. LinkedIn deprioritizes link posts by ~25-60% reach.
- Best posting window: Tue/Wed/Thu, 7:30-8:30 AM PT.
- The plugin does NOT auto-publish. Paste and post by hand.

Read `skills/linkedin-deriver/SKILL.md` and `references/hook-library.md` for the full workflow.
