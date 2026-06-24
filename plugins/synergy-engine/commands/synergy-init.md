---
description: One-time setup for the synergy engine — declare the tracker location, fingerprint sources, anchor paper, and LinkedIn channel(s). Creates the xlsx tracker.
argument-hint: ""
allowed-tools: [Read, Write, Bash, AskUserQuestion]
---

# /synergy-engine:synergy-init — configure the engine

Set up the topic-synergy outreach engine for a project. Run once per project; re-run to reconfigure.

## STEP 1 — Gather config (AskUserQuestion / elicitation)

Collect:

- **Tracker location** — the folder for `<name>-linkedin-outreach-tracker.xlsx` (default: the project's MARCOM/Audience folder).
- **Fingerprint sources** — any of: a Supabase project + `/answers` table, an anchor paper (whitepaper / DOI / URL), repo content paths, a keyword/audience study. Record how to read each (e.g. the Supabase `project_id` + table name).
- **Anchor paper / POV** — the content-center anchor (title + URL + DOI) the cite-then-tell lever points at.
- **LinkedIn channel(s)** — the personal profile and any Company/Showcase Pages the user can post as (used by `/synergy-run`).
- **Voice profile path** — optional; the writer's voice file for outreach copy.

## STEP 2 — Create the tracker

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tracker_init.py --out "<tracker-path>"
```

This writes the `Outreach Tracker` sheet (schema in `references/tracker-schema.md`) plus a `How this works` legend sheet. If the file already exists, do NOT overwrite — report its path and row count instead.

## STEP 3 — Write the config marker

Write `synergy-engine-config.md` next to the tracker, recording the choices from STEP 1 (tracker path, fingerprint sources, anchor paper, channels, voice path). `/synergy-fingerprint`, `/synergy-discover`, `/synergy-run`, and `/synergy-schedule` read this marker to locate everything. If no marker is found later, those commands route back here.

## STEP 4 — Report

Confirm the tracker path, the configured sources, the anchor paper, and the channels. Suggest `/synergy-fingerprint` as the next step.
