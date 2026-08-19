# Flag detection

Five flags. Each one is a rule you can check mechanically, and each one exists because it catches a mistake the owner would otherwise make in person.

## 1. Double-booking

Two **timed** events on the same day whose intervals overlap. All-day events do not participate — they overlap everything and would flag the whole window.

Overlap means `startA < endB && startB < endA`. Touching edges are not an overlap: a call ending at 10:00 and another starting at 10:00 is a tight day, not a clash.

Render: red tint on the day cell, red outline on both offending chips, and one short red line in the cell naming the conflict.

## 2. Duplicate calendar entries

A double-booking whose two events are **effectively the same title** — the calendar has collected the same invite twice, which is common on any calendar that has been accepting invitations for years.

"Effectively the same" means: case-insensitive, punctuation and whitespace normalised, and common invite decoration stripped from both ends — `Re:`, `Fwd:`, `Invitation:`, `Updated invitation:`, `Canceled:`, a trailing `@ <place>`, a trailing parenthetical, and any trailing organiser or attendee name. If what remains matches, it is a duplicate.

This is still surfaced — it is clutter worth cleaning — but it is labelled *duplicate calendar entries* and counted separately from real clashes. Conflating the two makes the clash count useless, and the clash count is the number the owner actually acts on.

Render: the same red treatment, but the explanatory line says duplicate, and the stats strip counts it under duplicates rather than clashes.

## 3. Location clash

A locally-anchored event falling inside a travel span in another city.

- A **locally-anchored event** is one whose location matches an entry in `anchors.localVenues`, matched on address first and label second.
- A **travel span** is a multi-day event, or a run of events, that puts the owner in a different city: flights, hotel reservations, a conference with a city in its location. Take the span from the earliest departure to the latest return.
- If a locally-anchored event sits inside that span and its venue's city differs from the span's city, that is a clash: a standing local commitment that has not noticed the trip.

Render: the same red flag treatment, with the line naming both the venue and the trip.

If `anchors.localVenues` is empty this check produces nothing, which is correct and does not need a caveat.

## 4. Unprepped deadline

A hard deadline with **no prep block on the calendar in the three days before it**. A prep block is any event whose title suggests preparation — `prep`, `focus`, `draft`, `review`, `write`, `rehearse`, `practice`, `block` — matched case-insensitively.

Flag every one. Do not rank them, do not suppress the ones that look easy, and do not decide on the owner's behalf that something needs no preparation. The point of the flag is that the owner makes that call with the list in front of them.

Render: a red `▲` on the deadline chip, plus a card in the *Deadlines & the prep that is missing* section naming the deadline, its date, and the three-day window that is empty.

A deadline landing in the **first three days of the window** has a partly-invisible prep window, because some of it is in the past. Flag it, and say the window is partly outside the render rather than implying the calendar was clear.

## 5. Zero-duration entries

An event whose start and end are identical. These are usually reminders rather than commitments.

Render them without a duration, and say so — a one-line footer note that N entries carry no duration is enough. Do not silently give them a fifteen-minute box; an invented duration is an invented commitment.

## Counting for the stats strip

- **commitments** — every chip on the grid, calendar and email alike.
- **hard deadlines** — chips in the Deadline category.
- **real clashes** — double-bookings that are *not* duplicates, plus location clashes.
- **duplicate entries** — double-bookings that are duplicates.
- **deadlines with no prep blocked** — the flag-4 count.

Keep clashes and duplicates in separate columns. The whole reason to tell them apart is so the first number stays honest.
