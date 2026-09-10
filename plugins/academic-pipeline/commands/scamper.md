---
description: SCAMPER defixation on a literature baseline — seven operators, novelty-scored candidate theses, and a paper outline for the top-ranked one (between Stage 1 and Stage 2)
argument-hint: [--topic "..."] [--baseline-json path] [--generate-outline] [--operator substitute|combine|adapt|modify|put_to_another_use|eliminate|reverse] [--output json|markdown]
---

Run the SCAMPER defixation pass on the current literature baseline. Stdlib Python, no install.

1. Build the baseline. From a Stage 1 run, distill `pipeline/theme_analysis.json` into a JSON file with `topic`, `consensus_claims`, `theoretical_frameworks`, `methodologies`, `implicit_assumptions` (lists of short strings) and save it as `pipeline/scamper_baseline.json`. With no run folder, pass `--topic` and the built-in demo baseline is used.
2. Run it: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scamper.py" --baseline-json <path> --generate-outline $ARGUMENTS`. Drop `--generate-outline` to see the ranked table of all seven candidates first; add `--output json` when a downstream stage will consume it.
3. Show the ranked candidates (novelty score 0–10, tier, thesis). Confirm the thesis with the user via AskUserQuestion before it becomes the Stage 2 perspective input; the top novelty score is a proposal, not a decision.
4. Write `pipeline/scamper_results.json` and, when an outline was generated, `pipeline/scamper_outline.md` to the run folder.

The script scores novelty as TF-IDF cosine distance from the baseline texts. Without an LLM client it uses built-in mock candidates, so the value of this pass is the operator prompts and the scoring frame; generate the real candidates yourself from the prompts in `ScamperPromptTemplates` when the mock output is not enough.

Programmatic use from another script: `from scamper import run_scamper_pipeline; run_scamper_pipeline(baseline_dict_or_path, generate_outline=True)` returns `{"scamper": ..., "outline": ...}`.
