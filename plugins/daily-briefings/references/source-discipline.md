# Source discipline — three states, and never plotting a guess

Both briefings assert things about the owner's life: you are somewhere at some time, this is due, you have not replied to that. A briefing that quietly gets one wrong is worse than no briefing, because it will be trusted. Two rules carry most of the weight.

## Rule 1 — a source you could not read is `not checked`, never empty

Every source has three states, not two.

| State | Means | How it renders |
|---|---|---|
| `ok` | The source answered. Zero results is a real finding. | Normal. A quiet day renders as a quiet day. |
| `unavailable` | The source was reached and refused, errored, or is not connected. | Named in the footer caveats: "Slack not connected — chat not checked." Any section that depends on it says so in place rather than rendering blank. |
| `not checked` | Deliberately skipped — the config disabled it, or checking it was too expensive to be worth the run. | Named in the footer, with the reason. |

The failure this prevents is specific and it is the one that actually happens: the calendar reads fine, Gmail is not connected, and the grid renders a clean two weeks. It looks like good news. It is a blind spot wearing the costume of good news. **An unread source and an empty source must never produce the same pixels.**

Track a small status map as you gather — one entry per source, one of the three states, plus a one-line reason for anything that is not `ok` — and render it in the footer whether or not anything went wrong. A footer that always names its sources is a footer whose silence means something.

## Rule 2 — only explicit dates get plotted

A calendar event carries its own date and time; it is plottable by construction. Everything harvested from email is not, and the bar for promoting it onto the grid is deliberately high:

- The date must be **explicit in the message body**, confirmed by reading the message, not inferred from the subject line, not inferred from the received date, and not inferred from a phrase like "next Thursday" unless the message also states which Thursday.
- Times in another timezone are **converted to `owner.timezone`, and the conversion is shown** in the chip note: `18:00 UTC → 11:00 PT`. Showing the arithmetic is what lets the owner catch it when it is wrong.
- An email-sourced chip is **prefixed `✉`** so the owner can tell at a glance which commitments the calendar does not know about.
- Anything real but **undated** goes to *Open loops*, never onto the grid. An ask with no date is a different kind of object and it deserves its own section rather than a made-up slot.

When a date is ambiguous, put the item in *Open loops* with the ambiguity stated. Do not pick the more likely reading and plot it.

## Provenance in the render

Every chip carries where it came from: the calendar name for calendar events, and for email the sender plus the thread subject, short enough to fit. The footer names every source consulted, the state of each, and the fetch timestamp in `owner.timezone`. That timestamp is what tells a reader looking at yesterday's file that they are looking at yesterday's file.

No claim in either render may exist without a source behind it. If a would-be chip cannot name where it came from, it does not go in.

## Noise suppression is a filter, not a verdict

`inbox.noiseSenders` and `inbox.noiseSubjects` suppress newsletter and blast traffic from the sweep. Two limits on that:

- A suppressed message that carries a **real deadline the owner has engaged with** (they replied, or it is a response to something they sent) is not noise. Let it through.
- Suppression is **counted and reported**: "142 newsletter and blast messages suppressed." A reader who knows how much was filtered can judge whether the filter is set right. A filter that reports nothing is indistinguishable from an empty inbox.
