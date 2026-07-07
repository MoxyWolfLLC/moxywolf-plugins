# Jira Board Mapping & Digest Format Reference

How the Obsidian kanban maps onto the Jira board (project **MOXY**, https://moxywolf.atlassian.net), plus the slim #general digest template.

---

## Board Model

- **Obsidian `KANBAN_VIEW.md` is the source of truth.** Jira is the published, team-editable mirror.
- One board card ↔ one MOXY issue (type **Task**). The link is the `#jira/MOXY-NNN` tag on the Obsidian card.
- The board URL for humans: `https://moxywolf.atlassian.net/jira/software/projects/MOXY/boards/1` (verify in config note).
- Statuses are **discovered at sync time** (`getTransitionsForJiraIssue`), never assumed. Map to the nearest status by name; fall back to labels when a column has no matching status.

## Column → Status/Label Mapping

| Kanban column | Jira status (preferred) | Fallback if status absent | Labels |
|---|---|---|---|
| Backlog | To Do | — | `backlog` |
| P0 — Today | To Do | — | `p0` |
| P1 — This Week | To Do | — | `p1` |
| Blocked | Blocked | To Do + label `blocked` | `blocked` |
| In Progress | In Progress | — | — |
| In Review | In Review | In Progress + label `in-review` | `in-review` |
| Done | Done | — | — |

Additional label conventions:

- `#project/x` tags → label `project-x` (Jira labels can't contain `/`)
- `#cat/technical` etc. → label `cat-technical`
- Blocked context ("Waiting on X since DATE") goes in the issue description, not a label
- Reviewer for In Review items: `Review: <name>` line in the description + label `review-<shortname>`

## Assignees

`#assigned/<short-name>` maps to the Jira accountId stored in the config note (resolved once at setup via `lookupJiraAccountId` with each roster email). Contractors without Jira accounts stay unassigned; put their name in the issue description.

## Issue Authoring — Jira Best Practices

Every issue the sync creates is filled out as completely as the source data allows. A MOXY issue is the team's view of the work — sparse issues push people back to asking Dorian.

**Summary:** imperative, specific, ≤ ~10 words ("Render enrollment ledger on sequence page", not "ledger stuff"). No tags, no source metadata.

**Description — use these sections, in order, populating every one the sources can fill:**

1. **Context** — why this exists: the originating signal (meeting, email thread, Slack conversation, standup), quoted or summarized in 1–3 lines. Include who raised it and when.
2. **Acceptance** — what "done" observably looks like. If the source states it ("After enrolling, per-member status is visible in the CRM"), quote it. If not, derive a one-line acceptance test from the task; only omit when genuinely underivable.
3. **Notes** — blocked context ("Waiting on X since DATE"), reviewer ("Review: <name>"), deadlines, links to relevant docs/PRs.

**Sub-items become Subtasks, never description checklists.** If an Obsidian card has indented sub-checkboxes, or a task naturally decomposes into steps with independent completion ("Tasks: [ ] render ledger, [ ] render funnel"), create the parent Task plus one **Subtask** (issue type Subtask) per step, each with its own summary and assignee. Do NOT write `[ ]` checklists into the description — they aren't assignable, transitionable, or visible in rollups. Subtask completion syncs back to the card's sub-item under the dual-authority rule; the parent card only reaches Done when all its subtasks are Done.

**Dependencies become issue links, never prose.** "Depends on WS3" → link the issues with `getIssueLinkTypes` → `createIssueLink` (type "Blocks": WS3 blocks this issue). Keep a one-line mention in Context for human readers, but the link is the machine-readable truth. Cards in the Blocked column always get a link to the blocking issue when the blocker is itself tracked in MOXY; when the blocker is external (a person, a vendor), it stays in Notes.

**Assignee, labels, status:** always set on creation — never create a bare issue and fix it later. Priority semantics ride on the `p0`/`p1` labels per the mapping above.

## Sync Rules

- Card without `#jira/` tag → `createJiraIssue` (project MOXY, type Task) authored per the best-practices section above (full description, subtasks for sub-items, issue links for dependencies), then write `#jira/MOXY-NNN` back onto the card (automatic metadata write-back). Sub-item ↔ subtask links are positional under the parent card — the parent's `#jira/` tag covers the family.
- Card changed (title, column, assignee, labels, blocked context) → `editJiraIssue` + `transitionJiraIssue` as needed. Only touch issues whose card actually changed.
- Issue moved to Done or In Review in Jira → dual-authority: completion wins; sync back to Obsidian (Step 10a).
- Issue in MOXY with no matching card and not from team-input handling → surface in Dorian's triage. Never delete Jira issues autonomously.

---

## Daily Digest Message Template (Slack mrkdwn — slim)

The digest is a pointer, not the board. Keep it under 150 words: stats, P0s, blocked escalations, board link.

```
:clipboard: *Team Kanban — [Day], [Month] [Date]*

*Quick Stats:* [total] tasks | [P0 count] :fire: P0 | [P1 count] :star: P1 | [blocked count] :no_entry: Blocked | [done count] :white_check_mark: Done this week

:fire: *P0 — Today*
• *[Task title]* — <@USLACKID> — [context/deadline]
[Or: "_No P0 items. Clear runway._"]

:no_entry: *Blocked escalations*
• *[Task title]* — waiting on *[Person]* ([N] days) [escalation emoji if > 7 days]
[Only items > 7 days. Or omit the section if none.]

:link: <https://moxywolf.atlassian.net/jira/software/projects/MOXY/boards/1|View the full board in Jira>

_Add tasks in Jira directly, or reply in this thread:_ `P1 Task description #project`
```

### Slack mrkdwn Rules (Messages Only)

- Bold: `*text*` (single asterisks, NOT double)
- Italic: `_text_` (underscores)
- Links: `<url|display text>` (pipe in angle brackets)
- User mention: `<@USLACKID>`
- No `## headers` — use `*bold text*` on its own line
- Emoji: `:emoji_name:` works in messages

---

## Configuration File Template

Store at `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md`:

```yaml
---
title: Team Kanban Configuration
date: [setup date]
type: reference
tags: [team-kanban, jira, automation]
status: active
---

# Team Kanban Configuration

## Jira
- **Site:** https://moxywolf.atlassian.net
- **Cloud ID:** [uuid from getAccessibleAtlassianResources]
- **Project key:** MOXY
- **Board URL:** [board URL]
- **Statuses discovered:** [list, with date discovered]

## Team Roster — Jira accountIds
| Short name | Email | Jira accountId |
|---|---|---|
| dorian | dorianc@moxywolf.com | [accountId] |
| phil | philm@moxywolf.com | [accountId] |
| steven | stevenp@moxywolf.com | [accountId] |
| michael | michaelf@moxywolf.com | [accountId] |

## Slack (digest only)
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

## Standup
- **last_standup_read:** [YYYY-MM-DD HH:MM TZ — updated by personal-os after each standup]

## Schedule
- Daily at [configured time] PT (weekdays)
- On-demand via `/team-kanban`

## History
- Setup date: [date]
- Last sync: [auto-updated]
```
