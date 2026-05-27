---
name: blog-social
description: |
  This skill should be used when deriving social-platform posts from a Diligence-passed blog in the 4D Blog Engine, or whenever the writer runs /4d-blog-engine:blog-social. Supports LinkedIn (feed Post + companion first-comment, with optional long-form Article), Twitter/X (5-10 post thread, ≤280 chars per post), and Facebook (single ~300-500 char post). The writer picks which platforms to derive — nothing is auto-invoked at Phase 4 sign-off. Reads <piece>/04-diligence/blog.md plus 01-delegation.md (angle + earned secret) and the writer's voice profile, applies per-platform register shifts, generates platform-appropriate hooks, runs scripts/social_score.py for format-compliance checks, and produces per-platform 3-axis scorecards. Outputs land in <piece>/04-diligence/social/. Triggers: "/4d-blog-engine:blog-social", "/blog-social", "derive the LinkedIn post", "derive the LinkedIn article", "make the Twitter thread", "write a Facebook post from this", "social derivatives".
allowed-tools: [Read, Write, Edit, Bash, Glob, AskUserQuestion]
---

# Blog Social Deriver — multi-platform social derivatives from a signed blog

> **Read this when:** Phase 4 (Diligence) has signed off and the writer wants to derive social-platform posts. Your job is to produce one or more of: `<piece>/04-diligence/social/linkedin-post.md` (+ its companion `linkedin-first-comment.md`), `<piece>/04-diligence/social/linkedin-article.md` (optional long-form), `<piece>/04-diligence/social/twitter-thread.md`, `<piece>/04-diligence/social/facebook-post.md` — based on which platforms the writer picks.

## Why LinkedIn produces two files

LinkedIn's algorithm deprioritizes posts that contain outbound links (the platform wants readers staying in the feed). The workaround everyone in the field uses is to paste substantive content directly into the **Post** body — no links — and put the link plus source citations in the **first comment** under the post. That's why this skill produces a Post / first-comment **pair** as the LinkedIn default, not a single artifact. The optional long-form Article (the "Write article" path) is a separate publishing surface — different button on LinkedIn, different URL, far less reach per piece, but indexed by Google and permanent on the writer's profile. Most writers only need the Post + first-comment.

## STEP 0 — Confirm the gate signed

Before generating anything, verify:

1. `<piece>/04-diligence/preflight-report.json` exists and `passed: true`.
2. `<piece>/changelog.md` exists and contains a line matching `^Verified — .+, \d{4}-\d{2}-\d{2}`.

If either check fails, **stop and report**: *"The Release Owner Gate has not been signed. Cannot derive social posts. Run /4d-blog-engine:blog-diligence first."*

## STEP 1 — Load references and context

Read in order:

1. `${CLAUDE_PLUGIN_ROOT}/references/hook-library.md` — six named hook formulas plus the per-platform formula-fit table.
2. `<piece>/04-diligence/blog.md` — the signed blog post (canonical source for every social artifact).
3. `<piece>/01-delegation.md` — angle, audience persona, earned secret. Social posts must lean MORE personal/opinion than the blog; the earned secret anchors that personal weight on every platform.
4. `<piece>/02-description.md` — voice interview answers (same voice carries across all platforms).
5. **The writer's voice profile** — locate by walking up from `<piece>` to find `blog-project-instructions.md`, then resolve `<blog-project-dir>/<author-slug>-voice.md`. If multiple `*-voice.md` files exist, use the same voice the blog was written in (the orchestrator state file records this in `<piece>/state.md` under `voice:`). Re-load right before writing each platform's output. If no voice profile is found, halt with a pointer to `/4d-blog-engine:blog-voice`.

## STEP 2 — Ask the writer which platforms to derive

Use `AskUserQuestion` (multiSelect: true) with options:

