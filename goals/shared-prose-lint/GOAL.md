## Serves
Thirteenth objective: blog publishing

## Outcome
Dorian, 2026-11-13: "Write a goal to focus on items 1 through 3 without requiring my intervention." This goal is the second of those items, BP-002's "what's not taken": the academic pipeline and `/blog-social` run BP-002's `prose_lint.py` before anything leaves them, and a test keeps every copy identical to the 4d-blog-engine original.

## Non-goals
- changing what `prose_lint.py` flags or how it grades
- a second copy of the lint that can drift from the 4d-blog-engine original
- scoring a Minor finding as a reason to hold a social post back
- posting anything to LinkedIn, X or Facebook

## Scenarios
- Given an abstract with three short same-shape sentences in a row and a "Here's where" opener, when the academic pipeline's copy of the lint runs on it, then it reports a parallel_run and a here_opener finding
- Given the same text as a LinkedIn post, when social_score.py checks it, then it reports the parallel_run and here_opener findings by rule id and fails the check
- The 4d-blog-engine lint grading a fixed text differently from how it grades it today must never happen
- social_score.py failing a clean post that passes its format checks today must never happen

## Goal tests
- `tests/test_shared_lint.py::SharedLint.test_academic_copy_reports_run_and_here_opener` (outcome)
- `tests/test_shared_lint.py::SharedLint.test_social_score_reports_lint_findings_and_fails` (outcome)
- `tests/test_shared_lint.py::SharedLint.test_original_lint_grades_fixed_text_as_today` (invariant)
- `tests/test_shared_lint.py::SharedLint.test_social_score_passes_clean_post_as_today` (invariant)

## Allowed paths
- plugins/academic-pipeline/scripts/prose_lint.py
- plugins/academic-pipeline/scripts/test_prose_lint_copy.py
- plugins/academic-pipeline/references/ai-anti-patterns.md
- plugins/academic-pipeline/commands/academic-pipeline.md
- plugins/academic-pipeline/commands/academic-critique.md
- plugins/academic-pipeline/skills/academic-pipeline-orchestrator/SKILL.md
- plugins/academic-pipeline/README.md
- plugins/academic-pipeline/.claude-plugin/plugin.json
- plugins/4d-blog-engine/scripts/social_score.py
- plugins/4d-blog-engine/tests/test_social_score.py
- plugins/4d-blog-engine/skills/blog-social/SKILL.md
- plugins/4d-blog-engine/commands/blog-social.md
- plugins/4d-blog-engine/README.md
- plugins/4d-blog-engine/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json

## Spend cap
$4

## Provider budgets
- openrouter: $3

## Max calls
25

## Max items
3

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- plugins/4d-blog-engine/scripts/prose_lint.py changes
- a deploy to any environment other than goal-holdout; the repository reports no other environment, so any deploy at all is Dorian's call

## Pre-mortem
- the academic copy is a paraphrase or an older version, so it passes on the test text but grades other text differently
- the identity test compares the copy with itself, or with a stored hash that nobody updates when the original changes
- social_score.py prints the lint findings but still exits 0, so the skill shows a post that should be held back
- social_score.py fails every post, including clean ones, because it scores Minor findings or runs long-form rules on a short post
- the pipeline command names the lint step but at a stage after the critique, so the critique reads unlinted prose
