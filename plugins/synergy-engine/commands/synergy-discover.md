---
description: Discover on-theme posts (author and/or content center) via Apify, score against the fingerprint, dedupe against the tracker, and write a synergy scan + queue.
argument-hint: "[author|content|both] [topic or query terms]"
allowed-tools: [Read, Write, Bash, AskUserQuestion, WebSearch]
---

# /synergy-engine:synergy-discover — find and rank on-theme posts

Pull recent posts from targets, score them against the fingerprint, and queue the good ones. See `references/topic-synergy-methodology.md` (Parts 2-3) and `references/apify-actors.md`.

## STEP 1 — Load config + fingerprint

Read `synergy-engine-config.md` and `topic-fingerprint.md`. If the fingerprint is missing, route to `/synergy-fingerprint`.

## STEP 2 — Pick the center(s)

From the argument or AskUserQuestion:

- **Author center** — a curated profile list (from the tracker, the config, or supplied names). Resolve any names to `/in/<slug>/` URLs (web search, allowed_domains `linkedin.com`). Pull via `harvestapi/linkedin-profile-posts`.
- **Content center** — keyword/hashtag queries built from the fingerprint's signature phrases (not generic terms). Pull via `harvestapi/linkedin-post-search`, `sortBy: relevance`, `postedLimit: month`.

Both actors, inputs, and dataset-reading guidance are in `references/apify-actors.md`. Keep `maxPosts` and query count modest (cost is per-result).

## STEP 3 — Score against the fingerprint

Read the dataset (projected fields). If too large for context, save and delegate to a subagent with: the file path, the fingerprint themes, the **exclude-list** (every `publicIdentifier` already in the tracker), and the output contract. Score each post on theme-hit (signature match = double), stance (extends / contradicts / adjacent), recency + heat, persona fit. Classify each author advisor / competitor-vendor / other.

## STEP 4 — Write the synergy scan + queue

Write `synergy-scan-<date>.md`: ranked synergy cards (best on-theme post + URL + engagement, themes hit, stance, type, the angle for our comment), and for the top accounts the two-touch (or three-lever) sequence with drafted comments and DM/connect notes. Append the fitting targets to the tracker as `Queued` rows, with the post URL in Next Action (schema in `references/tracker-schema.md`). Mark competitor-founders as the peer tier (`Content/peer`).

## STEP 5 — Report

Show the ranked candidates, flag the hot ones, and recommend a scope for `/synergy-run` (default <= 5, per the cadence rules).
