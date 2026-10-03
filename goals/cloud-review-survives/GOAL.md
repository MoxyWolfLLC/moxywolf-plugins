## Serves
Fifth objective: session memory

## Outcome
The first real goal (DESIGN.md, Boundary tests, B-e): a session review made in a cloud session can still be read from the vault after the session ends. A review lives in owner-only staging inside the session, which the cloud container deletes with it. It leaves through publish's existing gate (gitleaks over the exact files and Dorian's confirmation of the approval digest), Dorian's choice on 2026-10-03. The agent then copies the published folder into the vault through the linked computer, and `python3 plugins/project-init/scripts/session_record.py read <published folder>` verifies it against its hashes and prints the review, with no staging present.

## Non-goals
- moving the copy into the vault into code: the agent makes it through the linked computer
- changing what publish scans, confirms or writes
- reading a capture or review that was never published
- a reader for anything other than a published folder

## Scenarios
- Given a review published from a session, when the session's staging folder is gone, then read prints the review from the published folder
- A published folder whose files changed after publishing being printed as the review must never happen

## Goal tests
- `tests/test_read.py::Read.test_prints_the_published_review_after_staging_is_gone` (outcome)
- `tests/test_read.py::Read.test_never_prints_a_changed_publication` (invariant)

## Allowed paths
- plugins/project-init/scripts/session_record.py
- plugins/project-init/tests/test_session_record.py
- plugins/project-init/commands/session-review.md
- plugins/project-init/commands/session-end.md
- plugins/project-init/skills/session-end/SKILL.md
- plugins/project-init/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json

## Spend cap
$3

## Provider budgets
- openrouter: $2

## Max calls
15

## Max items
2

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- publish's gate is weakened: a published folder no longer needs gitleaks and Dorian's confirmed digest

## Pre-mortem
- read prints the review without checking the hashes, so an edited copy in the vault reads as genuine
- read depends on staging, so it only works inside the session that made the review
- the cloud instructions name a vault folder the linked computer can't reach, and the copy is never made
