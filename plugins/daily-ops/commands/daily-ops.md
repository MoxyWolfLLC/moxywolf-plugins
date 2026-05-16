---
description: "Run Daily Ops: morning standup, backlog triage, weekly review, or fitness coach. Usage: /daily-ops [standup|triage|review|fitness]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite", "AskUserQuestion", "mcp__cowork__request_cowork_directory"]
---

Read the skill at ${CLAUDE_PLUGIN_ROOT}/skills/daily-ops/SKILL.md and follow its instructions.

Determine the mode from the argument provided:
- No argument or "standup" → Mode 1: Morning Standup
- "triage" → Mode 2: Backlog Triage
- "review" → Mode 3: Weekly Review
- "fitness" or "workout" → Mode 4: Fitness Coach (reads Apple Health, prescribes today's workout, adds it to Google Calendar, iMessages a short summary)

If the argument is ambiguous or missing, default to Morning Standup and offer to switch modes at the end.

For Mode 4, before doing anything else:
1. Read the Fitness Coach profile at `<MoxyWolf Vault>/_Shared Knowledge/Fitness Coach/profile.md`.
2. If the profile is empty or marked `setup_complete: false`, run Step 1: Learn the User from the skill — ask the 10 intake questions and write the answers back to `profile.md`.
3. Otherwise proceed to Step 2: Read Today's Health Data.

Use TodoWrite to track progress through each step.
