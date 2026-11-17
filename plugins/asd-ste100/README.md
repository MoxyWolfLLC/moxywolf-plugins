# asd-ste100

Rewrites text that an agent will build or act from into ASD-STE100 Simplified Technical English, so a reader with no one to ask can't misparse it.

## Scope

Use it for DESIGN.md items and amendments, goal briefs and plans, review contracts and acceptance criteria, SKILL.md files and command descriptions, tool descriptions and error messages.

Never use it for MoxyWolf published prose: blog posts, articles, papers, email, LinkedIn posts, or anything written in Dorian's voice. Drafts are excluded too, and so is that prose when an agent reads it. Text that quotes Dorian stays verbatim wherever it appears.

The skill's own `## MoxyWolf scope` section says the same and overrides upstream's broader triggers.

## The linter

`skills/asd-ste100/scripts/ste-lint.py` is upstream's stdlib-only linter for STE's structural rules. Its findings and exit status are advice and never gate design, review, merge or release. Its `--selftest` runs in this repository's `run_all_tests.py`, and a broken self-test fails CI.

The skill and the linter check sentence structure only. They don't establish ASD dictionary compliance: the ~900-word approved dictionary isn't included.

## Source

Vendored from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) at `707362731928d0d92526c066df15dbbe6a378c07` (MIT). `SKILL.md` is modified (see `NOTICE`); every other upstream file is verbatim. Not taken: upstream's `.claude-plugin/` manifests and its README. Design item: ST-001 in the repository's `DESIGN.md`.

## Version history

- **0.1.0**: ST-001. First vendor of upstream at `7073627`, with the MoxyWolf scope section.
