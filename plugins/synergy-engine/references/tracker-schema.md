---
read_when: "synergy-init creates the tracker; synergy-discover/run/status read and write it. The tracker is the engine's memory, dedupe, and queue."
status: canonical
---

# Tracker schema

One xlsx workbook, sheet `Outreach Tracker`, one row per target. Created by `scripts/tracker_init.py`. A second sheet, `How this works`, holds the legend.

## Columns (A..P)

| Col | Field | Meaning |
|---|---|---|
| A | Target | Person/company name |
| B | Persona | `Content` / `Content/peer` / `Citation` / GRC / Builder / Bridge — topic center + persona |
| C | Tier | A (1:1) / B (authority + warm) / C (engagement-only) / peer |
| D | Path | `A` / `B` / `GA` (anchor-paper cite) / `cite-only` / `cited` (citation center: we cited them) |
| E | Synergy | High / Medium / Low / Cold |
| F | LinkedIn Profile | full `/in/<slug>/` URL |
| G | Last Touch | date of last action |
| H | Liked | Yes / No |
| I | Commented | Yes + date |
| J | Comment / engagement summary | one-line on the post + our angle |
| K | Cited URL | the answer page / anchor-paper URL cited (Path A / GA) |
| L | Connect / DM | status + date |
| M | Status | see below |
| N | Next Action | the exact next move (for Queued rows, include the post URL to engage) |
| O | Next Action Date | drives the queue |
| P | Notes | competitor flag, discovery source, anything durable |

## Status values

`Not started` · `Queued` (discovered, drafted, awaiting a run) · `Ready for review` (scheduled task staged drafts) · `Posted` · `Pending accept` (connection sent) · `Accepted` · `Replied` · `Engaged` · `Parked` · `Cold`

## Dedupe rule

Before discovery, collect the set of `publicIdentifier`s already present (any status) and pass it as the exclude-list to scoring, so already-tracked authors don't resurface. Before a run, a target is **due** if `Status = Not started/Queued/Ready for review`, or `Status in {Posted, Accepted, Engaged}` and `Next Action Date <= today`. Skip `Parked`.

## Synergy colors

Green = High, yellow = Medium, orange = Low, grey = Cold/Parked. Queued rows get a pale-yellow Status cell.

## Citation center

The citation center (`/synergy-cite-harvest`) keeps its detail in a separate, richer **citation registry** workbook (`references/citation-registry-schema.md`) because cited-author records carry ORCID, affiliation, enrichment, LinkedIn-confidence, and draft-email fields this 16-column tracker doesn't. Harvest still appends a light queue row here per ready-to-send person (`Persona = Citation`, `Path = cited`, `Cited URL` = the anchor paper) so `/synergy-status` shows all three centers in one view. The registry is the source of truth for the citation center; this tracker is the cross-center queue.
