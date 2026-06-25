---
read_when: "synergy-cite-harvest loads this for the citation-center pipeline: reachability triage, OpenAlex/ORCID resolution, Clarify dedup, Apollo enrich + verify gate, LinkedIn resolution + Apify verification."
status: canonical
---

# Citation Center — start from who you cited

The third discovery center. The author and content centers start from *who's posting*; the citation center starts from *who you already cited in your own paper*, then reaches out to thank them. It's the cite-then-tell lever (see `topic-synergy-methodology.md` Part 4) turned into a front-to-back pipeline: every target is already someone whose work you used, so the open writes itself and warmth is built in.

This is the lever that works on people who don't post, which is most academics. It also lifts your own authority: telling someone you cited them is true flattery, and it gets your paper in front of the exact people who'd reshare it.

## The pipeline

```
bibliography  ->  triage by reachability  ->  OpenAlex (DOI -> authors + ORCID + affiliation)
   ->  dedupe people  ->  Clarify dedup (skip already-enriched)  ->  Apollo enrich (person + org)
   ->  verify gate  ->  LinkedIn resolve + Apify verify  ->  draft email + connect note
   ->  citation registry xlsx + tracker rows
```

The harvest command (`/synergy-cite-harvest`) runs this. Sending is a separate human-gated step (`/synergy-cite-run`). The follow-through on accepted invites is a third step (`/synergy-cite-accept-check`).

## Step 1 — Triage by reachability

Only about half of a bibliography is reachable people. Parse the references and bucket each:

- **individual** — a named human author. The only bucket that proceeds to outreach.
- **organization** — a corporate/institutional author (NIST, an agency, a vendor). Log as a non-target.
- **legal case** — a court decision. Non-target.
- **statute / regulation** — Non-target.
- **classic-unreachable** — a foundational work whose authors are deceased or otherwise unreachable. Non-target.

Write the non-targets to their own sheet so they're never re-processed. Carry, per individual work: title, year, DOI (if any), the section(s) of our paper that cite it, and a one-line "how we used it."

## Step 2 — OpenAlex resolution (DOI to people)

For each individual-authored work with a DOI, resolve authors via the OpenAlex API. Use the sandbox (curl / python); the web-fetch path returns empty on the JSON API.

```
https://api.openalex.org/works/doi:<DOI>
```

Pull, per author: display name, ORCID, last-known institution, and whether they're the corresponding author. ORCID is the dedupe key across works. Works without a DOI get resolved by title search (`?filter=title.search:...`) as a fallback.

## Step 3 — Dedupe people

One author appears across many works. Collapse to one record per person (ORCID first, normalized name as fallback), carrying the union of their cited works and the sections that cite them. Mark a priority: load-bearing (their work is central to a claim) / primary author / co-author.

## Step 4 — Clarify dedup (before Apollo)

Before spending an Apollo credit, check Clarify (the CRM) for an existing enriched person and organization. If the person is already enriched there, reuse it. This saves credits on re-runs and keeps the CRM authoritative. (memory: feedback_clarify_dedup_before_apollo)

## Step 5 — Apollo enrich (person + org), LinkedIn-first

Enrich both the person and their organization via the Apollo MCP.

- **Match by LinkedIn URL first.** LinkedIn-anchored matching is ~100% precise; name+org is ~20-25% and produces wrong-person matches. If you have a LinkedIn URL from Step 7, prefer it as the match key. Otherwise match name+org and treat the result as provisional.
- A person-match returns the current org inline; enrich the org separately only when you need firmographics.
- **Skip the email-search add-on** for academics: it returns ~0 emails and costs more. Take the work email Apollo already has, or fall back to the org domain.
- Bulk runs return large payloads. Save to a file and **delegate the match to a subagent** with the input list + output contract, so the payload stays out of the main context.
- Apollo catches "people moved" (a cited Oxford affiliation that's now Yale). Record both the cited affiliation and the current one; outreach goes to the current.

## Step 6 — Verify gate

Every **name+org** match (not LinkedIn-anchored) goes through a verify gate before it's allowed into outreach: does the matched person's industry/field fit the author? Flag mismatches red and exclude them. This is the rule that catches the wrong-person matches (a human-factors researcher matched to a medical-devices engineer; a researcher's name matched to a coffee roaster). LinkedIn-anchored matches pass automatically.

## Step 7 — LinkedIn resolution + Apify verification

- **Resolve** each person to a `/in/<slug>/` URL: web search (allowed_domains linkedin.com), the ORCID page's links, or the Apollo record.
- **Verify** the resolved URL is the right person via Apify `harvestapi/linkedin-profile-scraper` (bulk). Confirm the headline/affiliation matches the author. Mark each: `verified (Apify)` / `REVIEW (Apify)` / `WRONG (Apify) - namesake` / `unverified (private profile)`. Only `verified` (or hand-confirmed) URLs go into the send queue.
- Apify's free plan caps at 10 runs / 10 items; a real verification pass needs a paid plan.

## Step 8 — Draft + register

Draft the per-person email (see `outreach-channels.md` for structure) and the LinkedIn connect note (hook-free, <=300 chars). Write everything to the **citation registry xlsx** (`citation-registry-schema.md`) and append send-queue rows to the post tracker so the two centers share one queue view.

## What this center reuses from the engine

The config marker, the human-in-the-loop rule, the voice rules, the cadence ceiling, and "the registry/tracker is the source of truth." What's new: the harvest pipeline above, the email channel, and the richer registry schema.
