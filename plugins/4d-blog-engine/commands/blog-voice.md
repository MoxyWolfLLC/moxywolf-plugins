---
description: Build your voice profile through a structured 8-question interview. Produces a voice file the 4D pipeline uses as the anchor for every post you write.
argument-hint: (no arguments — runs interactively)
allowed-tools: [Read, Write, Edit, AskUserQuestion, Glob, Bash]
---

# /4d-blog-engine:blog-voice — capture your writing voice

Invoke the `blog-voice` skill. It runs an 8-question interview to capture how you argue, your sentence rhythm, your vocabulary, where you get heated, what you'd never say — everything the pipeline needs to draft prose that sounds like you, not like AI.

The skill writes a voice file to your blog project directory:

```
<blog-project-dir>/<your-name-slug>-voice.md
```

For example, if your author name is "Jane Doe," the file lands at `<blog-project-dir>/jane-doe-voice.md`. Every subsequent `/4d-blog-engine:blog-pipeline` run loads this file as STEP 0 of the pipeline (Phase 2's voice anchor and Phase 4's voice-match check).

**One voice file per author.** You can run `/blog-voice` more than once in the same blog project to capture additional voices — guest contributors, co-writers, multiple staff bylines. At STEP 0 the skill asks whose voice this interview is for; pick the project's default author or "Someone else" and type the guest's name.

When the pipeline runs (`/4d-blog-engine:blog-pipeline` or `/4d-blog-engine:blog-start`) and finds more than one `*-voice.md` file in the blog project directory, it asks which voice to use for that post.

If you've already done a voice profile in another project and want to import it, drop the file at `<blog-project-dir>/<your-name-slug>-voice.md` directly — the plugin reads from disk and doesn't care whether the interview ran here or somewhere else.

The 8 questions cover:

1. Origin story — how you came to this work
2. The pattern — what you see that others miss
3. How you argue — your rhetorical instincts
4. What you hate — where conviction turns to heat
5. How you explain — your teaching style
6. Your reader — who you write for
7. The line you won't cross — your contrarian positions
8. Your natural register — formal, conversational, fragmented

One question per message. The skill pushes back on vague answers — specificity is what makes the rest of the pipeline work.

Read `skills/blog-voice/SKILL.md` for the full workflow.
