---
name: discourse-sweep
description: |
  This skill should be used when running the 30-day discourse sweep step of the 4D Blog Engine — Phase 3 (Discernment). It fires platform-targeted queries across reddit, X, Hacker News, Substack, dev.to, github, linkedin.com/pulse, Facebook, Quora, podcasts (Apify), and academic sources (research-pipeline/literature-discovery), then ranks the findings via combined_score = relevance×0.6 + recency×0.4, dedupes by 70% title-overlap, applies cross-source clustering, and writes a discourse.md to the piece's 03-discernment/ folder. Triggers: "/4d-blog-engine:discern", "run the 30-day sweep", "sweep the discourse on", "what's the world saying about <topic>", "research the last 30 days for <topic>". This is a specialist skill — invoked by the 4d-blog-engine orchestrator, not directly by the user in normal usage.
allowed-tools: [Read, Write, Bash, WebSearch, Glob]
user-invocable: false
---

# Discourse Sweep — the 30-day platform-targeted research engine

> **Read this when:** Phase 3 (Discernment) has just started. The orchestrator skill has confirmed Phase 2's outline is approved and the piece directory exists. Your job is to populate `<piece>/03-discernment/discourse.md` with a ranked, themed brief of the last 30 days of conversation on this topic.

## Why this is a specialist skill

The 30-day sweep is mechanically distinct from the rest of Phase 3 (drafting, slop pass). It's a research operation with a strict separation: **the orchestrator dispatches queries; `scripts/discourse_sweep.py` does the math.** Per agricidaniel/claude-blog's discipline: the LLM agent never does deterministic ranking/dedup; the script never makes network calls.

## Inputs

The orchestrator gives you:

- `<piece>/02-description.md` — the outline, with section-by-section evidence needs
- `<piece>/01-delegation.md` — the angle and the earned secret
- `<piece>/state.md` — the piece slug and the active project

## Workflow

### Step 1 — Generate the sweep plan

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/discourse_sweep.py plan \
  --topic "<angle from 01-delegation.md>" \
  --outline "<piece>/02-description.md" \
  --days 30 \
  --out "<piece>/03-discernment/sweep-plan.json"
```

The plan file lists ~9 web-platform queries for the primary topic + ~9 queries per outline section. Each query has the form `<terms> site:<platform> after:<YYYY-MM-DD>` and an `executor` field naming the tool to use.

### Step 2 — Execute the queries

For each query in `sweep-plan.json["queries"]`:

- **`executor: WebSearch`** (the default for all web platforms): call `WebSearch` with the query string. Capture the top 5-10 results.
- **`executor: Apify`** (for podcasts): call `mcp__Apify__call-actor` with an Apple Podcasts search actor and the topic terms. If Apify isn't connected, fall back to `WebSearch` with `site:apple.co/podcasts` and `site:open.spotify.com/episode` queries, and log the degradation.
- **`executor: research-pipeline`** (for academic): invoke the `research-pipeline/literature-discovery` skill with the topic. It returns OpenAlex + Semantic Scholar + arXiv hits.

For each result, capture into a findings array:

```json
{
  "title": "<page title>",
  "url": "<absolute URL>",
  "platform": "<reddit|x|hn|substack|devto|github|linkedin|facebook|quora|podcasts|academic>",
  "summary": "<2-4 sentence summary in your own words>",
  "published_at": "<ISO date if extractable, else null>",
  "source_type": "<discussion|blog|primary|whitepaper|podcast|paper|other>",
  "relevance": <optional 0-1 if you can judge precisely; otherwise omit>
}
```

Write the collected findings array to `<piece>/03-discernment/sweep-findings.json` as JSON (a single top-level array, or `{"findings": [...]}` — the ranker accepts both).

**Anti-fabrication rule** (load-bearing): **only include findings you actually retrieved.** If WebSearch returned nothing for a query, log the empty result in `sweep-findings.json` as a comment block but never invent a URL or a summary. Findings whose summary you cannot derive from real retrieved content do not exist.

### Step 3 — Rank, dedupe, cluster

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/discourse_sweep.py rank \
  --findings "<piece>/03-discernment/sweep-findings.json" \
  --topic "<angle from 01-delegation.md>" \
  --out "<piece>/03-discernment/discourse.md"
```

The ranker:

- Scores each finding `combined_score = relevance×0.6 + recency×0.4` (recency banded).
- Dedupes via 70% title-token overlap, keeps the highest-scoring as the primary of each cluster.
- Adds a +0.1 source-diversity bonus to clusters surfacing from ≥2 platforms.
- Writes `discourse.md` (human-readable) and `discourse.json` (sidecar for downstream steps).

### Step 4 — Council synthesis pass (optional but recommended)

The 30-day sweep is **recall-heavy**. The Council deliberation pass is the de-noiser. Invoke:

```
/council:deliberate --prompt "Given these findings, the angle, and the outline,
which findings move the post from generic to specific? Which contradict each
other? Which represent consensus vs minority view across platforms? Return a
ranked, themed brief with 3-5 themes." --input "<piece>/03-discernment/discourse.md"
```

Capture Council's output to `<piece>/03-discernment/discourse-themed.md`. This becomes the file the writer (research-pipeline/content-writer) reads when drafting.

If Council is unavailable (no OpenRouter key, etc.), log the degradation in `sources-verification.md` and use the unfiltered `discourse.md` directly. State this clearly.

### Step 5 — Apply source-quality tiers

Read `references/source-quality-tiers.md` if not already loaded. For each primary finding in `discourse.md`, assign a tier (1-5) based on the platform and the source character. Write a `<piece>/03-discernment/sources-verification.md` that lists each citable source with its tier, its FLOW-evidence-triple checklist (year anchor + inline citation form + retrieval date), and a verification state (`[V]/[S]/[F]`) that downstream citation verification will fill in.

**Tier 4-5 sources do not advance to the writer.** Drop them with a one-line "rejected (tier 4-5)" note.

### Step 6 — Hand off to the writer

Once `discourse-themed.md` and `sources-verification.md` exist, return control to the orchestrator with a status report:

```
Discourse Sweep complete.
- Findings retrieved: <N>
- Clusters after dedupe: <M>
- Tier 1-3 citable: <K>
- Tier 4-5 rejected: <L>
- Council synthesis: <ran|degraded>
- Output: <piece>/03-discernment/discourse-themed.md
```

The orchestrator then invokes `research-pipeline/content-writer` to do the actual draft, then `bibtex-builder/bibtex-from-urls` to generate `bibliography.bib` from the Tier 1-3 sources.

## What this skill does NOT do

- It does not draft the post — that's `research-pipeline/content-writer`.
- It does not verify citations — that's `research-pipeline/citation-verifier`.
- It does not build the bibliography — that's `bibtex-builder`.
- It does not run the slop pass — that's `scripts/prose_lint.py` + the Tier-2 LLM sub-agent (invoked from the discern command).

It does one thing: turn the outline + angle into a ranked, themed brief of the last 30 days.

## Degradation behaviors

- **Apify not connected:** fall back to WebSearch with `site:apple.co/podcasts` queries. Log it.
- **research-pipeline/literature-discovery not installed:** skip academic; emit a warning in `sources-verification.md`.
- **Council not configured:** skip Step 4; use unfiltered `discourse.md`. Log it.
- **WebSearch rate-limited or empty result for a query:** log the empty result; do not invent findings.

In all degradation cases, the sweep continues with what it can retrieve. Half a sweep is better than a fabricated full sweep.
