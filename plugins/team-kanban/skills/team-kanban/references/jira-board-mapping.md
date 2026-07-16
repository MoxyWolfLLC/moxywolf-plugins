# Jira Board Reference

How tasks map onto the single canonical board — Jira project **MOXY** (https://moxywolf.atlassian.net). There is no vault kanban and no Slack digest; this reference is the issue-authoring and status-mapping standard for the board.

---

## Board Model

- **Jira (project MOXY) is the single source of truth.** There is no Obsidian card and no sync-back.
- Each task is one MOXY issue (type **Task**); sub-items are real **Subtasks** under it.
- The board URL for humans: `https://moxywolf.atlassian.net/jira/software/projects/MOXY/boards/1` (verify in config note).
- New issues default to **Backlog** — not auto-added to an active sprint.
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

- Project → label `project-<slug>` (Jira labels can't contain `/`, so a `project/sams` scope becomes `project-sams`)
- Category → label `cat-<name>` (e.g. `cat-technical`)
- Blocked context ("Waiting on X since DATE") goes in the issue description, not a label
- Reviewer for In Review items: `Review: <name>` line in the description + label `review-<shortname>`

## Assignees

`#assigned/<short-name>` maps to the Jira accountId stored in the config note (resolved once at setup via `lookupJiraAccountId` with each roster email). Contractors without Jira accounts stay unassigned; put their name in the issue description.

## Issue Authoring — Jira Best Practices

Every issue the sync creates is filled out as completely as the source data allows. A MOXY issue is the team's view of the work — sparse issues push people back to asking Dorian.

**Summary:** imperative, specific, ≤ ~10 words ("Render enrollment ledger on sequence page", not "ledger stuff"). No tags, no source metadata.

**Description — use these sections, in order, populating every one the sources can fill:**

1. **Context** — why this exists: the originating signal (meeting, email thread, standup, Drive task), quoted or summarized in 1–3 lines. Include who raised it and when.
2. **Acceptance** — what "done" observably looks like. If the source states it ("After enrolling, per-member status is visible in the CRM"), quote it. If not, derive a one-line acceptance test from the task; only omit when genuinely underivable.
3. **Notes** — blocked context ("Waiting on X since DATE"), reviewer ("Review: <name>"), deadlines, links to relevant docs/PRs.

**Sub-items become Subtasks, never description checklists.** If a task naturally decomposes into steps with independent completion ("Tasks: [ ] render ledger, [ ] render funnel"), create the parent Task plus one **Subtask** (issue type Subtask) per step, each with its own summary and assignee. Do NOT write `[ ]` checklists into the description — they aren't assignable, transitionable, or visible in rollups. The parent Task only reaches Done when all its Subtasks are Done.

**Dependencies become issue links, never prose.** "Depends on WS3" → link the issues with `getIssueLinkTypes` → `createIssueLink` (type "Blocks": WS3 blocks this issue). Keep a one-line mention in Context for human readers, but the link is the machine-readable truth. Cards in the Blocked column always get a link to the blocking issue when the blocker is itself tracked in MOXY; when the blocker is external (a person, a vendor), it stays in Notes.

**Assignee, labels, status:** always set on creation — never create a bare issue and fix it later. Priority semantics ride on the `p0`/`p1` labels per the mapping above.

## Sync Rules

- New candidate (no matching open issue after dedup) → `createJiraIssue` (project MOXY, type Task) authored per the best-practices section above (full description, Subtasks for sub-items, Blocks links for dependencies). New issues default to Backlog.
- Existing issue changed (title, priority, assignee, labels, blocked context, column) → `editJiraIssue` + `transitionJiraIssue` as needed. Only touch issues that actually changed — an unchanged board is a no-op sync.
- Completion is authoritative in Jira: an issue in Done/In Review is complete/in-review; never resurface it as a new candidate (tombstone dedup, SKILL Step 5).
- Never delete or close Jira issues autonomously — surface anything questionable in Dorian's triage.

## Connector Mechanics & Gotchas (learned 2026-07-07, moxywolf.atlassian.net)

The Atlassian MCP connector handles reads and simple writes; anything needing an object-typed parameter fails and routes through the browser fallback.

**What the connector CAN do:** all reads (`getJiraIssue`, `searchJiraIssuesUsingJql`, `getVisibleJiraProjects`); `createJiraIssue` with flat params — including `parent` as a plain string key (that's how Subtasks attach: `issueTypeName: "Subtask"`, `parent: "MOXY-NNN"`); `createIssueLink` with flat `type` / `inwardIssue` / `outwardIssue` strings; `addCommentToJiraIssue`; `transitionJiraIssue`.

**What the connector CANNOT do:** any tool whose required parameter is an object — `editJiraIssue` (`fields`) and `createJiraIssue`'s `additional_fields` reject with "expected object, received string". Consequences: no description edits, no assignee setting, no label updates through the connector.

**Browser-REST fallback (the standard workaround):** run Jira REST v3 from the writer's logged-in browser via Claude in Chrome's `javascript_tool` on a moxywolf.atlassian.net tab. Same auth, full API:
- `PUT /rest/api/3/issue/<KEY>` with `{fields:{description:<ADF>}}` — description edits (descriptions are ADF: `doc > paragraph > text`, with `strong`/`code` marks)
- `PUT /rest/api/3/issue/<KEY>/assignee` with `{accountId}` — assignee
- `POST /rest/api/3/issue` with full `fields` (project, `parent:{key}`, `issuetype:{id:"10002"}`, summary, assignee, ADF description) — the preferred way to create Subtasks since it sets assignee in the same call
- `POST /rest/api/3/issueLink` / `DELETE /rest/api/3/issueLink/<id>` — links
- Avoid returning large JSON blobs from `javascript_tool` (the extension's DLP filter blocks them); return compact status arrays.

**Blocks link orientation (verified empirically — docs are ambiguous):** to make X "is blocked by" Y, pass `inwardIssue: Y` (the blocker) and `outwardIssue: X` (the blocked issue). Both the connector and raw REST follow this. Getting it backwards renders "blocks" on the wrong side; fix by DELETE + re-POST with the keys swapped.

**Retrofitting checklist tickets:** when a MOXY issue arrives with a `[ ]` checklist in its description (hand-written or from an older tool), convert it — one Subtask per checklist line (assignee inherited from the parent), rewrite the description to context + "split into the subtasks below" + bold Acceptance + dependency note, and turn any "depends on X" prose into a Blocks link. Verified pattern: MOXY-34/35/36/37 (2026-07-07).

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
