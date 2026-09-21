---
description: Review a repository's retrieval/RAG pipeline for stages that do not do their work
argument-hint: <repo-path> [--json]
---

Review the retrieval pipeline in the repository at $1.

Read `${CLAUDE_PLUGIN_ROOT}/skills/retrieval-review/SKILL.md`, run the checker it names
against $1, and report the result.

Report every FAIL with its `file:line` evidence, and report the SKIPs as coverage the
review did not have rather than omitting them. The checker never executes the pipeline;
say so. If the verdict is NO COVERAGE, say the repository has no retrieval pipeline these
checks can see, and do not present that as a clean review.
