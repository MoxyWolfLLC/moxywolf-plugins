---
description: Build or refresh the topic fingerprint from your configured content sources — themes, signature phrases, and search seeds.
argument-hint: ""
allowed-tools: [Read, Write, Bash, Grep, Glob]
---

# /synergy-engine:synergy-fingerprint — build the matching key

Distill your published content into a **topic fingerprint**: the themes you actually have something to say about, with the signature phrases that are uniquely yours. This is what discovery scores against. See `references/topic-synergy-methodology.md` Part 1.

## STEP 1 — Load config

Read `synergy-engine-config.md` (from `/synergy-init`). If absent, route to `/synergy-init`.

## STEP 2 — Read every configured source

- **Supabase `/answers`** — `execute_sql`: `select category, count(*), string_agg(question, ' | ') from <table> where active group by category;` to get the live answer topics per category.
- **Anchor paper / POV** — read the paper (or its markdown/model file) for its thesis, the named claims, and the formal sources it already cites.
- **Repo content** — read blog/news markdown for published angles.
- **Keyword/audience study** — read for the audience's own search language.

## STEP 3 — Distill the fingerprint

Write `topic-fingerprint.md` next to the tracker. For each theme: a one-line canonical claim, **signature phrases** (uniquely yours — the gold for search seeds), broad search seeds (the audience's words), and the persona it serves. Add a connective "bridge" note: how your themes map onto the broader discourse the targets post in. List the anchor paper's formal sources too (for the bibliography lever).

## STEP 4 — Report

Show the theme table. Note that the fingerprint auto-refreshes — re-running this command after you publish new content keeps the matching surface current. Suggest `/synergy-discover`.