- **LinkedIn Post + first comment** — feed Post (1,300-2,500 chars sweet spot; 2,900 hard cap) plus its companion first-comment file carrying the blog URL and the 2-3 sources the Post quotes inline. This is the primary LinkedIn surface. (Recommended)
- **LinkedIn Article (long-form)** — separate from the Post. Long-form article (800-1200 words) published via LinkedIn's "Write article" path. Gets a stable URL, indexed by Google, lives on the writer's profile. Lower initial reach than a Post, longer shelf life. Pick this in addition to the Post if the piece warrants both surfaces.
- **Twitter (X) thread** — 5-10 connected posts, each ≤280 chars. Post 1 is the hook; Post N closes with the blog URL + ≤2 hashtags.
- **Facebook post** — single post, 300-500 chars sweet spot, blog URL allowed inline (Facebook renders a preview card).

The writer can pick any combination. If they pick nothing, halt with: *"No platforms selected; nothing to derive."*

**Note on the LinkedIn pair:** if the writer selects "LinkedIn Post + first comment", you produce TWO files (`linkedin-post.md` AND `linkedin-first-comment.md`) — never one without the other. The first comment is what makes the no-body-link post-format strategy work; producing the Post without the first comment leaves the writer without the source-and-link payload to paste into the comment box after publishing.

Create the output directory if it doesn't exist:

```bash
mkdir -p <piece>/04-diligence/social/scorecards
```

## STEP 3 — Generate per-platform hook candidates

For each platform the writer selected, generate **3 candidate hooks** using formulas from `references/hook-library.md`. The per-platform formula-fit table in that file indicates which formulas land best where:

- **LinkedIn Post** — Stat-Led, Story (single-line), Contrarian work best. If Article is also selected for this piece, use a different formula on the Post than the Article so the two surfaces don't read as duplicates.
- **LinkedIn first comment** — no hook is generated. The first comment is a utilitarian payload (intro line + URL + cited sources), not a content artifact. Skip hook selection for this file.
- **LinkedIn Article** — Story, Pattern Interrupt, Bold Claim work for long-form openers.
- **Twitter Post 1** — Stat-Led, Pattern Interrupt, Question lead the thread. Must fit ≤260 chars (leave room for "🧵" or "1/").
- **Facebook** — Story (one-line), Question, Stat-Led. FB's audience tolerates conversational warmth better than LinkedIn.

Each hook must:

- Use a named formula from the library.
- Be a complete unit (no cliffhanger mid-sentence).
- Land before character 210 for LinkedIn / Facebook, or fit ≤260 chars for Twitter Post 1.
- Carry a curiosity trigger — the reader cannot guess the next sentence.
- Avoid every hook on the "Hooks to retire" list.

Present hooks to the writer via `AskUserQuestion` — one question per platform, each option showing `<formula name>: <hook text>`. Mark your recommendation. After the writer picks, persist the choice in the platform's frontmatter (`hook_formula: <name>`).

## STEP 4 — Per-platform register shifts (voice continuity, platform tone)

The voice profile is the anchor — every platform sounds like the same writer. But each platform has a register the voice should bend toward:

- **LinkedIn Article (long-form)** — closest to blog voice. Slightly more first-person, opinion-led. Surface the earned secret in the first third.
- **LinkedIn Post (feed)** — same voice, compressed. One earned-secret-anchored line in the middle. Conversational but professional. No outbound links in the body — the first comment carries them.
- **LinkedIn first comment** — register shifts OFF here. The first comment is utilitarian, not voicey: a friendly one-liner inviting research, the blog URL, and the source citations the Post quoted inline. Write it as a reader-respecting service note, not as another voice performance.
- **Twitter thread** — most compressed register. Drop articles ("the," "a") where natural. Each post is a stand-alone thought. No setup paragraphs — the thread structure IS the setup. Slightly more declarative, less hedging.
- **Facebook post** — warmer, more conversational than LinkedIn. Personal-essay register. OK to open with "Last week," or "I keep thinking about…" — language that would feel too soft on LinkedIn lands fine on FB.

