---
description: Stand up an every-other-day prep task that stages N due targets as review-ready drafts and books a calendar block. Never posts.
argument-hint: "[N per run, default 5] [window, e.g. 1-3pm PT]"
allowed-tools: [Read, Bash, AskUserQuestion, mcp__scheduled-tasks__create_scheduled_task, mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__create_event]
---

# /synergy-engine:synergy-schedule — automate the prep, not the posting

Create a scheduled task that does the **unattended** half of the cycle: pick due targets from the tracker, sweep their freshest on-theme post, draft the like/comment (+ connect + citation), log them as `Ready for review`, and book a calendar block. **It never posts** — comments and connects go out under the user's name through their browser, so a human approves and posts at the calendar block.

## STEP 1 — Parameters

From the argument or AskUserQuestion: N per run (default 5), the calendar window (default 1-3pm PT), cadence (default every other day). Confirm the tracker path from `synergy-engine-config.md`.

## STEP 2 — Create the task

`mcp__scheduled-tasks__create_scheduled_task` with a cron in the user's local time (e.g. `0 13 */2 * *` = 1pm every other day). The prompt must be fully self-contained (fresh session, no memory): include the tracker path discovery, the due-target rule, the Apify actor for the freshest post, the fingerprint scoring, the drafting rules (Path A/B + cite-then-tell, verified citations, voice), the instruction to write drafts into the tracker as `Ready for review` (NOT to flip Liked/Commented), and to book a Google Calendar event in the window titled "Review <project> outreach batch (N drafts)" with the drafts in the description and a line like "Open Cowork and say 'run the synergy batch' to approve and post." End with: never post/like/comment/connect autonomously; citations verified; tracker is dedupe + source of truth.

## STEP 3 — Report + pre-approve

Confirm the schedule and next run. Recommend the user click "Run now" once to pre-approve the tools the task uses (Apify, Calendar, file writes) so future unattended runs don't pause on permission prompts. Note: the first run may stage a batch the same day — that's drafts only, safe to ignore.
