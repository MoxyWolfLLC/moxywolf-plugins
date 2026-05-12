# Daily Ops Plugin

Energy-aware personal operations system that combines health data, calendar, Gmail inbox intelligence, Google Drive task persistence, and a data-driven fitness coach into structured daily workflows.

## What It Does

Four operating modes:
- **Morning Standup** — Health assessment, calendar scan, full inbox intelligence (5-query email scan), Google Drive task state, energy-adjusted briefing
- **Backlog Triage** — Process and prioritize backlog with pillar alignment and energy cost
- **Weekly Review** — Retrospective with health trends, pillar attention analysis, goal progress
- **Fitness Coach** *(new in 1.3.0)* — Reads Apple Health (sleep, HRV, RHR, workouts), runs a daily decision engine, prescribes today's workout, drops it on Google Calendar at the configured time, and sends an iMessage summary

## Commands

- `/daily-ops` or `/daily-ops standup` — Morning Standup (default)
- `/daily-ops triage` — Backlog Triage
- `/daily-ops review` — Weekly Review
- `/daily-ops fitness` — Fitness Coach (today's workout)

## What's New in v1.3.0

**Fitness Coach Mode** — A complete personal-trainer subsystem built on the Claude Fitness Coach Setup Guide (mavgpt.ai, 2026 ed.):

- **First-run intake:** 10 questions on goals, equipment, schedule, limitations — stored in `_Shared Knowledge/Fitness Coach/profile.md` in the MoxyWolf Vault.
- **Daily decision engine:** Sleep, HRV, resting HR, soreness, momentum, and (optional) menstrual phase drive intensity. Bad sleep auto-swaps heavy lifts for active recovery.
- **Progressive overload:** Tracks weights per lift; auto-bumps on 2-session clears; mandatory 4th-week deload.
- **Smart calendar integration:** Each workout becomes a Google Calendar event at the user's preferred time with full workout details in the description (warm-up, main sets, finisher, cool-down, modifications, form cues).
- **iMessage notifications:** Short daily nudge with the "based on" rationale and the calendar pointer — no full workout in the SMS.
- **Apple Health setup reminder:** If HealthKit access fails, sends a one-time iMessage walking the user through enabling permissions in the Claude iOS app.
- **Weekly planning** (every Sunday) and **monthly progress reports** (every 4 weeks) baked in.

## What's New in v1.2.0

**Full Inbox Intelligence** — Step 5 now runs 5 targeted Gmail sub-queries instead of a simple inbox flag:
- **5a:** Unanswered emails needing reply (sent by others, no reply from you)
- **5b:** Meeting-related emails cross-referenced with today's calendar
- **5c:** VIP/key contact messages
- **5d:** Urgent or time-sensitive threads
- **5e:** Optional-reply items (newsletters, FYIs, low-priority)

Results are deduplicated by thread ID and sorted by priority. The Step 8 briefing now includes a **"Your Inbox Says"** section with categorized email summaries: Needs Reply, Meeting Prep, VIP/Key Contacts, Urgent/Time-Sensitive, and Could Reply.

## What's New in v1.1.0

**Direct Google Drive Writes** — Uses `proxy_execute` with `supportsAllDrives=true` for Team Drive operations instead of standard Composio tools (which return 404).

## Requirements

- Google Drive (Team Drive with operations folder)
- Google Calendar
- Gmail
- Rube/Composio connection (for HealthKit and Drive writes)
- Apple HealthKit or Oura (for sleep/health data)
- iMessage MCP / Messages app (for fitness coach notifications — Mac required)

## Trigger Phrases

"morning standup", "daily ops", "what should I focus on", "brain dump", "triage my tasks", "process my backlog", "weekly review", "how did my week go", "what's my day look like", "fitness", "workout", "what should I do today" (gym context), "build my week" (workout context), "I'm sore", "I only slept X hours"
