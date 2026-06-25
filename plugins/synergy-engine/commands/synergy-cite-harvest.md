---
description: Citation center — harvest the cited authors from a paper's bibliography, enrich + verify them, draft the outreach, and write the citation registry. The "we cited you" pipeline.
argument-hint: "[path to the source paper / bibliography]"
allowed-tools: [Read, Write, Bash, AskUserQuestion, WebSearch, Task, mcp__Apify__call-actor, mcp__Apify__get-dataset-items]
---

# /synergy-engine:synergy-cite-harvest — start from who you cited

Turn a paper's bibliography into a drafted, enriched citation registry of reachable authors to thank. Read `references/citation-center.md` (the full pipeline) and `references/outreach-channels.md` (the draft structure) first. Sending is a separate, human-gated step (`/synergy-cite-run`) — this command never sends.

## STEP 1 — Load config + the source paper

Read `synergy-engine-config.md` for the anchor paper, the Apollo / Clarify / Mailtrap availability, and the tracker path. Take the source paper from the argument (a markdown/PDF/bibliography path); if absent, ask. The source is usually the anchor paper itself.

## STEP 2 — Triage by reachability

Parse the bibliography. Bucket each reference: `individual` (a named human — the only bucket that proceeds), `organization`, `legal case`, `statute`, `classic-unreachable`. Write the non-people to the registry's Non-targets sheet so they're never re-processed. For each individual work, carry: title, year, DOI, the section(s) of our paper that cite it, and a one-line "how we used it."

## STEP 3 — Resolve people (OpenAlex + ORCID)

For each individual work with a DOI, resolve authors via `https://api.openalex.org/works/doi:<DOI>` (use the sandbox curl/python; web-fetch returns empty on the JSON API). Pull name, ORCID, last-known institution, corresponding-author flag. No-DOI works resolve by title search. **Dedupe to one record per person** (ORCID first, name fallback), unioning their cited works + sections, and tag a priority (load-bearing / primary author / co-author).

## STEP 4 — Clarify dedup (before spending Apollo credits)

For each person/org, check Clarify (CRM) for an existing enriched record. Reuse it if present; only the misses go to Apollo. (memory: feedback_clarify_dedup_before_apollo)

## STEP 5 — Apollo enrich + verify gate

Enrich person + org via Apollo, **matching by LinkedIn URL first** (~100% vs ~25% on name+org). Skip the email-search add-on (useless for academics). Bulk runs return large payloads — **save to a file and delegate the match to a subagent** (Task tool) with the input list + output contract, keeping the payload out of context. Record current org (catches "moved") alongside the cited affiliation. Then run the **verify gate**: every name+org match must pass an industry/field-fit check before outreach; flag mismatches `FALSE POSITIVE - exclude`. LinkedIn-anchored matches pass automatically.

## STEP 6 — LinkedIn resolve + Apify verify

Resolve each person to `/in/<slug>/` (web search allowed_domains linkedin.com, the ORCID page, or the Apollo record). **Verify** via Apify `harvestapi/linkedin-profile-scraper` (bulk) that the profile's headline/affiliation matches the author. Mark each `verified (Apify)` / `REVIEW (Apify)` / `WRONG (Apify) - namesake` / `unverified (private profile)`. Only `verified` (or hand-confirmed) URLs become send-eligible.

## STEP 7 — Draft the outreach

Per ready person, draft both channels (structure in `references/outreach-channels.md`):

- **Email** — their bibliographic reference first, then how we used it, then our paper once. No pitch.
- **Connect note** — hook-free, <=300 chars, acknowledges the citation. If the person was emailed, the note may open "just emailed you...".

Voice: no em-dashes, contractions, typographer's quotes. Read the configured voice profile first.

## STEP 8 — Write the registry + queue

Build the citation registry xlsx:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/citation_registry.py --from-json <authors.json> --out "<registry-path>" [--nontargets-json <nt.json>] [--force]
```

Schema in `references/citation-registry-schema.md`. Then append a light queue row per send-ready person to the post tracker (`Persona = Citation`, `Path = cited`, `Cited URL` = the anchor paper) so `/synergy-status` shows all centers in one view.

## STEP 9 — Report

Show the funnel (references -> individual works -> distinct authors -> enriched -> LinkedIn-verified -> send-ready), the verify-gate exclusions, anyone `Held` (e.g. extrapolated email), and recommend a first `/synergy-cite-run` batch sized to the daily ceiling.