The voice profile's rules (no em-dashes, contractions, two-reader frame, etc.) still apply on every platform except the first comment. The register shift is *tone within voice*, not a different voice.

## STEP 5a — Write the LinkedIn Post + first-comment pair (if selected)

This is the default LinkedIn output. Both files are produced together — never one without the other.

### Post (feed)

Targets:

- **Char count:** 1,300-2,500 (sweet spot). **2,900 hard cap** — LinkedIn rejects posts over 3,000 chars, and the script enforces the safety margin. If your draft exceeds 2,900, compress before saving.
- **Word count:** ~200-500.
- **Hook:** the user-picked Post hook from STEP 3, landing complete before char 210 (the mobile-fold "See more" cutoff).
- **Body structure:** 3 acts — `Hook → Stakes/Setup → Soft CTA`. One earned-secret line woven into the middle (one sentence, concrete, never a story arc — that's the Article's job if it was selected).
- **Closing line:** a specific question naming a concrete decision the reader is actually facing. Not "What do you think?" or "Agree?"
- **Hashtags:** 0-3, at the very end after a line break.
- **Formatting:** LinkedIn-native — single-line paragraphs, generous whitespace. NO markdown tables. NO markdown bold-italic stacks.
- **External links:** ZERO in the body. The blog URL and source citations go in the companion `linkedin-first-comment.md` file. This is what makes the Post format strategy work — link-in-body posts get throttled by ~25-60% on reach.

Save to `<piece>/04-diligence/social/linkedin-post.md` with frontmatter:

```yaml
---
type: linkedin-post
source_blog: <piece>/04-diligence/blog.md
companion_file: linkedin-first-comment.md
hook_formula: <name>
audience: <persona from 01-delegation.md>
target_chars: 1800
posting_notes:
  link_placement: first-comment-file
  hashtag_count_max: 3
  best_window: "Tue/Wed/Thu 7:30-8:30 AM PT"
---
```

### First comment (companion to the Post)

Targets:

