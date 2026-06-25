---
read_when: "synergy-cite-harvest creates the registry; synergy-cite-run and synergy-cite-accept-check read and update it. The registry is the citation center's memory, dedupe, and queue."
status: canonical
---

# Citation registry schema

One xlsx workbook per source paper, built by `scripts/citation_registry.py`. Three sheets: `Cited Authors` (one row per reachable person), `Non-targets` (the bibliography entries that aren't reachable people), and `How this works` (legend). This is the citation center's richer parallel to the post tracker; it carries the enrichment, LinkedIn-confidence, and draft fields the 16-column post tracker doesn't.

## Sheet 1 — `Cited Authors` (columns A..V)

| Col | Field | Meaning |
|---|---|---|
| A | Author | Display name |
| B | Priority | `load-bearing` / `primary author` / `co-author` |
| C | ORCID | dedupe key across works |
| D | Cited Affiliation | institution as cited (from OpenAlex) |
| E | Cited Works | the work(s) of theirs we cited (title + year) |
| F | Sections | section(s) of our paper that cite them |
| G | How Used | one-line on the claim their work supports |
| H | Apollo Title | role from Apollo |
| I | Current Org | current employer (catches "moved") |
| J | Org Domain | for the work email |
| K | Email | work email (verified or org-domain) |
| L | Email Status | `verified` / `unavailable` / `unknown` / `extrapolated` |
| M | Verify | `ok` / `REVIEW` / `FALSE POSITIVE - exclude` (the verify gate) |
| N | Moved | cited vs current affiliation note |
| O | LinkedIn URL | full `/in/<slug>/` |
| P | LinkedIn Conf | `verified (Apify)` / `REVIEW (Apify)` / `WRONG (Apify) - namesake` / `unverified (private profile)` / `sent/confirmed` |
| Q | Email Sent | date |
| R | Connect Sent | date |
| S | Status | see below |
| T | Next Action | the exact next move |
| U | Draft Email | the "we cited you" email body (their ref -> how used -> our paper once) |
| V | Draft Connect Note | the hook-free connect note (<=300 chars) |

## Status values (col S)

`Not started` · `Drafted` · `Email sent` · `Connect pending` · `Accepted` · `Replied` · `Engaged` · `Excluded` (verify gate / unreachable) · `Held` (e.g. extrapolated email awaiting confirmation)

## Sheet 2 — `Non-targets`

| Col | Field |
|---|---|
| A | Reference | the bibliography entry as written |
| B | Type | `organization` / `legal case` / `statute` / `classic-unreachable` |
| C | Note | why it's not a reachable person |

## Dedupe rule

ORCID (col C) is the primary dedupe key; normalized name is the fallback. Before a re-run, pass every ORCID/name already in `Cited Authors` as the exclude-list so the harvest doesn't re-resolve or re-enrich them. Before `/synergy-cite-run`, a row is **due to email** if `Email Status in {verified, unavailable-with-org-domain}` and `Email Sent` is blank; **due to connect** if `LinkedIn Conf = verified` and `Connect Sent` is blank and the daily ceiling allows.

## Colors

`Verify = FALSE POSITIVE` and `Status = Excluded` rows get a grey fill. `Priority = load-bearing` gets a bold author cell. `LinkedIn Conf = verified (Apify)` gets a green Conf cell; `WRONG`/`REVIEW` get orange.

## Relationship to the post tracker

The registry is the citation center's source of truth. `/synergy-cite-harvest` also appends a light queue row per ready-to-send person to the post tracker (`Persona = Citation`, `Path = cited`, `Cited URL` = our anchor paper) so `/synergy-status` shows both centers in one view. The registry holds the detail; the tracker holds the cross-center queue.
