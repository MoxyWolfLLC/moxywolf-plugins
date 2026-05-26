---
name: 4d-blog-engine
description: |
  This skill should be used when the user asks to "write a blog post from this document", "derive a blog from this whitepaper / report / transcript / meeting notes", "run the 4D pipeline on this", "write a LinkedIn article + teaser from this", "run the release-owner gate on my draft", or any request to turn a base document into a publication-ready blog post + LinkedIn pair under the 4D AI Fluency Framework. This skill is the orchestrator — it routes to the four phase commands (delegate, describe, discern, diligence) and the two derivative commands (linkedin, status). It is also the central place that detects the active Cowork project and computes the per-piece working directory. Trigger aggressively for anything touching deriving a blog from a base doc, the 4D framework, the Release Owner Gate, or producing a blog + LinkedIn pair. Do NOT use this skill for: writing a blog post from scratch with no base document; editing an existing published post; rewriting an arbitrary document with no derivation target.
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# 4D Blog Engine — orchestrator

> **Read this when:** any `/4d-blog-engine:*` command runs. This file is the spine; it routes work to the phase commands and computes the working directory. Read `references/4d-discipline.md` immediately after this file — every phase needs the framework loaded.

## What this skill does

This skill turns a base document plus a chosen angle/question into a publication-ready blog post, a long-form LinkedIn article, and a short hook-led LinkedIn teaser — under the 4D AI Fluency Framework from MoxyWolf's *Beyond the Prompt* whitepaper.

It is composed of seven commands, four of which map directly to the four D's:

| Command | Phase | Specialist skill invoked |
|---|---|---|
| `/4d-blog-engine:delegate` | Delegation — triage, angle pick, earned-secret stall | inline (this skill) |
| `/4d-blog-engine:describe` | Description — voice interview, outline, At-a-Glance | reuses `research-pipeline/content-writer`'s 8-question interview |
| `/4d-blog-engine:discern` | Discernment — 30-day sweep, draft, slop pass | `discourse-sweep`, `research-pipeline/*`, `council:deliberate`, `bibtex-builder` |
| `/4d-blog-engine:diligence` | Diligence — Release Owner Gate | `release-owner-gate` |
| `/4d-blog-engine:linkedin` | Derivative output | `linkedin-deriver` |
| `/4d-blog-engine:blog` | End-to-end (all four phases sequentially) | all of the above |
| `/4d-blog-engine:status` | Print current piece state | inline (this skill) |

## STEP 0 — Always load these references first

When this skill is invoked, **immediately Read these three files in this order before doing any other work**:

1. `${CLAUDE_PLUGIN_ROOT}/references/4d-discipline.md` — the framework, the gate definitions, the load-bearing rules.
2. `${CLAUDE_PLUGIN_ROOT}/references/ai-anti-patterns.md` — the slop catalog (two-tier).
3. `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md` — the MoxyWolf voice anchor.

**Report back to the user** what was loaded (voice tone, sentence-length range, contraction rate target, fragment frequency, conjunction-starter frequency, top forbidden phrases). Silent loading causes voice drift in long sessions. This is the jamon8888/cc-suite STEP 0 LOAD DNA discipline — never skip the report-back.

## STEP 1 — Detect the active Cowork project and compute the working directory

The plugin saves everything into the active Cowork project's directory using a standardized structure. To find the active project, walk up from the current working directory looking for the marker file:

```bash
# Pseudocode for the discovery walk
CWD = current working directory
while CWD != /:
    if exists CWD/00 – Project Hub/cowork-project-instructions.md:
        ACTIVE_PROJECT_DIR = CWD
        break
    CWD = parent(CWD)
else:
    ACTIVE_PROJECT_DIR = "$HOME/4d-blog-engine-work"  # fallback
```

Implement with Bash. **Numbered MoxyWolf project folders may use either an en-dash (`–`, U+2013) or a plain hyphen (`-`, U+002D) as the separator** — folders 00-09 + 99 typically use en-dash; folders 11-12 (Project Knowledge + MARCOM) sometimes use hyphen depending on when they were created. Path resolution must tolerate both:

```bash
# tolerant of en-dash (U+2013) and hyphen (U+002D) in numbered folder names
find_active_project() {
  local d="$PWD"
  while [ "$d" != "/" ]; do
    for sep in '–' '-'; do
      if [ -f "$d/00 ${sep} Project Hub/cowork-project-instructions.md" ]; then
        echo "$d"; return 0
      fi
    done
    d="$(dirname "$d")"
  done
  echo "$HOME/4d-blog-engine-work"
}
ACTIVE_PROJECT=$(find_active_project)

# Resolve the MARCOM folder tolerantly. Returns the actual path the project uses.
resolve_marcom() {
  local proj="$1"
  for d in "$proj"/12\ *MARCOM "$proj"/12-MARCOM; do
    [ -d "$d" ] && { echo "$d"; return 0; }
  done
  # No MARCOM folder exists — create with en-dash convention as default
  local dest="$proj/12 – MARCOM"
  mkdir -p "$dest"
  echo "$dest"
}
MARCOM_DIR=$(resolve_marcom "$ACTIVE_PROJECT")
```

