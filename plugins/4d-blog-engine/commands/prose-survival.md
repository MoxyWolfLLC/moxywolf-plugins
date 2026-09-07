---
description: "How much of Claude's sampled wording survives in a file — paper, email, README, post. Reads the baseline captured on first write. Usage: /prose-survival <file> [--brief] [--gate]"
argument-hint: "<file> [--brief] [--gate] [--threshold N]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob"]
---

Read `${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_text.py` before running it. Its module
docstring is the contract, and the first section of that docstring is what this
command does **not** do.

```bash
S="${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_text.py"
python3 "$S" <file>                      # baseline resolved automatically
python3 "$S" <file> --brief              # + which paragraphs to rewrite first
python3 "$S" <baseline> <file>           # explicit pair
```

## Where the baseline comes from

Two places, in order:

1. **A sibling `*.raw.*`** — what `/blog-discern` writes at Phase 3 step 8.
2. **The shadow store** — `~/.claude/prose-baselines/`, written by this plugin's
   PostToolUse hook on a file's **first Write**, keyed by absolute path.

The second is what makes this work outside the blog pipeline. Papers from
`academic-pipeline`, sequences from `email-lifecycle`, articles from
`research-pipeline`, anything drafted through Write — all get a baseline with no
per-skill snapshot step to add or forget.

**No baseline means no answer.** Exit code 2, and say so plainly: nothing was
captured before the file was edited, so survival is unmeasurable. Do not
substitute a source document, an outline, or an earlier git revision that has
already been through a rewrite — a baseline that was never Claude-sampled gives
a confident meaningless number.

## What the number is, and is not

Claude's output carries a SynthID-Text-class watermark, in the choice among
equally valid words, on every Anthropic surface with no opt-out. Anthropic's
support page names when it stops being reliably detectable: text *"heavily
edited, paraphrased, translated, or mixed into other writing"*, or too short to
carry a signal.

This measures token-sequence survival, which is the **input** the mark rides on.
It is a proxy and must be reported as one. Detection needs a cryptographic key
we do not hold and is in private preview. **Never tell the writer a file is
"clean" or "de-watermarked".** Give the number.

## Rewrite direction — the part that matters

`--brief` ranks the paragraphs still carrying the most original wording. Rewrite
those **toward the writer's voice profile**, not away from the draft.

Both directions perturb the token sequence; only one improves the prose.
Rewriting toward entropy is what a generic de-watermarker does, and the upstream
project concedes in its own README that it degrades quality. Rewriting toward the
voice profile perturbs the same distribution and makes the piece more the
writer's.

After any rewrite, re-run `prose_lint.py --report`. **A rewrite that lowers
survival but drops the prose grade is a failed rewrite** — revert and try again.

For academic work, one extra rule: `research-pipeline`'s citation verifier
establishes claim-to-source correspondence. Rewriting a sentence that carries a
`[V]` datum can break that correspondence without touching the citation. Re-run
`/verify-citations` after rewriting any cited passage.

## Gating

`--gate` exits non-zero above `--threshold` (default 50%). **That number is not
calibrated** — nobody outside the detection preview can validate it against
ground truth, us included. It is a dial, and the `ponytail:` comment at its
definition says so. Report it next to the prose grade; do not wire it into the
Release Owner Gate as a blocking check on an uncalibrated figure.
