---
name: linkedin-deriver
description: |
  This skill should be used when deriving the LinkedIn article + teaser pair from a Diligence-passed blog post in the 4D Blog Engine. It reads <piece>/04-diligence/blog.md (after the Release Owner has signed), pulls the angle and earned secret from 01-delegation.md, generates a full-mirror LinkedIn article (800-1200 words) plus a short hook-led teaser (~1,300 chars), runs scripts/linkedin_score.py for format compliance checks, and produces the 3-axis scorecard (thought leadership / pain / audience fit). Triggers: "/4d-blog-engine:blog-linkedin", "derive the LinkedIn pair", "write the LinkedIn version", "make the LinkedIn article and teaser". This is a specialist skill — invoked by the 4d-blog-engine orchestrator after the Release Owner Gate passes, not directly by the user in normal usage.
allowed-tools: [Read, Write, Edit, Bash, Glob, AskUserQuestion]
user-invocable: false
---

# LinkedIn Deriver — derive the article + teaser from a signed blog

> **Read this when:** Phase 4 (Diligence) just passed and the Release Owner signed the changelog. Your job is to produce `<piece>/04-diligence/linkedin-article.md` and `<piece>/04-diligence/linkedin-teaser.md` from the signed blog, then run format checks and the 3-axis scorecard.

## STEP 0 — Confirm the gate signed

Before generating anything, verify:

1. `<piece>/04-diligence/preflight-report.json` exists and `passed: true`.
2. `<piece>/changelog.md` exists and contains a line matching `^Verified — .+, \d{4}-\d{2}-\d{2}` dated today (or any past date).

If either check fails, **stop and report**: *"The Release Owner Gate has not been signed. Cannot derive LinkedIn output. Run /4d-blog-engine:blog-diligence first."*

## STEP 1 — Load the references and context

Read in order:

1. `${CLAUDE_PLUGIN_ROOT}/references/hook-library.md` — six named formulas with templates and hooks-to-retire.
2. `<piece>/04-diligence/blog.md` — the signed blog post (the canonical source for both LinkedIn artifacts).
3. `<piece>/01-delegation.md` — angle, audience persona, earned secret. The LinkedIn artifacts must lean MORE personal/opinion than the blog (per agricidaniel/claude-blog rule); the earned secret is the anchor for that personal weight.
4. `<piece>/02-description.md` — voice interview answers (carry the same voice into the LinkedIn pair).
5. **The writer's voice profile** — locate by walking up from `<piece>` to find `blog-project-instructions.md`, then resolve `<blog-project-dir>/<author-slug>-voice.md`. Re-load right before writing (per naveedharri's voice-drift-stop rule). If the voice profile is missing, halt with a pointer to `/4d-blog-engine:blog-voice`.

## STEP 2 — Generate 3 candidate hooks

Per `references/hook-library.md`, generate **3 distinct candidate hooks** for the teaser. Each must:

- Use a different named formula (Stat-Led / Question / Story / Contrarian / Bold Claim / Pattern Interrupt — pick the 3 best for this piece).
- Be a complete unit (no cliffhanger mid-sentence).
- Land before character 210 (the mobile fold).
- Carry a curiosity trigger — the reader should not be able to guess the next sentence.
- Avoid every hook on the "Hooks to retire" list.

Present all 3 to the user via `AskUserQuestion`, each option showing the formula name + the hook text. Mark your recommendation.

After the user picks, persist the choice in `linkedin-teaser.md`'s frontmatter (`hook_formula: <name>`).

## STEP 3 — Write the LinkedIn article (full mirror)

The article is a long-form LinkedIn post (LinkedIn Articles, not the feed). Targets:

- **Word count:** 800-1200 (shorter than the blog).
- **Tone:** MORE personal and opinion-led than the blog. The earned secret from Phase 1 anchors this — surface it explicitly within the first third of the article.
- **First 2-3 lines:** the "See more" hook (use a different hook formula than the teaser, or the same with a different framing). Never "I'm excited to share."
- **Formatting:** LinkedIn-native — bold for emphasis (sparingly), single-line paragraphs, generous whitespace, NO markdown tables (LinkedIn renders them as raw text), NO markdown bold-italic stacks.
- **Citations:** 2-3 sourced statistics carrying the FLOW evidence triple (year + publisher + URL).
- **External links:** zero in the body. The blog URL goes in the **first comment** (a posting metadata note records this).
- **Ending:** an engagement question — specific, not "What do you think?" or "Agree?"

Save to `<piece>/04-diligence/linkedin-article.md` with this frontmatter shape:

```yaml
---
type: linkedin-article
source_blog: <piece>/04-diligence/blog.md
hook_formula: <name>
audience: <persona from 01-delegation.md>
target_words: 1000
posting_notes:
  link_placement: first-comment
  hashtag_count_max: 5
  best_window: "Tue/Wed/Thu 7:30-8:30 AM PT"
---
```