**Report the resolved active project to the user** in one line — `Active project: <name> (<path>)` — before proceeding. If the fallback was used, say so explicitly: `Active project: NONE — falling back to $HOME/4d-blog-engine-work`.

The per-piece working directory is then `<MARCOM_DIR>/Posts/<YYYY-MM-DD-slug>/` — `<MARCOM_DIR>` uses whichever separator the project actually has on disk (as resolved by `resolve_marcom`), so the path works regardless of typographic inconsistency. The slug is computed from the chosen post title (kebab-cased, ASCII, ≤40 chars, leading articles dropped).

Create the per-piece directory tree at the start of the run:

```
<piece>/
├── state.md
├── 01-delegation.md         # Phase 1 writes
├── 02-description.md        # Phase 2 writes
├── 03-discernment/          # Phase 3 writes
└── 04-diligence/            # Phase 4 writes
```

The `state.md` template lives at the bottom of this file.

## STEP 2 — Route the command

After STEP 0 and STEP 1, route to the requested phase. Each phase has its own skill or inline workflow described below. **Phases enforce ordering via the `_phase` and `_status` fields in their output frontmatter** — Phase N+1 refuses to run if Phase N didn't pass or if more than 24 hours have elapsed since Phase N passed. Don't try to defeat this — it's the engineered gate the whole plugin exists for.

### Phase 1 — Delegation (inline)

Triggered by `/4d-blog-engine:delegate <base-doc>` or as the first step of `/4d-blog-engine:blog`.

**Workflow:**

1. **Locate the base document.** `<base-doc>` can be: a file path (absolute or relative to CWD), a URL, or pasted text supplied in a prior message. If a URL, use WebFetch (after checking the provenance set) or Claude in Chrome. If a file, Read directly. If pasted, use as-is.
2. **Classify the doc type** (LLM judgment): blog post / whitepaper / meeting notes / transcript / report / email / braindump / code commit log / other. State the classification in one line.
3. **Capability triage** — apply a fast yes/no test from `references/4d-discipline.md` (Delegation section): does this topic warrant a post against the jagged frontier? If NO, surface the one-line reason and exit with a clean message ("Triage NO: topic falls outside the model's reliable frontier — recommend a manual brief instead").
4. **Angle elicitation.** If the user supplied an angle, restate it and confirm. If not, propose 3-5 candidate angles via `AskUserQuestion`. Each angle = one-sentence thesis + audience + a slot for the earned secret. Angles must be genuinely different (not three rephrasings).
5. **Earned-secret stall.** Ask: *"What do you know from direct experience about this that most of your audience does not? It cannot be something you read."* Push back hard on weak answers — paraphrase the question if the user offers something abstract. **Do not proceed until you get a concrete, lived-experience answer.** If the user can't supply one within 2 rounds, write a state.md note ("blocked: no earned secret") and exit. This stall is the feature.
6. **Modality decision.** Ask which modality (automation / augmentation / agency, default automation) — see `references/4d-discipline.md`. Most pieces are automation: the plugin drafts, the human signs.
7. **Write `01-delegation.md`** with frontmatter `_phase: 01, _status: passed, _timestamp: <ISO-8601>, earned_secret: <one line>, modality: <choice>`. Body: base doc location, doc type, angle, candidate angles considered + why rejected, audience persona (forced to specifics — name, role, recent context, frustration).

### Phase 2 — Description

Triggered by `/4d-blog-engine:describe` or as Phase 2 of `:blog`. Refuses to run if `01-delegation.md`'s `_status` isn't `passed` or its timestamp is >24h old.

**Workflow:**

1. **Phase 1 → Phase 2 carry (v0.1.1+).** Before invoking the voice interview, read `<piece>/01-delegation.md`'s `earned_secret` field and the `angle` + `audience` blocks. Scan the earned-secret text for content matching each of the 8 voice-injection slots:

   - **Trigger** — a recent event that prompted the topic
   - **Evidence** — a specific number, fact, or anecdote that grounds the claim
   - **Contrarian Take** — the "but actually" the post pushes against
   - **Authority** — why this author specifically gets to say this
   - **Specific Reader** — the named persona the post is for (also drawn from the audience block)
   - **Business Connection** — how it connects to the author's product/service
   - **Call to Action** — the Monday move the reader should make
   - **Emotional Core** — the visceral phrase or image that sticks

   For each slot where a substantive match is detectable, pre-fill a draft answer. Present the pre-filled set to the user with one confirmation message: *"Based on your earned secret + angle, I have draft answers for: [Trigger, Evidence, Emotional Core, ...]. Use these, refine them, or re-ask?"* If the user accepts, skip the corresponding slots in step 2. If the user wants to refine, capture the refinement. If the user wants to re-ask, queue that slot for step 2.

   This step exists because the Phase 1 earned-secret answer frequently substantively answers Trigger, Evidence, and Emotional Core — re-asking those wastes the user's turns and risks thinner second-pass answers.

