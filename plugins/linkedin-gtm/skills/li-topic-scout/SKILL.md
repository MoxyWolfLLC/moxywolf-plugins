---
name: li-topic-scout
risk_tier: read-only
description: >
  The Monday topic scout for the blog-to-LinkedIn rhythm. Reads the last 30 days of discourse
  for each long-form page (FrontierFounder, MoxyWolf LLC, STIGViewer), proposes two or three
  candidate topics per page with a why-now, the pillar it would be a spoke on, and tier 1-3
  sources, and pairs each with a candidate earned secret drawn from Dorian's own meeting notes
  and threads, quoted and linked, for him to confirm or replace. Use it for "/li-topics",
  "what should we write about this week", "topic scout", or from the weekly automation. It
  proposes; it never starts the blog pipeline, picks the page or writes a post.
allowed-tools: [Read, Write, Bash]
---

# li-topic-scout: what's worth writing this week

The 4D blog engine starts from a base document, and nothing in it decides what to write about. This skill gives Dorian Cougias a short list every Monday. He picks, supplies or confirms the earned secret, and only then does `/4d-blog-engine:blog-pipeline` run.

## Inputs

- The pages in config `long_form.pages`, and for each one the pillars it can carry. FrontierFounder today: `the-frontier-founder`, `ai-fluency-for-founders`, `ai-governance` (in `FrontierFounder/content/blog/_clusters`, each with a `why`). MoxyWolf LLC and STIGViewer targets are register-only in the blog engine; propose a pillar and say it would be new.
- The week's li-signals output and li-weekly topic notes, if present. The same conversations Dorian is engaging with are the first place to look.
- Published posts in each target repo, so nothing repeats an existing spoke.

## Steps

1. **Sweep, lightly.** For each page, run a reduced version of the blog engine's discourse sweep (`4d-blog-engine/skills/discourse-sweep/SKILL.md`): the last 30 days on Reddit, Hacker News, Substack, LinkedIn articles, X, GitHub and primary sources (.gov, standards bodies, vendor research). Look for a live argument, a new primary source, or a contradiction between sources. Apply `references/source-quality-tiers.md`: tier 4 and 5 never appear.
2. **Shape two or three candidates per page.** Each one: a one-sentence thesis, the specific reader, why now (the trigger, dated), the pillar and whether its `why` supports the thesis, two or three tier 1-3 sources with links, and the obvious counter-argument.
3. **Find a candidate earned secret.** Search Dorian's Granola meetings (last 30 days on the free plan), memory and recent threads for something he lived that bears on the thesis: a number, a date, a named person or company, an event. Quote it in at most two sentences with a link to where it came from. Mark it plainly as a candidate. If nothing real turns up, say "none found, needs yours"; never invent or embellish one. Partner conversations under NDA (suppression list notes) are not material for public posts unless Dorian says otherwise.
4. **Deliver one message.** Grouped by page, at most nine candidates, each about six lines. End with one question: which ones to take into the pipeline, and with what earned secret. No em dashes; plain language.

## What this never does

- Start a pipeline, choose the long-form page, or write a draft.
- Cite a source it didn't fetch, or invent an earned secret.
- Use NDA or partner-confidential material without Dorian's say-so.
