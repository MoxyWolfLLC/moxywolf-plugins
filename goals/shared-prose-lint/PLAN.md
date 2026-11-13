# shared-prose-lint
1. social_score.py runs the lint on every social post
   - `social_score.py` loads `prose_lint.py` from its own scripts folder and scans the post in short-form, with no long-form allowance
   - each lint finding is printed on standard output in the report it already writes, under a `Prose lint` heading, one line per finding naming its rule id and severity
   - a Major or Medium lint finding makes the check fail: exit 1; a Minor finding is printed and doesn't change the exit code; a missing file still exits 2 with its message on standard error
   - a post with no lint finding gets the same exit code and format verdict it gets today
   - `skills/blog-social/SKILL.md` and `commands/blog-social.md` say a post that fails on a lint finding is held back and the finding named to the writer
   - `tests/test_social_score.py` covers a post with a parallel run (exit 1), a post with only a closing zinger (exit 0) and a clean post (exit 0)
2. The academic pipeline carries an identical copy and runs it before the critique
   - `plugins/academic-pipeline/scripts/prose_lint.py` is byte-identical to `plugins/4d-blog-engine/scripts/prose_lint.py`, and `plugins/academic-pipeline/references/ai-anti-patterns.md` is byte-identical to the 4d-blog-engine catalog
   - `plugins/academic-pipeline/scripts/test_prose_lint_copy.py` compares both pairs byte for byte and fails, naming the file, the moment either differs
   - `commands/academic-pipeline.md`, `commands/academic-critique.md` and the orchestrator skill run `prose_lint.py --report` on the article before Stage 8, in long-form with the voice profile's signature devices, and the critique receives the findings file
   - the lint's own exit codes are unchanged: 1 on a D or F grade, 0 otherwise; the pipeline stops before the critique on exit 1 and names the grade
3. Versions and the suites
   - academic-pipeline and 4d-blog-engine each move a minor version in `plugin.json`, their marketplace entries and their README version history; the marketplace's top-level version is left for the release
   - `run_all_tests.py` names `test_social_score.py` and `test_prose_lint_copy.py` among the suites it ran and reports no failures
