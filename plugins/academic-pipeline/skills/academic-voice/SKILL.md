---
name: academic-voice
description: Capture the author's voice for an academic piece — the standing voice profile from the MoxyWolf vault plus eight article-specific questions (trigger, evidence, contrarian take, authority, reader, business connection, call to action, emotional core). Stage 3 of the academic-pipeline. Use to inject authentic authorial voice before drafting so the first draft already sounds human.
license: Proprietary - MoxyWolf LLC
---

# Academic Voice — Stage 3

Two layers of voice feed the writer. This stage captures both:

1. **Standing voice** — how this author writes *in general*. It lives in a profile file and rarely changes. The pipeline reads it; it does not re-interview for it.
2. **Article voice** — why *this* piece exists, what it argues, who it is for. This is captured fresh every run, with eight short questions.

The result, `voice_context.json`, lets Stage 6 (`research-writer`) draft in an authentic voice from the first word instead of retrofitting one afterward.

## Role in the pipeline

Third stage of the `academic-pipeline`. Runs after `academic-perspective-builder` (Stage 2) and before `academia-formatting` (Stage 4). The `academic-pipeline` is voice-first by design: voice and formatting are fixed *before* writing, never patched in after.

## Inputs

- **Required:** the topic and perspective — Stage 2's `perspective.json`.
- **Optional run folder** — from the orchestrator. Write `voice_context.json` to `<run folder>/pipeline/`.

## Layer 1 — Standing voice profile

Read the canonical author voice profile. For MoxyWolf work this is:

`MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md`

It encodes the durable rules — no em dashes, ~80% contractions for general writing (academia-formatting dials this to ~50% for scholarly register), asymmetric paragraph architecture, typographer's quotes, the two-reader frame, the "keep The Main Thing the Main Thing" framing, the David-sentence test. The raw extraction interview sits beside it (`dorian-cougias-raw-qa.md`) and is worth reading when a passage needs more voice than the rule summary captures.

Record the profile **path** in `voice_context.json` rather than copying its contents — the writer reads the live file.

**If the profile is not found** (the plugin is running outside the MoxyWolf vault, or for a different author): do not guess a voice. Ask the user where their voice profile lives, or — if they have none — run a short standing-voice mini-interview (three questions: sentence rhythm and length habits; punctuation and formatting tics; words or phrases they never use) and save the answers into `voice_context.json` under `standing_voice_inline`.

## Layer 2 — The eight article questions (HITL)

This is an **interactive** stage. Ask all eight questions with the **AskUserQuestion tool**, in short batches (e.g. groups of two to four), each question offering a few example angles plus the free-text path — these answers are inherently personal, so expect free text. If the user would rather just talk it through, take the answers conversationally. If the orchestrator front-loaded the answers, skip the interview and go straight to *Generate output*. Never block on a HITL request file.

1. **trigger** — What triggered this piece? What conversation, client situation, paper, or frustration put it in motion?
2. **evidence** — What have you actually seen? Give one real, specific example — a case, a number, a moment.
3. **contrarian_take** — What does most of the field get wrong here? Where is the conventional wisdom broken?
4. **authority** — Why should anyone listen to you on this? What experience shaped how you see it differently?
5. **specific_reader** — Who, specifically, is this for? What keeps that person up at night?
6. **business_connection** — How does this connect to MoxyWolf — to the products, the practice, the thesis?
7. **call_to_action** — What should the reader actually *do* after finishing?
8. **emotional_core** — What about this genuinely angers you, excites you, or worries you?

These eight map to concrete spots in an academic paper: *trigger* and *authority* anchor the Introduction's hook; *evidence* grounds Results or the worked example; *contrarian_take* sharpens the contribution statement and Discussion; *specific_reader* keeps register and examples honest; *business_connection* and *call_to_action* drive the Conclusions; *emotional_core* is the through-line that keeps the prose from going flat.

## Generate output

Write **`<run folder>/pipeline/voice_context.json`**:

```json
{
  "topic": "<TARGET_TITLE from perspective.json>",
  "standing_voice_profile_path": "MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md",
  "standing_voice_inline": null,
  "trigger": "<answer>",
  "evidence": "<answer>",
  "contrarian_take": "<answer>",
  "authority": "<answer>",
  "specific_reader": "<answer>",
  "business_connection": "<answer>",
  "call_to_action": "<answer>",
  "emotional_core": "<answer>",
  "created_at": "<ISO 8601 timestamp>"
}
```

Set `standing_voice_profile_path` when the vault profile was found; otherwise leave it `null` and fill `standing_voice_inline` with the mini-interview answers.

## Return to the orchestrator

```json
{
  "status": "complete",
  "output_file": "<run folder>/pipeline/voice_context.json",
  "standing_voice_resolved": true
}
```

## Notes

- This stage captures voice; it does not write prose. The writer (Stage 6) applies it.
- Standing voice is read, never re-interviewed — re-interviewing the author every run is the kind of friction this stage exists to remove.
- The eight answers are this article's fingerprint. Capture the author's actual words; do not smooth them into generic statements.
