# The render

Both briefings are one self-contained HTML file: all CSS inline, no external assets, no fonts fetched over the network, no `localStorage`, no scripts that need anything to be running. The file has to work from disk, on a plane, a week after it was written.

They should also look like siblings. Same type scale, same colour logic, same flag language — so a reader who has learned one has learned the other.

## Tone

Restrained and print-friendly. System font stack. Generous whitespace. No emoji decoration beyond the flag marks (`▲` for an unprepped deadline, `✉` for an email-sourced chip). The document should look like something a careful person made, not like something a tool generated.

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

Add a small `@media print` block: drop background tints to hairline borders, avoid breaking a week row across pages, and keep the flag colours legible in greyscale by pairing every colour with a mark. Colour alone must never be the only carrier of meaning — every red cell also has words in it.

## Category colour

Each category gets a **soft background** and a **saturated left border** of the same hue. The border does the identifying; the background does the grouping. Keep backgrounds pale enough that black body text stays comfortably readable on them.

Assign hues in the order categories appear in `config.categories` so the mapping is stable between runs. A category derived at render time that is not in the config takes the next unused hue and is named in the footer.

Contrast floor: body text on any chip background at 4.5:1 or better. If a hue cannot make that, darken the text rather than brightening the chip.

## The grid

- Week rows, one cell per day, `window.weekStartsOn` first.
- The grid starts at the week-start on or before the window's first day and ends at the week-end on or after its last, so weeks are always whole. Days outside the window are dimmed, not omitted — a dimmed Sunday is how the reader knows the week is whole.
- Today's cell is marked distinctly from both the in-window and out-of-window states. Three visual states, clearly three.
- Chips carry start time and title. All-day items carry no time. Zero-duration items carry a start and no duration.
- A day with nothing in it stays empty and keeps its full height. Collapsing empty days makes a light week look like a missing week.

## Flags

Flag styling is defined in `flag-detection.md`; the render obeys it. The one rule that belongs here: a flagged cell gets tint, outline, **and words**. Never a colour on its own.

## Sections

Above the grid:

- A **legend** naming every category in use plus the flag key.
- A **stats strip** — commitments, hard deadlines, real clashes, duplicate entries, deadlines with no prep blocked. Five numbers, no more. Clashes and duplicates stay separate columns.

Below the grid:

- **Deadlines & the prep that is missing** — one card per unprepped deadline: what is due, when, and which three-day window is empty.
- **Open loops with no date on them yet** — everything real that could not be plotted because nothing authoritative gives it a date. Group by surface, in the order the surfaces appear in `work-surfaces.md`, with a count per group: unanswered email and pending replies, pull requests waiting on a review, tickets in a review state, drafts stalled at a gate, decisions parked at *proposed*, deals past their close date, envelopes unsigned, invoices overdue, a scheduled task that has stopped firing.

  Give this section room. On most days it will be longer than the grid, and that is not a defect — it is the accurate shape of the work. Cap any group that can run long, state the cap on the group, and order groups so the ones with a person waiting on the other end come first.

A section with nothing in it renders as a single line saying so. Do not drop it — its absence would read as "not checked," which is the exact confusion `source-discipline.md` exists to prevent.

## Footer

The footer is not decoration. It carries:

- Every source consulted and its state — `ok`, `unavailable`, `not checked` — with a reason for anything that is not `ok`.
- The fetch timestamp in `owner.timezone`.
- The window's start and end dates.
- Honest caveats: suppressed-message count, any category invented at render time, zero-duration entries, any timezone conversion the reader should check, and the missing-config note if the config was absent.

Write the caveats as sentences. A reader skimming the footer should be able to tell in five seconds whether to trust the grid.
