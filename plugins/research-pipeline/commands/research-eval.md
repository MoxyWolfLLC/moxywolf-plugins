---
description: Grade a finished article's claims against the sources it cites — grounding rate, overstated claims, source coverage, run cost
argument-hint: [article path or library name] [--focus <section|claim|citation>] [--full]
---

Load the `research-evaluator` skill and evaluate the article named or pathed in "$ARGUMENTS".

`/verify-citations` proves the sources exist. This proves the sentences citing them actually follow from them — the failure that survives every other check in the pipeline.

Resolve the target first. A path is the article. A library name means the most recent article produced from that library. Nothing at all means the article this session produced or last worked on; if that's ambiguous, ask once rather than guessing — evaluating the wrong draft wastes the whole run.

Scope next. `--focus <section|claim|citation>` runs a narrow pass and is the right default when someone is challenging one specific thing; it costs cents. `--full` walks the whole article. Without either, propose the full pass with its cost estimate and get a go before spending.

Steps:

1. Extract the load-bearing claims — the ones whose falsity would change the argument. Skip the author's own framing, transitions, and common-term definitions.
2. Resolve each claim to the source it cites, pulling real source text (full text for numeric claims, not just the abstract).
3. Grade each claim SUPPORTED / PARTIAL / UNSUPPORTED / CONTRADICTED / UNCITED / UNVERIFIABLE, judged by a different model than the one that wrote the article — Council's OpenRouter dispatch, or an isolated-context sub-agent as fallback.
4. Report grounding rate, source coverage, citation load, and run cost, findings worst-first, each with the claim, what the source actually says, and a one-line fix.
5. Stop. Offer to soften the PARTIAL claims, to send the UNSUPPORTED and UNCITED ones to `/discover-literature` as targeted gap queries, or to re-run on a revised draft — but make no edits. This is a human-decision queue.

Write the summary numbers to the library metadata so grounding rate is tracked draft over draft.
