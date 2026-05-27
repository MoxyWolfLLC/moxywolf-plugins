---
name: blog-voice
description: |
  This skill should be used when the user runs /4d-blog-engine:blog-voice or asks any variant of "build my voice profile," "do the voice interview," "capture how I write," "create a voice file," "how do I sound when I write," or "set up the voice anchor for the blog plugin." The skill runs an 8-question structured interview, analyzes the answers, and writes a voice profile to <blog-project-dir>/<author-slug>-voice.md. This file is the voice anchor the 4D pipeline loads in STEP 0 of every post. Self-contained inside the 4d-blog-engine plugin — no dependency on editorial-forge or any other plugin. Derived from the voice-architect interview structure in editorial-forge. Do NOT use this skill for: writing prose (use /4d-blog-engine:blog-pipeline), running the full pipeline, or applying a pre-existing voice (the pipeline loads the file you produce here automatically).
allowed-tools: [Read, Write, Edit, AskUserQuestion, Glob, Bash]
---

# Blog-Voice — capture the writer's voice in 8 questions

> **Read this when:** the user runs `/4d-blog-engine:blog-voice`. Your job is to interview the writer, analyze the answers, and produce a voice profile markdown file the rest of the pipeline can anchor to.

## What this skill produces

A single file at `<BLOG_PROJECT_DIR>/<AUTHOR_SLUG>-voice.md` containing the writer's voice profile. The 4D pipeline's STEP 0 reads this file before every post. Phase 4's voice-match scoring checks generated prose against it.

The skill also writes the raw Q&A transcript to `<BLOG_PROJECT_DIR>/<AUTHOR_SLUG>-voice-raw-qa.md` for the audit trail and for the writer to re-read later when calibrating.

## Core principle (read this first)

Voice is not style. Style is mechanics (sentence length, punctuation, word choice). Voice is the person — their origin story, their patterns of thought, how they fight, what they refuse to say. This interview extracts both.

**You never apply a preset voice.** Not MoxyWolf's, not anyone else's. The voice profile this skill produces comes entirely from the writer's answers. If you find yourself reaching for a template phrase the writer didn't say, stop.

## STEP 0 — Resolve the blog project and pick whose voice we're capturing

Walk up from the current working directory to find `blog-project-instructions.md`:

```bash
find_blog_project() {
  local d="$PWD"
  while [ "$d" != "/" ]; do
    if [ -f "$d/blog-project-instructions.md" ]; then echo "$d"; return 0; fi
    d="$(dirname "$d")"
  done
  return 1
}
BLOG_PROJECT_DIR=$(find_blog_project)
```

If no marker file is found, halt with:

> *No blog project found here. Run `/4d-blog-engine:blog-init` first to set up your blog project, then come back to `/blog-voice`.*

Read the marker file. Extract `DEFAULT_AUTHOR_NAME` from the Setup section's `Author` value. Glob `<BLOG_PROJECT_DIR>/*-voice.md` to enumerate existing voice files (`EXISTING_VOICES` — list of file paths).

The plugin supports multiple voices in one blog project. Ask the writer who this interview is for, via `AskUserQuestion`:

> *Whose voice are we capturing in this interview?*

Build the options dynamically:

