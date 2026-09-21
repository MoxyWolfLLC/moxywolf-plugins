---
name: retrieval-review
description: >
  This skill should be used when reviewing a repository's retrieval or RAG pipeline:
  "review this RAG pipeline", "is the reranker actually doing anything", "audit our
  retrieval", "check the retrieval quality gates", "does this pipeline ground its
  answers", "/review-retrieval". It reviews the pipeline statically and never runs it.
  Do NOT use this skill for general code review (use code-review-pro) or repository
  health (use analyze-repo).
allowed-tools: [Read, Bash, Glob, Grep]
---

# Retrieval review

A retrieval stage that does nothing returns exactly what a working one returns: an
ordered list. A reranker that passes its input through, a top-k that never cuts and a
grounding check that never fires are each a stage reporting work it did not do, and the
pipeline's output looks the same either way. These checks look for the absence directly.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/retrieval_review.py" --repo <path> [--json]
```

Exit 0 when nothing failed, 1 when a check failed, 2 on a usage error.

## What it checks, and what it refuses to claim

| Check | Finds | Cannot establish |
| --- | --- | --- |
| `rerank_effective` | A reranked result that is discarded or bound to a name nobody reads | That the order actually changed at runtime |
| `topk_before_model` | A pipeline file that calls a model with no top-k cut | Whether the cut is large enough |
| `grounding_fallback` | Retrieval with no early exit on an empty or low-scoring result | Whether the threshold is right |
| `citation_attribution` | An answering pipeline that emits no citation or chunk identifier | That each citation resolves to a chunk that was in the context window |

**It never executes the pipeline.** `executed` is `false` in the JSON and the header says
so. Where a claim needs a run, the check returns SKIP with the reason rather than a verdict
it did not earn. That is the point of the item, not a limitation to apologise for.

## Reading the result

Every check reports what it examined. Zero coverage turns a PASS into a FAIL, and a run
where every check skipped reports **NO COVERAGE**, never PASS: a repository these checks
cannot see into has not been reviewed, and saying "pass" would retire the reader's doubt
without earning it.

The unit of analysis is a **pipeline file**: one that both retrieves and calls a model.
A repository that retrieves in one module and answers in another is not examined and says
so through its SKIP count. That is deliberate. Scoping wider was tried and produced untrue
findings both times, and a wrong accusation costs more than a miss that announces itself.

Python only. Files in other languages are counted and reported as unexamined rather than
guessed at with regex.

## After the run

Report each FAIL with its `file:line` evidence, and report the SKIPs as coverage the review
did not have. A SKIP is not a pass and is never folded into a green line. If the summary
says NO COVERAGE, say that the repository has no retrieval pipeline these checks can see,
and do not present it as a clean review.