- **Char count:** 80-1,200 (LinkedIn's comment limit is ~1,250; stay under it with margin).
- **Voice:** OFF. This is a utilitarian service note, not voice prose.
- **Structure (fixed template — don't improvise):**

  ```
  If you want to do your own research, here are the cited sources in my article:
  <blog-url>

  1. <source-1-title> — <source-1-url>
  2. <source-2-title> — <source-2-url>
  3. <source-3-title> — <source-3-url>
  ```

- **Which sources to include:** only the 2-3 citations the Post text **quotes inline** (e.g. the Anthropic stat, the 269-row catalog count). Do **not** include the full bibliography from the blog — those live on the blog post itself, not in the comment. If the Post quotes zero external sources, the comment still gets the intro line + blog URL (the sources block is just omitted).
- **No hashtags.** No emoji as bullets. Sequential numbering 1, 2, 3.
- **URL handling:** bare URLs only. LinkedIn auto-links them on render. Don't use markdown link syntax `[title](url)` — the comment box renders as plain text.

Save to `<piece>/04-diligence/social/linkedin-first-comment.md` with frontmatter:

```yaml
---
type: linkedin-first-comment
source_blog: <piece>/04-diligence/blog.md
companion_to: linkedin-post.md
target_chars: 600
posting_notes:
  paste_as: "the writer's own first comment under the published Post"
  inline_sources_only: true
---
```

The opening line is fixed for now — *"If you want to do your own research, here are the cited sources in my article:"* — keep the phrasing verbatim unless the writer overrides it via a follow-up edit. The verbatim phrasing is what we've calibrated against; rewording it ad-hoc each time defeats the calibration.

## STEP 5d — Write the LinkedIn Article (optional, only if selected)

Only generate this file if the writer explicitly selected **"LinkedIn Article (long-form)"** in STEP 2. If the writer only selected the Post + first-comment pair, skip this section entirely.

Targets:

- **Word count:** 800-1200.
- **Char count band:** 4,000-9,000 (validated by `social_score.py --type article`).
- **Tone:** more personal and opinion-led than the blog; earned secret surfaces in the first third.
- **First 2-3 lines:** the "See more" hook (the formula the writer picked for the Article). Never "I'm excited to share."
- **Formatting:** LinkedIn-native — bold for emphasis (sparingly), single-line paragraphs, generous whitespace. NO markdown tables (LinkedIn renders as raw text). NO markdown bold-italic stacks.
- **Citations:** 2-3 sourced statistics carrying the FLOW evidence triple (year + publisher + URL). Inline citations are fine in the Article (different surface from the Post — Articles aren't penalized the same way).
- **Ending:** an engagement question — specific, not "What do you think?" or "Agree?"

Save to `<piece>/04-diligence/social/linkedin-article.md` with frontmatter:

```yaml
---
type: linkedin-article
source_blog: <piece>/04-diligence/blog.md
hook_formula: <name>
audience: <persona from 01-delegation.md>
target_words: 1000
posting_notes:
  link_placement: inline-ok
  hashtag_count_max: 5
  best_window: "Tue/Wed/Thu 7:30-8:30 AM PT"
---
```

## STEP 5b — Write the Twitter thread (if selected)

Targets:

- **Posts:** 5-10. Sweet spot is 6-8. Anything under 5 fits better as a LinkedIn teaser; anything over 10 loses engagement past the fold.
- **Per-post limit:** ≤280 chars. Hard cap. The script enforces this — there is no soft fallback.
- **Layout:** each post is its own `## Post N` block. Post 1 is the hook. Post N (the final post) closes the loop and contains the blog URL + ≤2 hashtags total across the thread.
- **Voice:** compressed register (see STEP 4). Each post is a stand-alone thought; the reader can stop after any post and have gotten value.
- **Earned-secret placement:** somewhere in posts 2-4 (not buried at the end). One concrete sentence.
- **Numbering:** sequential 1, 2, 3, … The script checks this.
- **No emoji-as-bullet patterns** — don't use 👇 to "point to" the next post. The thread structure points itself.

Save to `<piece>/04-diligence/social/twitter-thread.md`. The file structure:

```markdown
---
type: twitter-thread
source_blog: <piece>/04-diligence/blog.md
hook_formula: <name>
audience: <persona from 01-delegation.md>
target_posts: 7
posting_notes:
  link_placement: final-post
  hashtag_count_max: 2
  best_window: "Tue/Wed/Thu 9:00-11:00 AM PT"
---

## Post 1

<hook post — ≤260 chars to leave room for "🧵" or "1/">

## Post 2

<post text — ≤280 chars>

## Post 3

<post text — ≤280 chars>

… (continue through final post)

## Post N

<closing post with blog URL and up to 2 hashtags>
```

## STEP 5c — Write the Facebook post (if selected)

Targets:

- **Char count:** 300-500 (allowed range 200-800). Facebook's algorithm favors mid-length posts; super-short posts read as shallow, super-long ones get truncated with "See more."
- **Word count:** 60-150.
- **Hook:** the user-picked Facebook hook from STEP 3.
- **Voice:** warmer than LinkedIn. Personal-essay register. OK to open with a temporal anchor ("Last week…", "I keep thinking about…").
- **External link:** the blog URL goes **in the body** (Facebook renders a preview card; this is the only platform where the link belongs inline).
- **Hashtags:** 0-2 total, at the end after a line break.
- **Earned-secret:** one sentence, conversational framing.

Save to `<piece>/04-diligence/social/facebook-post.md`:

```yaml
---
type: facebook-post
source_blog: <piece>/04-diligence/blog.md
hook_formula: <name>
audience: <persona from 01-delegation.md>
target_chars: 400
posting_notes:
  link_placement: body
  hashtag_count_max: 2
  best_window: "Weekdays 1:00-3:00 PM PT"
---
```

## STEP 6 — Format compliance check

Run the format checker against every file produced. The script lives at `${CLAUDE_PLUGIN_ROOT}/scripts/social_score.py`. One call per file:

```bash
# LinkedIn Post + first comment (the default LinkedIn pair)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/social_score.py \
  --file <piece>/04-diligence/social/linkedin-post.md --type post \
  --out <piece>/04-diligence/social/scorecards/linkedin-post.score.md

python3 ${CLAUDE_PLUGIN_ROOT}/scripts/social_score.py \
  --file <piece>/04-diligence/social/linkedin-first-comment.md --type first-comment \
  --out <piece>/04-diligence/social/scorecards/linkedin-first-comment.score.md

# LinkedIn Article (only if selected)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/social_score.py \
  --file <piece>/04-diligence/social/linkedin-article.md --type article \
  --out <piece>/04-diligence/social/scorecards/linkedin-article.score.md

# Twitter thread
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/social_score.py \
  --file <piece>/04-diligence/social/twitter-thread.md --type twitter-thread \
  --out <piece>/04-diligence/social/scorecards/twitter-thread.score.md

# Facebook post
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/social_score.py \
  --file <piece>/04-diligence/social/facebook-post.md --type facebook-post \
  --out <piece>/04-diligence/social/scorecards/facebook-post.score.md
```

Each call emits a scorecard scaffold (with 3-axis judgment scores empty) and a JSON sidecar with deterministic findings. Exit code 1 means format checks failed — fix the issues (length, hook position, per-post char limit, hashtag placement, external-link-in-body for LinkedIn Post) and re-run. **Don't proceed to STEP 7 until every file returns exit code 0.**

For the LinkedIn Post specifically: if char count exceeds 2,900, the script flags it. Compress — there is no auto-truncate fallback. The 2,900 cap exists because LinkedIn rejects posts over 3,000 chars, and we keep a 100-char safety margin for typographic-quote substitution and any trailing-whitespace surprises.

For the first-comment file specifically: the script requires at least one URL in the body (opposite of the Post rule). A first-comment with no URLs has nothing useful for the reader; it fails the check.

For Twitter: if any single post is over 280 chars, the script flags it. Rewrite that post — there is no auto-truncate fallback.

## STEP 7 — Fill in the 3-axis scorecard for each content artifact

The format checker produces a scaffold per artifact; you (the LLM) fill in three /10 scores by judgment for each scorecard file. For each axis:

- **Thought leadership /10** — Is the insight non-obvious enough that a senior practitioner would forward this to a peer? 10 = "I hadn't thought of it that way" reaction guaranteed. 5 = competent restatement of conventional wisdom. 0 = generic.
- **Pain (lands on the reader, not a third party) /10** — Does the pain land on the reader's own job/identity/recent week, or on a third party they observe? 10 = the reader thinks "this is about me." 5 = "this is about someone I know." 0 = abstract pain on no one in particular.
- **Audience fit /10** — Does the post speak to the persona declared in `01-delegation.md`, using their vocabulary and decision context? Twitter and Facebook each have their own audience flavor — a great LinkedIn post can be a mediocre Twitter post if the register doesn't shift. Score for the platform's audience, not the blog's.

Each score needs a **one-sentence justification** — specific, not generic.

Recommendation per artifact: ship if all three axes ≥ 7. Revise if any axis is 4-6. Discard if any axis is ≤ 3.

**Exception — `linkedin-first-comment.md` skips the 3-axis scorecard.** The first comment is a utilitarian service note, not a content artifact. The format checker still runs on it (URL-present check, length band, hashtag/emoji-bullet sanity), but the scorecard scaffold for the first-comment file is just a one-line "deterministic check only — no LLM-judgment axes apply" note. Don't try to score it on thought leadership / pain / audience fit.

## STEP 8 — Update state and report

Append to `<piece>/state.md`:

```
- [x] Social derivatives produced (<platform list>)
```

And to the process log: `<ISO> — Social derivatives: <platform list>; axes <T>/10, <P>/10, <A>/10 per platform.`

Report to the writer:

```
Social derivatives produced.

LinkedIn Post:          <piece>/04-diligence/social/linkedin-post.md (<chars> chars)
LinkedIn first comment: <piece>/04-diligence/social/linkedin-first-comment.md (<chars> chars)
LinkedIn Article:       <piece>/04-diligence/social/linkedin-article.md (<words> words)   [only if Article selected]
Twitter Thread:         <piece>/04-diligence/social/twitter-thread.md (<N> posts)
Facebook Post:          <piece>/04-diligence/social/facebook-post.md (<chars> chars)

Scorecards: <piece>/04-diligence/social/scorecards/
  Per content artifact: thought leadership /10, pain /10, audience fit /10
  Recommendation per artifact: ship | revise | discard
  (Note: linkedin-first-comment.md is a utilitarian payload — format-check only, no 3-axis scoring.)

Posting reminders:
  - LinkedIn Post: paste the POST body first. NO link in the body. As soon as the
    post publishes, paste the contents of linkedin-first-comment.md as the FIRST
    COMMENT under the post (under your own handle). The first comment is what
    carries the blog URL and source citations. Best window: Tue/Wed/Thu 7:30-8:30 AM PT.
  - LinkedIn Article (if produced): published via "Write article" — separate
    LinkedIn surface, gets its own URL. Inline links allowed in the body.
  - Twitter: blog URL in FINAL POST. Best window: Tue/Wed/Thu 9:00-11:00 AM PT.
  - Facebook: blog URL in BODY (renders preview card). Best window: weekdays 1:00-3:00 PM PT.

The plugin does NOT auto-publish to any platform. Paste and post by hand on each platform.

Next step — ship these files to your repo so a teammate or downstream automation
can pick them up:

  /4d-blog-engine:blog-publish <slug>

The publish skill detects this `social/` directory and includes the .md files
plus scorecards in the same commit as the post. The blog post itself gets
treated as a republish (dateModified bump → site rebuild). If the post was
already published before social existed, this is how the social files reach
the repo.
```

(Only list the platforms the writer actually selected.)

## What this skill does NOT do

- It does NOT modify the signed blog. The blog is canonical and read-only after the Release Owner signs.
- It does NOT post to LinkedIn, Twitter/X, or Facebook on the writer's behalf. The writer pastes by hand on each platform. This is intentional — see the whitepaper's Diligence ethos.
- It does NOT ship the derivative files into the writer's publishing repo. The files land under `<piece>/04-diligence/social/` only — `/4d-blog-engine:blog-publish` is the skill that copies them into the GitHub repo (auto-detected on its next run for the same slug). Keeping the publish step in one skill avoids two skills both writing into the repo.
- It does NOT generate carousels, video clips, infographics, or YouTube descriptions — that's outside scope. Article + teaser (LinkedIn), thread (Twitter), single post (Facebook) — that's the scope.
- It does NOT auto-invoke after Phase 4 sign-off. The writer runs `/4d-blog-engine:blog-social` explicitly when they want derivatives.

## Degradation behaviors

- **social_score.py fails to run** (Python error): treat as a script bug and surface it; fall back to the format rules in `references/hook-library.md` checked manually.
- **Writer picks `[skip hook selection]`:** generate the recommended hook automatically but flag in the platform's frontmatter that the human did not pick.
- **The signed blog won't compress to a given platform** (too technical for Twitter, too short to make a 7-post thread, etc.): surface the issue per platform ("the source post's argument doesn't compress to a Twitter thread — recommend skipping Twitter for this piece"). Do not force-fit.
- **Twitter thread comes out under 5 posts after compression attempts:** report and suggest a LinkedIn teaser as the better fit. Don't pad with filler posts to hit the minimum.