## STEP 4 — Write the LinkedIn teaser

The teaser is a short feed post that drives traffic to the blog. Targets:

- **Char count:** 800-1500 (sweet spot ~1,300).
- **Word count:** ~150-280.
- **Hook:** the user-picked hook from STEP 2, landing complete before char 210.
- **Body structure:** 3 acts — `Hook → Stakes/Setup → Soft CTA`. One earned-secret-anchored line woven into the middle (one sentence, concrete, never a story arc — that's the article's job).
- **Closing line:** a specific question. Not "What do you think?" Not "Agree?" The question must name a specific concrete decision the reader would actually be facing.
- **Hashtags:** 0-3, at the very end after a line break.
- **No external links in body.** Blog URL goes in the first comment.

Save to `<piece>/04-diligence/linkedin-teaser.md` with the same frontmatter shape as the article, plus `type: linkedin-teaser`.

## STEP 5 — Format compliance check

Run the format checker against both files:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_score.py \
  --file <piece>/04-diligence/linkedin-article.md --type article \
  --out <piece>/04-diligence/linkedin-article.score.md

python3 ${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_score.py \
  --file <piece>/04-diligence/linkedin-teaser.md --type teaser \
  --out <piece>/04-diligence/linkedin-teaser.score.md
```

The script outputs a scorecard scaffold (with the 3-axis judgment scores empty) and a JSON sidecar with the deterministic findings. Exit code 1 means format checks failed — fix the issues (length, hook position, hashtag placement, external-link-in-body) and re-run. Don't proceed to STEP 6 until both files return exit code 0.

## STEP 6 — Fill in the 3-axis scorecard

The format checker produces a scaffold; you (the LLM) fill in the three /10 scores by judgment. For each axis:

- **Thought leadership /10** — Is the insight non-obvious enough that a senior practitioner would forward this to a peer? 10 = "I hadn't thought of it that way" reaction guaranteed. 5 = competent restatement of conventional wisdom. 0 = generic.
- **Pain (lands on the reader, not a third party) /10** — Does the pain in the post land on the reader's own job/identity/recent week, or on a third party they observe? 10 = the reader thinks "this is about me." 5 = the reader thinks "this is about someone I know." 0 = abstract pain on no one in particular.
- **Audience fit /10** — Does the post speak to the audience persona declared in `01-delegation.md`, using their vocabulary, problem frame, and decision context? 10 = pitch-perfect for the named persona. 5 = generic-marketer voice. 0 = wrong audience entirely.

Fill in both scaffold files. Each score needs a **one-sentence justification** — write specifically, not generically ("Score 8 because the post anchors the earned secret to a Maya-class founder's board context, but the third paragraph drifts into industry-analyst voice").

Recommendation: ship if all three axes ≥ 7. Revise if any axis is 4-6. Discard if any axis is ≤ 3.

## STEP 7 — Update state and report

Append to `<piece>/state.md`:

```
- [x] LinkedIn pair derived
```

And to the process log: `<ISO> — LinkedIn pair derived; article <words>w, teaser <chars>ch; axes <T>/10, <P>/10, <A>/10.`

Report to the user:

```
LinkedIn pair derived.

Article: <piece>/04-diligence/linkedin-article.md (<words> words)
Teaser:  <piece>/04-diligence/linkedin-teaser.md (<chars> chars)
Scorecard: <piece>/04-diligence/linkedin-{article,teaser}.score.md
  Thought leadership: <T>/10
  Pain (on reader):   <P>/10
  Audience fit:       <A>/10
  Recommendation:     ship | revise | discard

Reminders:
  - Post the BLOG URL in the FIRST COMMENT after you publish, not in the body.
  - Best posting window: Tue/Wed/Thu, 7:30-8:30 AM PT.
  - The plugin does NOT auto-publish. Paste and post by hand.
```

## What this skill does NOT do

- It does NOT modify the signed blog. The blog is canonical and read-only after the Release Owner signs.
- It does NOT publish to LinkedIn. The user pastes the artifacts by hand. This is intentional — see the whitepaper's Diligence ethos.
- It does NOT generate carousels, video clips, or infographics — that's `blog-content-ecosystem`'s scope. The LinkedIn pair (article + teaser) is the scope of this skill.

## Degradation behaviors

- **linkedin_score.py fails to run** (Python error): treat as a script bug and surface it; fall back to the format rules in `references/hook-library.md` (char count, hook position, hashtag count) checked manually.
- **User picks `[skip hook selection]`:** generate the recommended hook automatically but flag in the teaser's frontmatter that the human did not pick.
- **The signed blog uses an angle that won't compress to LinkedIn (too technical, too long, no clear hook)**: surface the issue ("the source post's argument doesn't compress to LinkedIn's format constraints — recommend revising the source angle, not the LinkedIn version"). Do not force-fit.