- **Option A:** `<DEFAULT_AUTHOR_NAME>` (the project's default author from `blog-project-instructions.md`). Always show this option.
- **Option B-N:** One option per **existing** voice file in `EXISTING_VOICES` whose slug doesn't match the default author's slug (so the writer can re-interview a previously captured guest author). Label each with the author name pulled from the voice file's frontmatter.
- **Last option:** *"Someone else — I'll type the name"* — free-text input that captures a new author name (e.g., a guest contributor).

If the writer picks an existing author (default or guest), use that name. If they pick "Someone else," ask: *"What's the author name?"* Free-text.

Store the chosen name as `AUTHOR_NAME`. Slugify to kebab-case (lowercase, ASCII, spaces and punctuation become hyphens): "Jane Doe" → `jane-doe`. Store as `AUTHOR_SLUG`.

Compute `VOICE_FILE = <BLOG_PROJECT_DIR>/<AUTHOR_SLUG>-voice.md` and `RAW_QA_FILE = <BLOG_PROJECT_DIR>/<AUTHOR_SLUG>-voice-raw-qa.md`.

If `VOICE_FILE` already exists, ask:

> *A voice profile for `<AUTHOR_NAME>` already exists at `<VOICE_FILE>`. What now?*

Options:

1. **Re-interview from scratch** — replaces the existing file. Use when their voice has shifted or the old profile feels off.
2. **Continue from where I stopped** — if `RAW_QA_FILE` has partial answers, pick up at the next unanswered question.
3. **Cancel** — leave the existing profile alone.

If "continue": read `RAW_QA_FILE`, count completed answers, skip ahead. If the file is missing or empty, treat as re-interview.

## STEP 1 — Set up the raw-Q&A file

Write a header to `RAW_QA_FILE` (or read+continue if resuming):

```markdown
---
author: <AUTHOR_NAME>
author_slug: <AUTHOR_SLUG>
date_started: <today YYYY-MM-DD>
type: voice-raw-qa
---

# Voice interview — raw Q&A

Each Q&A pair is captured as the writer gave it. The analyzed profile lives in `<AUTHOR_SLUG>-voice.md`.
```

Append each answer to this file as the interview proceeds.

## STEP 2 — Tell the writer what's coming

Before the first question, set expectations in one short message:

> *Eight questions. One at a time. Answer however long you want — short or long. The point is for you to say something specific that's actually yours. If I get a vague answer, I'll push back. The interview usually takes 15-40 minutes. Save state is automatic — you can stop and pick up later.*

> *Ready? Here's question 1.*

## STEP 3 — Run the 8 questions, one per message

**One question per message.** Wait for the full answer. After each answer:

1. Append the Q&A to `RAW_QA_FILE`.
2. If the answer is vague, abstract, or sounds rehearsed, push back ONCE with a specific paraphrase request. Don't keep pushing — after one round, take what you got and move on.
3. Move to the next question.

### Question 1 — Origin story

> *How did you come to this work? Not your resume — the moment you knew this was your thing.*

Extract: the emotional entry point. Where conviction comes from. Whether they lead with stories or credentials.

### Question 2 — The pattern

> *What do you see that others miss? What pattern have you noticed over years that most people in your field haven't caught yet?*

Extract: intellectual signature. How they synthesize. Whether they think in systems, narratives, or data.

### Question 3 — How you argue

> *When you're making a case to someone who disagrees, how do you do it? Stories first? Data first? Do you get loud or get quiet?*

Extract: argument structure. Rhetorical instincts. Deductive, narrative, Socratic, or confrontational.

### Question 4 — What you hate

> *What's the thing in your field that makes you genuinely angry? The practice, the phrase, the mindset that you'd burn if you could?*

Extract: emotional triggers. Where conviction turns to heat. The forbidden territory they patrol.

### Question 5 — How you explain

> *Pick something complex in your domain. Explain it to me like I'm smart but from a different field.*

Extract: teaching style. Metaphor preferences. How they simplify without dumbing down. Technical vocabulary comfort.

### Question 6 — Your reader

> *When you picture someone reading your work and thinking "they get it" — who is that person and what specifically did you say that landed?*

Extract: who they write FOR. What "landing" feels like to them. Their theory of impact.

### Question 7 — The line you won't cross

> *What's the popular advice in your space that you refuse to give? Why?*

Extract: intellectual boundaries. Where they diverge from consensus. The contrarian positions they hold with conviction.

### Question 8 — Your natural register

> *Do you write like you talk? More formal? Less? What's the closest published thing to how you actually sound?*

Extract: self-awareness about register. The gap (or lack of gap) between spoken and written voice. Reference points for calibration.

## STEP 4 — Analyze the answers

Once all 8 are captured, analyze the raw Q&A for:

1. **Argument style** — deductive (premise → conclusion), narrative (story → insight), Socratic (question → discovery), confrontational (challenge → proof), or hybrid.
2. **Sentence rhythm** — short and punchy, long and layered, alternating, fragments for emphasis.
3. **Vocabulary register** — technical depth, jargon comfort, metaphor density, register (formal / conversational / informal).
4. **Emotional patterns** — where they heat up, where they pull back, what triggers conviction vs. caution.
5. **Teaching mode** — analogies, step-by-step, examples first, theory first.
6. **Forbidden territory** — phrases, structures, tones that would never come from this writer. Extract these as concrete examples (*"This writer would never say 'It's worth noting that...'"*).
7. **Anti-detection markers** — contraction rate, sentence length range, fragment usage, paragraph length, technical vocabulary depth, emotional vocabulary, conjunction-starter frequency, metaphor density. Calibrate from observed patterns in the raw Q&A.

## STEP 5 — Write the voice profile

Compose the voice profile and write it to `VOICE_FILE`:

```markdown
---
title: "Voice Profile — <AUTHOR_NAME>"
author: <AUTHOR_NAME>
author_slug: <AUTHOR_SLUG>
created: <today YYYY-MM-DD>
last_validated: <today YYYY-MM-DD>
type: voice-profile
schema: voice-profile/v1
---

# Voice Profile — <AUTHOR_NAME>

## How they argue

<Analysis of argument style with specific examples drawn from interview answers. Quote phrases the writer actually used.>

## Sentence rhythm

<Observed patterns: length range, variation, fragment usage, paragraph shape. Anchor to specific examples from the Q&A.>

## Vocabulary and register

<Technical depth, jargon comfort, metaphor preferences, words they reach for, words they avoid. Note their stated register from Q8.>

## Emotional patterns

<Where they get heated, where they pull back, what triggers conviction. Anchor to Q4 specifically.>

## Teaching mode

<How they explain complex things, metaphor style, simplification approach. Anchor to Q5.>

## Who they write for

<The reader from Q6. Be specific — a named persona if they gave one, a description otherwise. What "landing" feels like to them.>

## The line they won't cross

<From Q7. The contrarian positions, the popular advice they refuse to give, why.>

## Forbidden patterns

Phrases, structures, or tones that would never come from this writer:

- <Specific example>
- <Specific example>
- <Specific example>

## "Sounds like me" passages

Three to five short passages from the raw Q&A that the writer confirmed (in STEP 6 below) as authentically their voice. Use these as positive calibration anchors when generating prose:

- > <Passage 1>
- > <Passage 2>
- > <Passage 3>

## Anti-detection markers

Calibrated checklist for prose generated in this writer's voice. Phase 4's slop linter scores against these.

- **Contraction rate:** <X>% of opportunities (observed)
- **Sentence length range:** <X>-<Y> words typical
- **Fragment usage:** <frequency and purpose>
- **Paragraph length:** <typical range>
- **Technical vocabulary depth:** <level>
- **Emotional vocabulary:** <observed patterns>
- **Conjunction starters (And, But, Because):** <observed frequency>
- **Metaphor density:** <low / medium / high>
- **Em-dashes:** <observed usage — banned if user's voice avoids them>
- **Typographer's quotes vs straight:** <observed preference>

## Notes for the pipeline

- Phase 2 of `/4d-blog-engine:blog-pipeline` loads this file at STEP 0 and reports back what it found.
- Phase 4's reviewer scores generated prose against the Forbidden Patterns and the Anti-Detection Markers above.
- If the writer's voice shifts over time, re-run `/4d-blog-engine:blog-voice` to refresh this profile.
```

## STEP 6 — Validate with the writer

Show the profile to the writer (full markdown render). Ask:

> *Does this sound like you? Anything you'd add, change, or cut? Read the "Forbidden patterns" and the "Sounds like me" passages especially carefully — those are the strongest calibration anchors.*

Iterate up to 2 times based on their feedback. Each iteration edits the profile in place; don't bloat it with revisions.

On the third edit request, write the current profile to disk with the writer's most recent edits and tell them they can keep editing the file by hand (it's just markdown).

