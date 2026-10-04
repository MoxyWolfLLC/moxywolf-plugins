## Serves
Fifth objective: session memory

## Outcome
`python3 plugins/project-init/scripts/session_record.py list <folder>` lists every published review folder directly inside a vault session-records folder, one line each, verified or refused by the same checks `read` makes. Reviews that outlived their cloud sessions can then be found, not only read one at a time. This is goal mode's acceptance run, second attempt. The first, vault-review-list, failed its holdout: an empty folder printed its message only on standard error, and the holdout read "says so" as standard output. This brief and plan say which stream; the goal tests are the same, and the holdout is new. It must go from start to merge with no intervention but Dorian's approvals.

## Non-goals
- searching inside reviews
- looking below the folder's direct children
- changing what `read`, `publish` or `capture` do

## Scenarios
- Given a folder holding two published reviews, then list prints one verified line naming each publication
- A changed published folder being listed as verified must never happen

## Goal tests
- `tests/test_list.py::List.test_lists_each_published_review` (outcome)
- `tests/test_list.py::List.test_never_lists_a_changed_publication_as_verified` (invariant)

## Allowed paths
- plugins/project-init/scripts/session_record.py
- plugins/project-init/tests/test_session_record.py
- plugins/project-init/commands/session-review.md
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
- the marketplace's top-level version moves on the goal branch

## Pre-mortem
- list prints verified without making read's checks, so an edited copy lists as genuine
- list counts a folder that isn't a publication as verified
- an empty folder lists nothing and exits 0, which reads as a clean vault
- a message meant for the person goes only to standard error, where a caller reading the listing never sees it
