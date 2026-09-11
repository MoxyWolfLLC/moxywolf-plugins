# Design: <repo name>

_Canonical copy: `DESIGN.md` at the repo root. Mirror: `Taskade/<project>/06 – Engineering/DESIGN-<repo>.md`. Every change to this file is its own commit (`design: …`) and lands before the code it governs._

## Goal

One paragraph. What this repo is for, who uses it, what "working" means to them. `/gstack-build` reads this first and refuses to build anything that does not serve it.

## Constraints and settled decisions

Bulleted. Architecture choices already made, boundaries not to cross, dependencies not to add, anything a reviewer must not reopen. These become the `exclusions` of every review packet. Change one only through the Amendments log, with the reason.

- 

## Items

One row per unit of work. An item is buildable when its acceptance criteria are checkable statements, not intentions. For a web item, a criterion names the Playwright spec that proves it (`e2e/<area>.spec.ts: <test title>`); Endform runs it against the preview deployment on every push (`.github/workflows/endform-e2e.yml`, added by `/gstack-build` if missing). Status is one of `planned`, `building`, `review`, `done`, `dropped`.

| ID | Item | Acceptance criteria | Status | Review ID / merge |
|---|---|---|---|---|
| I-001 | | 1. … 2. … | planned | |

## Amendments log

Newest first. One line each: date, item or constraint touched, what changed, why, who approved.

- 