## STEP 7 — Report back

```
Voice profile saved.

  Profile:  <VOICE_FILE>
  Raw Q&A:  <RAW_QA_FILE>
  Author:   <AUTHOR_NAME>

The pipeline reads `*-voice.md` files from your blog project directory.
When you run /blog or /blog-start and there's more than one, you'll be
asked which voice to use for that post.

To add another author's voice (guest contributors, co-writers), re-run
/4d-blog-engine:blog-voice and pick "Someone else" at STEP 0.

Next: run /4d-blog-engine:blog-pipeline <path-to-base-document> to write a post.
```

## What this skill does NOT do

- It does not generate prose. The profile is the input to Phase 2; drafting happens there.
- It does not apply any preset voice. MoxyWolf, brand guidelines, anyone else's voice — none of it leaks into the profile. The profile comes from the writer's answers only.
- It does not skip questions. Each question builds on previous ones. If a writer says "skip 4," push back once: *"Question 4 is the one that surfaces conviction. Even a one-sentence answer helps. Want to take a shot?"* If they still refuse, log it as "skipped by writer" in the raw Q&A and proceed.
- It does not store anything outside `<BLOG_PROJECT_DIR>`. The voice file and raw Q&A live with the blog project.

## Degradation behaviors

- **No `blog-project-instructions.md` found:** halt with a clear pointer to `/4d-blog-engine:blog-init`. Don't proceed.
- **AUTHOR_NAME missing from marker file:** ask the writer for their name, but don't write it back into the marker file from here (that's blog-init's job).
- **Writer wants to import an existing voice file from another project:** tell them to copy the file into `<BLOG_PROJECT_DIR>/<AUTHOR_SLUG>-voice.md` directly. The plugin reads from disk; provenance doesn't matter.
- **Writer aborts mid-interview:** the raw Q&A is already on disk. They can pick up from STEP 0's "continue from where I stopped" option later.
