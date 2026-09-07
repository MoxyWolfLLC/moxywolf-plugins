---
description: "Measure how much of Claude's sampled wording survives to publish, and drive a voice-preserving rewrite of what does. Usage: /blog-rewrite <raw.md> <live.md> [--gate] [--threshold N]"
argument-hint: "<raw.md> <live.md> [--gate] [--threshold N]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob"]
---

Read `${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_text.py` before running it. Its module
docstring is the contract, and the first section of that docstring is what this
command does **not** do.

## What this is

Claude's text carries a SynthID-Text-class watermark, in the choice among equally
valid words. Anthropic's support page names the conditions under which it stops
being reliably detectable: text *"heavily edited, paraphrased, translated, or
mixed into other writing"*, or too short to carry a signal.

This command measures whether a piece is actually in that state instead of
assuming it, then briefs the rewrite of the parts that are not.

## What this is not

**It cannot verify removal.** Detection needs a cryptographic key we do not hold,
and it is in private preview. This measures token-sequence survival, which is the
input the mark rides on — a proxy, and it must be described as one. Never tell the
writer a piece is "clean" or "de-watermarked". Report the number.

## Run it

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_text.py"
python3 "$S" <piece>/03-discernment/draft.raw.md <piece>/03-discernment/draft.md --brief
```

`draft.raw.md` is the snapshot taken in Phase 3 before the slop rewrite. Without
it there is no baseline and this command cannot run — say so rather than
substituting the base document, which was never Claude-sampled and would give a
meaningless number.

## Rewrite direction — the part that matters

The brief lists the paragraphs still carrying the most original wording. Rewrite
those **toward the writer's voice profile**, not away from the draft.

Both directions perturb the token sequence. Only one of them improves the prose.
Rewriting toward entropy — what a generic de-watermarker does — resamples the
distribution and degrades quality, which the upstream project concedes in its own
README. Rewriting toward the voice profile resamples it and makes the piece more
the writer's. Same mechanism, opposite outcome.

So: load the voice profile, rewrite the flagged paragraphs as the writer would
have written them, then re-run `prose_lint.py --report`. **A rewrite that lowers
survival but drops the prose grade is a failed rewrite** — revert it and try again.

## Gating

`--gate` exits non-zero above the threshold. Default is 50% and it is **not
calibrated** — nobody outside the detection preview can validate it against
ground truth, including us. It is a dial. The `ponytail:` comment in the script
says so at the definition.

Do not wire `--gate` into the Release Owner Gate as a blocking check on an
uncalibrated number. Report it alongside the prose grade and let the named signer
weigh it.
