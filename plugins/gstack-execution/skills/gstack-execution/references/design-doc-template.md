# Design: <repo name>

_Canonical copy: `DESIGN.md` at the repo root. Mirror: `Taskade/<project>/06 – Engineering/DESIGN-<repo>.md`. Every change to this file is its own commit (`design: …`) and lands before the code it governs._

## Goal

One paragraph. What this repo is for, who uses it, what "working" means to them. `/gstack-build` reads this first and refuses to build anything that does not serve it.

## Constraints and settled decisions

Bulleted. Architecture choices already made, boundaries not to cross, dependencies not to add, anything a reviewer must not reopen. These become the `exclusions` of every review packet. Change one only through the Amendments log, with the reason.

- 

## Items

Every item declares the evidential links it introduces. A link is a place where the
system will hold a NAME and a reader will assume a RELATIONSHIP: an identifier, a cache
key, a retained handle, a resume point, a declaration of what a handler reads or writes.
Names are cheap to keep and expensive to verify, so they persist after the thing at the
other end has changed, and the report stays complete while being wrong about its subject.
Copying someone else's list is the smaller half of the lesson: derive this one from what
THIS change actually introduces, before anything built on it starts producing reports
that look complete. An item that introduces state and declares no links is not ready.

One row per unit of work. An item is buildable when its acceptance criteria are checkable statements, not intentions. For a web item, a criterion names the Playwright spec that proves it (`e2e/<area>.spec.ts: <test title>`); Endform runs it against the preview deployment on every push (`.github/workflows/endform-e2e.yml`, added by `/gstack-build` if missing). Status is one of `planned`, `building`, `review`, `done`, `dropped`.

| ID | Item | Acceptance criteria | Links this item introduces | Status | Review ID / merge |
|---|---|---|---|---|---|
| I-001 | | 1. … 2. … | e.g. "cache key over declared deps only"; "review id retained across resume"; "none" | planned | |

## Amendments log

Newest first. One line each: date, item or constraint touched, what changed, why, who approved.

-

## On the objective preamble

State the premise and what prompted the objective. Do **not** restate which items are built, merged,
or pending: each item's `**Status:**` field carries that, and a preamble repeating it is a second
home that drifts on the first merge touching one of them. Observed 2026-09-17, where a preamble read
"XE-002 through XE-004 are declared and not started" while the three statuses beneath it said done.