2. **Voice interview (carried slots skipped).** For any of the 8 voice-injection slots NOT pre-filled in step 1, ask the question from `research-pipeline/content-writer`'s set (Trigger / Evidence / Contrarian Take / Authority / Specific Reader / Business Connection / Call to Action / Emotional Core). **One question per message.** Push back on vague answers; the discipline of specifics is what makes the rest work.
3. **Pick the structure.** Default: Sorkin DOB (Desire / Obstacle / Battle). Alternatives: Hero's Journey, Story Circle, Inverted Pyramid. State the choice and explain why.
4. **Build the outline.** H2-by-H2, 60-70% of H2s phrased as natural questions per `references/aeo-checklist.md`. Per-section word budget. Per-section evidence-mapping ("what does the 30-day sweep need to find for this section?"). Per-section "what's the citation capsule's load-bearing claim?"
5. **Draft the "At a Glance" block.** 60-90 words. Self-contained. Takes a point of view. Use the template in `references/aeo-checklist.md`.
6. **Pre-load the anti-slop catalog.** Read `references/ai-anti-patterns.md` in full; state in one line which Tier-2-Major patterns you'll specifically guard against in this piece's prose.
7. **Write `02-description.md`** with frontmatter `_phase: 02, _status: passed, _timestamp: <ISO>`. Body: voice interview Q&A (including carried slots, marked as carried-from-Phase-1), structure choice + reason, outline (H2s with section budgets and evidence needs), At-a-Glance block, anti-slop watch list.
8. **Gate.** Show the outline + At-a-Glance to the user and ask "proceed / revise <specific>". Cap at 2 revision rounds before escalating.

### Phase 3 — Discernment

Triggered by `/4d-blog-engine:discern` or as Phase 3 of `:blog`. Refuses to run on stale Phase 2.

**Workflow:** Hand off to the `discourse-sweep` skill (in this plugin) for steps 1-2, then call `research-pipeline/content-writer` for the draft, then `prose_lint.py` and the Tier-2 LLM sub-agent for the slop pass. Detailed orchestration is in `skills/discourse-sweep/SKILL.md` and the discern command file.

The orchestrator's responsibility in Phase 3: **chain the sub-skills in order**, persist each step's artifact in `<piece>/03-discernment/`, and surface the slop letter grade to the user at the end. If grade ≤ C, force a re-rewrite. If grade = D or F, abort the phase and require a structural rethink.

### Phase 4 — Diligence

Triggered by `/4d-blog-engine:diligence` or as Phase 4 of `:blog`. Refuses to run on stale Phase 3.

Hand off entirely to the `release-owner-gate` skill (in this plugin). Detailed orchestration is in `skills/release-owner-gate/SKILL.md`. Phase 4 is non-trivial — read that skill's instructions in full before invoking it.

### Derivative — LinkedIn pair

Triggered by `/4d-blog-engine:linkedin` (on an existing Diligence-passed blog) or as the final step of `:blog`. Hand off entirely to the `linkedin-deriver` skill.

## Status command

`/4d-blog-engine:status [<piece-slug>]` — if no slug given, pick the most-recently-modified piece directory. Read its `state.md` and print: current phase, gates passed, next command to run, slop grade if Phase 3 ran, preflight verdict if Phase 4 ran. Useful when resuming a multi-day piece.

## state.md template

When STEP 1 creates the piece directory, write `state.md` with this structure:

```markdown
---
slug: <YYYY-MM-DD-kebab-title>
title: <title>
created: <ISO-8601>
active_project: <project name>
piece_dir: <absolute path>
current_phase: 01
gates_passed: []
target_words: 1500
modality: automation
earned_secret: <one line, filled by Phase 1>
---

# Piece state — <title>

## Progress

- [ ] 01 — Delegation
- [ ] 02 — Description
- [ ] 03 — Discernment
- [ ] 04 — Diligence
- [ ] LinkedIn pair derived

## Process log

(Each phase appends a one-line entry: `2026-05-25T16:13 — Phase 01 passed.`)
```

Every phase updates `current_phase` and appends to `gates_passed` when its gate passes. The status command reads from this file.

## Hard rules

- **Never auto-commit or auto-push.** The plugin writes to disk; the user commits via GitHub Desktop.
- **Never auto-publish to LinkedIn.** Phase 4 writes the article and teaser to disk; the user posts them by hand.
- **Never fabricate citations.** Tier 1-3 sources only; `[F]` data is forbidden in body; unverifiable claims get `[CITATION NEEDED]`.
- **Never skip the Release Owner Gate.** The gate is the whole point of the framework.
- **Never assume the active project.** Always run the discovery walk in STEP 1 and report the resolved project to the user.
- **Never load voice silently.** STEP 0 loads voice anchor + reports back what was loaded.
