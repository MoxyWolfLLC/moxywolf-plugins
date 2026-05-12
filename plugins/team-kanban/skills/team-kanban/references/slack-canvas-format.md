# Slack Canvas & Digest Format Reference

Templates for the Team Kanban Canvas and the daily #general digest message.

---

## Canvas Template (Canvas-flavored Markdown)

Use this exact structure when creating or updating the Team Kanban Canvas via `slack_create_canvas` or `slack_update_canvas`.

Canvas-flavored Markdown uses standard Markdown, NOT Slack mrkdwn. Headers, links, and checklists all work normally.

```markdown
# Team Kanban — MoxyWolf

*Last updated: [Day], [Month] [Date], [Year] at [Time] PT*
*Last standup read: [YYYY-MM-DD] at [Time] PT*

---

## :inbox_tray: Backlog

- [ ] [Task description in plain language] — ![](@USLACKID)
- [ ] [Task description in plain language] — ![](@USLACKID)

*[N] items*

---

## :fire: P0 — Today (Max 3)

- [ ] [Task description] — ![](@USLACKID) — [why today / deadline context]
- [ ] [Task description] — ![](@USLACKID) — [context]

*[N]/3 slots used*

---

## :star: P1 — This Week

**![](@USLACKID) [Person Name]**
- [ ] [Task description in plain language]
- [ ] [Task description] :warning: CRITICAL
- [ ] [Task description] (blocked on [what/who])

*(Group P1 items by assignee with bold name headers. The person's name IS the assignment — no need for project labels, source tags, or other metadata on each line. Write task descriptions naturally, like you'd say them out loud.)*

---

## :no_entry: Blocked

- [ ] [Task description] — Waiting on [Person Name] since [Date] ([N] days) — ![](@USLACKID)
  - :red_circle: ESCALATION OVERDUE (if > 14 days)
  - :large_yellow_circle: Approaching escalation (if > 7 days)

*[N] items blocked*

---

## :hammer_and_wrench: In Progress

- [ ] [Task description] — ![](@USLACKID)

*[N] items in flight*

---

## :mag: In Review

- [ ] [Task description] — Completed by ![](@ASSIGNEE_ID) since [YYYY-MM-DD] — Review: ![](@REVIEWER_ID)

*(Tasks here were marked done by the assignee and need confirmation from a different team member before moving to Done. The reviewer should NOT be the same person who completed the task. The "since" date is when the item entered In Review — used by the morning standup to calculate review wait time.)*

*[N] items awaiting review*

---

## :white_check_mark: Done (This Week)

- [x] [Task description] — ![](@USLACKID) — Reviewed by ![](@REVIEWER_ID)

*[N] items completed*

---

### How to Add Tasks

Reply in the #general digest thread with a task and it will be picked up on the next sync.

Format: `[P0/P1/Backlog] Task description #project-name`

Example: `P1 Review RegGenome press release draft #reggenome`
```

### Team Roster (Slack IDs for Canvas mentions)

| Name | Short Name | Canvas Mention | Slack ID |
|------|-----------|----------------|----------|
| Dorian Cougias | dorian | `![](@U08PV3UHTEX)` | U08PV3UHTEX |
| Philip Mudhir | phil | `![](@U096C551HBR)` | U096C551HBR |
| Steven P | steven | `![](@U098H0X9CQ4)` | U098H0X9CQ4 |
| Michael Flanagan | michael | `![](@U09EB7N7B98)` | U09EB7N7B98 |

For contractors without Slack accounts, use their name as plain text instead of a mention.

### Canvas Formatting Rules

- Use `- [ ]` for incomplete tasks (renders as interactive checklists in Slack Canvas)
- Use `- [x]` for completed tasks
- Write task descriptions in plain language — like you'd say them in a standup
- The assignee IS the person under the bold header (P1) or the `![](@USLACKID)` inline mention (P0, Backlog, etc.)
- Do NOT include metadata labels on task lines: no source tags (`obsidian`, `slack`, `gmail`), no project labels in italics (`*SAMS*`, `*STIGViewer*`), no category tags. If the project context matters, weave it naturally into the task description (e.g., "Export STIG vendor spreadsheet from admin panel" not "Export spreadsheet — *STIGViewer*")
- Use `:emoji_name:` for emoji — Canvas renders these
- Horizontal rules (`---`) separate columns visually
- User references in Canvas use `![](@USLACKID)` format, NOT `<@USLACKID>`
- Channel references use `![](#CCHANNELID)` format, NOT `<#CCHANNELID>`

---

## Daily Digest Message Template (Slack mrkdwn)

Use this template for the daily `slack_send_message` to #general. This uses Slack mrkdwn, NOT standard Markdown.

```
:clipboard: *Team Kanban — [Day], [Month] [Date]*

*Quick Stats:* [total] tasks | [P0 count] :fire: P0 | [P1 count] :star: P1 | [blocked count] :no_entry: Blocked | [done count] :white_check_mark: Done
[If new items since last sync: "+[N] new items from [sources]"]

:fire: *P0 — Today*
[For each P0 item:]
• *[Task title]* — _[project]_ — <@USLACKID> — [context/deadline]
[Or if empty: "_No P0 items. Clear runway._"]

:no_entry: *Blocked*
[For each blocked item:]
• *[Task title]* — waiting on *[Person]* ([N] days) [escalation emoji if applicable]
[Or if empty: "_Nothing blocked._"]

:star: *P1 Highlights* (full list on Canvas)
[Show top 3-4 P1 items. If more exist, note "and [N] more on the board"]

:link: <[Canvas URL]|View Full Board>

_Reply in this thread to add tasks. Format:_ `P1 Task description #project`
```

### Slack mrkdwn Rules (Messages Only)

- Bold: `*text*` (single asterisks, NOT double)
- Italic: `_text_` (underscores)
- Links: `<url|display text>` (pipe in angle brackets)
- User mention: `<@USLACKID>`
- Channel mention: `<#CCHANNELID>`
- No `## headers` — Slack messages don't support Markdown headers. Use `*bold text*` on its own line
- No `[text](url)` links — use `<url|text>` format
- Emoji: `:emoji_name:` works in messages

---

## Configuration File Template

Store at `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md`:

```yaml
---
title: Team Kanban Configuration
date: [setup date]
type: reference
tags: [team-kanban, slack, automation]
status: active
---

# Team Kanban Configuration

## Slack
- **Canvas ID:** [F-prefixed Canvas ID]
- **Canvas Title:** Team Kanban — MoxyWolf
- **Channel:** #general
- **Channel ID:** [C-prefixed channel ID]

## Columns
- Backlog (no limit)
- P0 — Today (max 3)
- P1 — This Week (max 7)
- Blocked (no limit)
- In Progress (no limit)
- In Review — completed by assignee, awaiting confirmation from a different team member (no limit)
- Done — This Week (confirmed complete, cleared Mondays)

## Sources
- Obsidian KANBAN_VIEW.md (primary)
- Google Drive Active Tasks (secondary)
- Google Calendar (today's commitments)
- Gmail (action items, VIP contacts)
- Slack DMs, Group DMs, and threads (team commitments and assignments)
- Slack project channels: #sams, #stig-viewer, #assured-book, #jtbd_analyzer, #team-edify, #cms-migration
- Slack thread replies to #general digest (manual team input)

## Schedule
- Daily at [configured time] PT (weekdays)
- On-demand via `/team-kanban`

## History
- Setup date: [date]
- Last sync: [auto-updated]
```
