---
name: team-kanban
description: >
  This skill should be used when the user says "team kanban", "update the team board",
  "sync the kanban to Jira", "what's the team working on", "team task board",
  "sync the kanban", "team status board", "push tasks to Jira", "update the MOXY board",
  "team kanban update", "kanban sync", or any request to aggregate tasks from multiple
  sources into the team-visible Jira board. Also trigger when the user asks to
  "set up the team board" or references the MOXY board or the #general kanban digest.
  This skill aggregates from Obsidian KANBAN_VIEW.md, Google Drive Active Tasks,
  Google Calendar, Gmail, Slack DMs/group DMs/threads, and project channels
  (#sams, #stig-viewer, #assured-book, #jtbd_analyzer, #team-edify, #cms-migration) —
  then syncs the board to Jira (project MOXY) with best-practice issue authoring
  (Context/Acceptance/Notes descriptions, sub-items as real Subtasks, dependencies as
  issue links) and sends a slim daily digest to #general.
---

# Team Kanban — Multi-Source Task Board on Jira

Aggregate tasks from the personal operations stack (Obsidian vault, Google Drive Active Tasks, Google Calendar, Gmail) and Slack conversations (DMs, group DMs, threads, and project channels: #sams, #stig-viewer, #assured-book, #jtbd_analyzer, #team-edify, #cms-migration) into the team-visible Jira board (project **MOXY** at https://moxywolf.atlassian.net). Post a slim daily digest to #general linking to the board. Team input arrives via Jira directly or digest thread replies.

---

## Team Roster

The following people can be assigned tasks. Use their short name in `#assigned/` tags in Obsidian, their Slack user ID for digest mentions, and their Jira accountId (resolved once at setup via `lookupJiraAccountId`, stored in the config note) for issue assignment.

| Name | Short Name | Slack ID | Email | Role |
|------|-----------|----------|-------|------|
| Dorian Cougias | dorian | U08PV3UHTEX | dorianc@moxywolf.com | Founder/CEO |
| Philip Mudhir | phil | U096C551HBR | philm@moxywolf.com | Core team |
| Steven P | steven | U098H0X9CQ4 | stevenp@moxywolf.com | Core team |
| Michael Flanagan | michael | U09EB7N7B98 | michaelf@moxywolf.com | Core team |

Contractors can be added with `#assigned/firstname` tags. If no Slack ID is known, display the name as plain text rather than a mention.

---

## Kanban Columns

The board uses seven columns, ordered left to right:

| Column | Emoji | Purpose |
|--------|-------|---------|
| Backlog | :inbox_tray: | Captured but not yet prioritized |
| P0 - Today | :fire: | Max 3 items. Time-sensitive, blocks other work, or external deadline within 24h |
| P1 - This Week | :star: | Max 7 items. Important but not today-urgent. Must move before Friday |
| Blocked | :no_entry: | Waiting on external input. Include who/what is blocking and how long |
| In Progress | :hammer_and_wrench: | Actively being worked on right now |
| In Review | :mag: | Task marked complete by the assignee — awaiting confirmation from the person who created or assigned the task before moving to Done |
| Done | :white_check_mark: | Confirmed complete. Clear weekly on Monday |

---

## Operating Modes

### Mode 1: Full Sync (Default)

**Triggers:** "team kanban", "update the team board", "sync the kanban", "post the kanban", or the `/team-kanban` command.

Execute these steps in order:

#### Step 1: Locate the Vault

Check if the current workspace folder contains `KANBAN_VIEW.md` in a `Tasks/` directory. The vault is typically mounted at the Cowork workspace path. Set `${VAULT}` to the resolved root.

If the vault is not mounted, use `request_cowork_directory` to ask Dorian to mount it.

#### Step 2: Read Obsidian Kanban

Read `${VAULT}/Tasks/KANBAN_VIEW.md`. Parse the Obsidian Kanban plugin format:

- Each column is an H2 heading (e.g., `## :fire: P0 - Today (Max 3)`)
- Tasks are markdown checkboxes: `- [ ] Task description #tags`
- Completed tasks use: `- [x] Task description`
- Tags encode metadata: `#priority/p0`, `#cat/technical`, `#status/w` (waiting), `#project/sams`
- **Assignee tags:** `#assigned/dorian`, `#assigned/phil`, `#assigned/steven`, `#assigned/michael`, or `#assigned/contractor-name`
- Waiting items include context: who is being waited on and how long
- Tasks without an `#assigned/` tag default to Dorian (as the originator)

Also read the **done-archive** at `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-done-archive.md` into a `completed_index`. This is the tombstone ledger: items that were finished and moved off the board (Done cards older than 3 days are appended here by the `team-kanban-daily` task). Each line is `- YYYY-MM-DD — task text — @who — #project/name`. Capture each entry's leading date as its completion date. The `## ✅ Done` column of `KANBAN_VIEW.md` (with its `#completed/YYYY-MM-DD` tags) is part of the same ledger. Step 6's tombstone check (rule 1a) reads `completed_index` so finished work isn't resurrected.

Parse every task into a structured object:
```
{
  title: "Task description",
  column: "p0|p1|backlog|blocked|in-progress|in-review|done",
  tags: ["tag1", "tag2"],
  project: "project-name or null",
  category: "technical|outreach|admin|marketing|leadership|strategy",
  assigned_to: "short-name or dorian (default)",
  assigned_slack_id: "U-prefixed Slack ID or null",
  waiting_on: "person-name or null",
  waiting_since: "date or null",
  is_critical: boolean,
  subtasks: [ { title, done: boolean, assigned_to: "short-name or inherit" } ]
}
```

**Sub-items:** indented checkboxes under a card (`  - [ ] step`) are that card's sub-items. Capture every one, in order, with its own checked state and any `#assigned/` tag (default: inherit the parent's assignee). Sub-items become real Jira **Subtasks** in Step 8 — never flatten them into the parent's description.

**IMPORTANT:** The `source` (obsidian, slack, gmail, etc.) is internal metadata for deduplication only. NEVER display source tags on the Jira board or in digest messages. Tasks should show: title, project, assignee, and context — nothing else.

**Assignee resolution:** Look up the `#assigned/` tag value against the Team Roster table. If the short name matches, populate both `assigned_to` and `assigned_slack_id`. If it's an unknown name (contractor), set `assigned_to` to the tag value and `assigned_slack_id` to null.

**Slack thread assignments:** When team members add tasks via #general thread replies, they can include an assignment:
- `P1 Review press release draft #reggenome @phil` — assign to Phil
- `P1 Fix login bug #sams` — defaults to the person who posted it (look up their Slack ID in the roster)

#### Step 3: Read Google Drive Active Tasks

Fetch the Active Tasks document from Google Drive. The daily-ops plugin manages this document in the MoxyWolf Team Drive (driveId: `0AHxJ5CazJqxOUk9PVA`), folder ID `1MjSabHDWYjjnp17DshdO9pnESLyvm6Gs`.

1. Search for the document: `google_drive_search` with query `name contains 'Daily Ops - Active Tasks'`
2. Fetch contents with `google_drive_fetch` using the resolved document ID
3. Parse the task list — the format mirrors the Obsidian kanban with P0/P1/P2/P3 sections

**Deduplication:** Compare task titles from Google Drive against Obsidian kanban tasks. Use fuzzy matching (title similarity > 80%). When duplicates are found, prefer the Obsidian version (it has richer tag metadata) but note the Google Drive source. Flag any tasks that exist in Google Drive but NOT in the Obsidian kanban — these may be items added via mobile or the daily-ops standup that haven't been synced to the vault yet.

#### Step 4: Scan Google Calendar for Today

Pull today's events using `gcal_list_events`:

- Identify meetings that imply task commitments (prep-required meetings, review sessions, deadline-related events)
- Extract implicit tasks: "Prep for investor call at 3 PM" → task in P0 column
- Cross-reference against existing P0 items — don't duplicate what's already tracked
- Calendar-derived tasks get tagged with `source: calendar` and the meeting time

#### Step 5: Scan Gmail for Action Items

Use `gmail_search_messages` with targeted queries:

1. **Urgent threads:** `is:inbox newer_than:1d (urgent OR deadline OR ASAP OR "action required")`
2. **Unanswered action items:** `is:inbox newer_than:2d -from:me` — then filter for emails explicitly requesting action
3. **VIP contacts:** `is:inbox newer_than:2d from:(phil OR mudhir OR strikegraph OR gryphon OR fortreum)`
4. **Meeting summaries:** `subject:"Meeting summary" newer_than:2d` — catch meeting recap emails regardless of sender. For each result, read the full message body with `gmail_read_message` and extract action items, deadlines, owners, and decisions. Match names mentioned in the summary against the Team Roster to assign tasks. Meeting summaries often contain the most concrete next-steps that don't surface in any other source.

For each actionable email:
- Create a task entry with `source: gmail`
- Include sender name and one-line summary
- A single email that yields several concrete action items with one owner and one deliverable is ONE task with `subtasks`; unrelated action items are separate tasks
- Classify priority: explicit urgency markers → P0, VIP contacts → P1, meeting summary action items → P1, everything else → Backlog
- Deduplicate against existing tasks — if a task like "Follow up with Phil" already exists, don't create a duplicate from a Phil email

#### Step 5b: Scan Slack DMs, Group DMs, and Threads for Action Items

Use `slack_search_public_and_private` to find action items buried in team conversations. This catches commitments, assignments, and to-dos that exist only in chat — the gap that daily-ops does NOT cover.

**Search strategy — run these queries:**

1. **Group DMs with the team (last 48h):**
   - `after:[2-days-ago] in:<@U096C551HBR>` (Phil group DMs)
   - `after:[2-days-ago] in:<@U09EB7N7B98>` (Michael group DMs)
   - `after:[2-days-ago] in:<@U098H0X9CQ4>` (Steven group DMs)
   - Set `channel_types: "mpim,im"` to search DMs and group DMs

2. **Direct DMs between Dorian and each team member (last 48h):**
   - `from:<@U08PV3UHTEX> in:<@U096C551HBR> after:[2-days-ago]` (Dorian→Phil)
   - `from:<@U08PV3UHTEX> in:<@U09EB7N7B98> after:[2-days-ago]` (Dorian→Michael)
   - `from:<@U08PV3UHTEX> in:<@U098H0X9CQ4> after:[2-days-ago]` (Dorian→Steven)

3. **Keyword-targeted searches (last 7 days):**
   - `"need to" OR "action item" OR "to do" OR "can you" OR "please" after:[7-days-ago]` in DMs/group DMs
   - Look for commitment language: "I will", "I'll get that", "by end of day", "tomorrow", "this week"

4. **Project channels (last 48h):**
   Scan these project-specific channels for action items, decisions, and commitments:
   - `after:[2-days-ago] in:#sams`
   - `after:[2-days-ago] in:#stig-viewer`
   - `after:[2-days-ago] in:#assured-book`
   - `after:[2-days-ago] in:#jtbd_analyzer`
   - `after:[2-days-ago] in:#team-edify`
   - `after:[2-days-ago] in:#cms-migration`

   For each channel, extract:
   - Explicit action items and assignments
   - Decisions that imply follow-up work
   - Blocking issues or dependency callouts
   - Deadline mentions

   Map channel to project tag automatically:
   - `#sams` → `#project/sams`
   - `#stig-viewer` → `#project/stigviewer`
   - `#assured-book` → `#project/stigviewer` (book content line)
   - `#jtbd_analyzer` → `#project/jtbd-analyzer`
   - `#team-edify` → `#project/edify`
   - `#cms-migration` → `#project/cms-migration`

**Action item extraction rules:**

- Look for explicit assignments: "Can you [do X]", "@person [do X]", numbered lists of tasks
- Look for commitments: "I will [do X]", "I'll have that [by time]", "working on [X] tonight"
- Look for blocking language: "I need [X] before I can", "waiting on", "blocked by"
- Look for deadlines: "by tomorrow", "before the meeting", "end of week"

**For each extracted action item, create a task entry:**
```
{
  title: "Extracted task description",
  column: "p0|p1|backlog",
  assigned_to: "person who committed or was assigned",
  assigned_slack_id: "their Slack ID from roster",
  context: "brief quote or summary of the conversation",
  subtasks: [ { title, done: false, assigned_to } ]
}
```

When a conversation lays out numbered or listed steps toward one deliverable ("first X, then Y, then Z"), capture them as `subtasks` of one parent — they become Jira Subtasks in Step 8.

Note: Track the source internally for deduplication, but NEVER render source tags (like `slack`, `obsidian`, `gmail`) on the Jira board or in digest messages. The board should only show: task title, project, assignee, and relevant context.

**Priority assignment from Slack:**
- Explicit urgency ("ASAP", "today", "blocking", "before the meeting") → P0
- This-week commitments ("this week", "by Friday", general assignments) → P1
- Vague or future items → Backlog

**Deduplication:** Compare extracted Slack tasks against the Obsidian kanban and Google Drive tasks. Many Slack conversations will reference work already tracked. Only add genuinely new items. If a Slack conversation adds context to an existing task (e.g., a blocking dependency), update the existing task's notes rather than creating a duplicate.

---

#### Step 6: Merge and Reconcile

Combine all sources into a single task list. Resolution rules:

1a. **Tombstone check — dedup against Done and the archive, not just the open board (do this BEFORE rules 2–5).** Before adding ANY task surfaced from Google Drive, Calendar, Gmail, or Slack, match it against three sets: (a) every open `- [ ]` line across all columns, (b) the `## ✅ Done` column, and (c) the `completed_index` loaded from `team-kanban-done-archive.md` in Step 2. Use the same >80% fuzzy title match (tags/source stripped) already used for open-board dedup. **Recency gate:** if the candidate matches a Done or archived item AND the candidate's source-signal date is on or before that item's completion date (`#completed/YYYY-MM-DD` on the card, or the leading `YYYY-MM-DD` in the archive line), **suppress it** — the work is already done and this is the same signal resurfacing. Only add it when the candidate carries a genuinely newer signal than the completion date (a real recurrence); when you do, note "recurs after prior completion on `<date>`" in the task context. When ambiguous, suppress and surface it to Dorian's triage rather than re-adding. This rule exists because the originating Slack/email signal outlives the completion — without it, finished tasks get rewritten onto the board. (Team rule: `Taskade/_Shared Files/_shared-memory/feedback_kanban_check_tombstones_before_readd.md`.)
1. **Dual-authority completion model: Obsidian AND the Jira board are both authoritative for task completion status.** If an item is checked `[x]` in Obsidian *or* its linked MOXY issue is in Done (or In Review) in Jira, it is considered complete (or in review). During sync, apply the *union* of completion states — whichever source has the item further along wins, and the other source is updated to match. This means team members can resolve issues in Jira and Dorian can check items off in Obsidian, and neither will be overwritten. For all other task metadata (title, tags, column, priority), Obsidian remains the primary source. MOXY issues with no matching card (created by the team directly in Jira) are treated as additions.
2. **Google Drive tasks** that don't exist in Obsidian get added
3. **Calendar tasks** only appear if no existing task covers the same commitment
4. **Gmail tasks** only appear if genuinely new action items, not duplicates of tracked work
5. **Slack tasks** only appear if they represent commitments/assignments not already tracked in Obsidian or Google Drive. Slack is the richest source of team-distributed action items — many tasks are agreed upon in DMs but never make it to the formal kanban. These are high-value additions.
6. Enforce column limits: P0 max 3, P1 max 7. If over limit, flag for Dorian's triage. Also keep each card's column and its `#priority/pN` tag in agreement — a `#priority/p2` card parked in the P1 column is drift from a regenerate-without-clean-move; fix the column or the tag, don't leave them split.
7. **Never display source metadata on the board.** Source tracking is internal only — used for deduplication logic. Jira issues and digest messages show only: task title, project (label), assignee, blocking context, and deadlines.
8. **Checked items → In Review (not Done).** When a task is found with `- [x]` (checked) in the Obsidian kanban, or its Jira issue was moved to Done by the assignee (per the dual-authority rule above), do NOT move it directly to Done. Instead, move it to the **In Review** column. Resolve the reviewer using this priority order:

   **a) Volunteer override (highest priority):** If someone in Slack messages or threads has explicitly volunteered to review a specific task (e.g., "I'll review that", "I can verify"), assign them as the reviewer regardless of the default pairings below.

   **b) Default review pairings:** If no one volunteered, use these standing assignments:

   | Assignee (completes the task) | Default Reviewer |
   |-------------------------------|-----------------|
   | Dorian | Phil |
   | Phil | Dorian |
   | Michael | Steven |
   | Steven | Michael |

   **c) Fallback:** If the default reviewer is unavailable (e.g., not active on the board, or is the same person who created the task), fall back to Dorian as reviewer.

   - Tag the reviewer on the In Review item so they know to confirm: e.g., "Completed by Michael since 2026-04-10 — Review: Steven"
   - **Always include a "since YYYY-MM-DD" date** when moving an item to In Review. Use today's date (the date of the sync that moved it). This date lets the morning standup calculate how long a review has been waiting.
   - In Obsidian, use `#review/name` tag (e.g., `#review/phil`, `#review/steven`)
   - A task only moves from In Review → Done when the reviewer explicitly confirms (by transitioning the issue in Jira, checking it off in Obsidian, or posting confirmation in a Slack thread).
   This ensures every completed task gets a second pair of eyes before closure.

#### Step 7: Check for Team Input (Jira + digest thread)

Team members contribute in two ways; check both:

1. **Directly in Jira:** run `searchJiraIssuesUsingJql` with `project = MOXY AND created >= -3d` and filter out issues created by the sync itself (they carry the `#jira/` write-back; anything with no matching board card is candidate team input). Capture creator, summary, status, and labels.
2. **Digest thread replies:** search #general thread replies to the most recent kanban digest message that contain task additions (`P1 Task description #project`). Parse contributions as potential new tasks with `source: team-input` and the contributor's name.

#### Step 8: Sync the Board to Jira (project MOXY)

The team-visible board is the Jira board for project **MOXY** (cloudId and board URL in the config note). Obsidian remains the source of truth; Jira is the published, team-editable mirror. Read `references/jira-board-mapping.md` for the full column/status/label mapping.

**Card ↔ issue identity:** each board card carries a `#jira/MOXY-NNN` tag in Obsidian once it has a Jira twin.

- Card **without** a `#jira/` tag → create a MOXY issue (`createJiraIssue`, type Task) **authored per the best-practices section of the reference**: imperative summary; description with Context (originating signal, who/when), Acceptance (observable done-state), and Notes (blockers, reviewer, deadlines) — fill every section the source data allows. Every entry in the parsed `subtasks` array (from any source — Obsidian sub-checkboxes, multi-step email action items, multi-step Slack commitments) becomes one **Subtask** issue under the parent, with its own summary, assignee, and status (`Done` if its `done` flag is set) — never a `[ ]` checklist in the parent's description. Existing linked issues gain Subtasks the same way when a card grows new sub-items. Dependencies on other tracked work become issue links (`getIssueLinkTypes` → `createIssueLink`, type "Blocks"), not prose. Then write the `#jira/MOXY-NNN` tag back onto the card in KANBAN_VIEW.md. This write-back is automatic metadata maintenance — no approval needed. **Exception — bulk creation:** when a sync would create more than 5 new issues at once (e.g., the first sync after setup), show Dorian the list first and get explicit approval; a mass write to the shared tracker is team-visible.
- Card **with** a `#jira/` tag → fetch the issue; if the card changed (title, column, assignee, labels, blocked context), apply `editJiraIssue` and, for column moves, `getTransitionsForJiraIssue` → `transitionJiraIssue`. Statuses are discovered, never assumed — if a target status doesn't exist on the board, use the fallback label per the reference.
- MOXY issue with **no matching card** and not handled as team input (Step 7) → surface in Dorian's triage. Never delete or close Jira issues autonomously.

**Subtask completion:** subtasks obey the same dual-authority rule — a subtask Done in Jira checks the matching sub-item on the card, and vice versa. The parent card/issue moves to Done only when all its subtasks are Done.

**Assignees:** map `#assigned/` short names to Jira accountIds from the config note. Contractors without Jira accounts stay unassigned; their name goes in the issue description.

**Update batching:** only touch issues whose card actually changed. Don't rewrite every issue on every sync — the sync should be a no-op on an unchanged board.

**Standup sync marker:** the `last_standup_read` timestamp lives in the config note at `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md` (not on the board). The personal-os morning standup reads it to filter Done/In Review items to those changed since the last standup, and updates it after each standup. This sync preserves it untouched.

#### Step 9: Post the Slim Daily Digest to #general

> **Confirm before sending.** Show the exact message (or digest content) and the destination, then wait for explicit human approval before posting. The human can stop at any point. Never auto-send. For a public/shared-channel broadcast, treat it as high-stakes: a named person approves before it posts.

The #general digest is a public broadcast to the whole team. Render the exact digest message and name the destination (#general), then wait for Dorian's explicit approval before calling `slack_send_message`. Never auto-post the digest.

The digest is a **slim pointer, not the full board** — the board lives in Jira now. Read `references/jira-board-mapping.md` for the message template. Keep it under 150 words:
- Quick stats: total tasks, items by column, new items since last sync
- P0 items in full (these are urgent — everyone should see them)
- Blocked items over 7 days (escalations only)
- Link to the Jira board for everything else
- A prompt: add tasks in Jira directly, or reply in the thread

#### Step 10: Sync Back to Obsidian

This step is **mandatory** for completion state changes and **approval-gated** for new tasks.

**10a) Completion sync-back (automatic, no approval needed):**
If any linked issues were moved to Done or In Review in Jira but their cards are unchecked in Obsidian (detected in Step 6 via the dual-authority rule), update `${VAULT}/Tasks/KANBAN_VIEW.md` to match:
- Change the item from `- [ ]` to `- [x]` in its current column
- Move the item to the `## 🔍 In Review` section with the appropriate `#review/name` tag
- This ensures Obsidian and the Jira board stay in sync — no manual reconciliation needed

**10b) New task sync-back (requires Dorian's approval):**
If team members added tasks via Jira or Slack threads (Step 7), offer to write them back to `${VAULT}/Tasks/KANBAN_VIEW.md`:
- Present new team-contributed items for Dorian's approval
- If approved, add them to the appropriate column in KANBAN_VIEW.md
- Use the Edit tool to append to the correct section — never overwrite the entire file

---

### Mode 2: Quick Update

**Triggers:** "quick kanban update", "just refresh the board", "push current tasks to Jira"

Skip Steps 4, 5, and 5b (calendar/email/Slack DM scanning). Only read Obsidian + Google Drive, merge, and sync to Jira. Skip the digest. Faster for mid-day refreshes when the full intelligence scan isn't needed.

---

### Mode 3: Setup

**Triggers:** "set up the team kanban", "create the team board", "initialize the kanban board", or the `/team-kanban-setup` command.

One-time setup flow:

> **Confirm before sending.** Show the exact message (or digest content) and the destination, then wait for explicit human approval before posting. The human can stop at any point. Never auto-send. For a public/shared-channel broadcast, treat it as high-stakes: a named person approves before it posts.

Setup performs the first bulk write to the shared Jira tracker and the first #general broadcast — both team-visible, both gated. Before steps 4 and 6, show Dorian the exact content (issue list / intro message) plus the destination, and wait for his explicit approval. Never auto-create or auto-post.

1. **Verify Jira access:** `getAccessibleAtlassianResources` → capture the cloudId; `getVisibleJiraProjects` → confirm project **MOXY** is visible and capture its issue types (expect Task)
2. **Resolve roster accountIds:** `lookupJiraAccountId` for each team member email in the roster; record them for the config note
3. **Check board statuses:** discover the available statuses (via `getTransitionsForJiraIssue` on any existing issue, or the project metadata). If "Blocked" or "In Review" statuses are missing, tell Dorian he can add those columns in Jira board settings for a 1:1 mapping — the sync degrades gracefully to labels (`blocked`, `in-review`) if he doesn't
4. **First full sync (after approval):** run Mode 1 Steps 1–8. The first sync bulk-creates a MOXY issue for every open card — show Dorian the full list of issues to be created and get his explicit approval before creating them
5. **Find #general:** Use `slack_search_channels` to find the #general channel and capture its channel ID
6. **Post introduction (after approval):** Send an introductory message to #general explaining the Jira board, how to add tasks (in Jira directly, or reply in digest threads), and linking to the board
7. **Store config:** Write a config note to `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md` per the template in `references/jira-board-mapping.md` (cloudId, project key, board URL, discovered statuses, roster accountIds, #general channel ID, column configuration, `last_standup_read`)
8. **Offer to set up a scheduled task** using the Cowork scheduled-tasks system for daily automated syncs

---

## Finding Existing Config

Before creating anything new, always check for existing config:

1. Read `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md` if it exists
2. If it contains a cloudId + project key, verify access with `getVisibleJiraProjects` (cheap read)
3. If it contains roster accountIds and a #general channel ID, use them directly instead of re-resolving

If the config file doesn't exist or the Jira project is unreachable, fall back to discovery or prompt for setup.

---

## Voice and Formatting

The Slack digest message should be direct and scannable:

- Lead with the date and a one-line status summary
- Use Slack mrkdwn formatting (`*bold*` not `**bold**`, `<url|text>` for links)
- No hedging. "3 items blocked" not "there appear to be some blocked items"
- Include specific names for blocked items: "Waiting on Mark Johnston since March 18"
- Jira issue summaries stay plain: title only, no tags, no source metadata — semantics go in labels and the description
- Keep the digest message under 150 words — the Jira board has the full detail

---

## Error Handling

- **Vault not mounted:** Ask Dorian to mount it. Don't proceed without the Obsidian kanban.
- **Google Drive unreachable:** Post what you have from Obsidian alone. Note the gap in the digest.
- **Jira unreachable or Atlassian MCP not connected:** Don't fake the sync. Save the merged board to `${VAULT}/Tasks/team-kanban-latest.md`, note the gap, and tell Dorian the Atlassian connector needs attention.
- **Transition fails (status missing):** Apply the fallback label per `references/jira-board-mapping.md` and note it in the sync report.
- **Slack digest send fails:** The board is already synced to Jira — report the digest failure and offer to retry.
- **Column limits exceeded:** Don't silently drop items. Flag the overflow in the digest: "P0 has 5 items (limit: 3). Triage needed."

## Restraint layer (ponytail)

Ingest the `/ponytail-debt` ledger: each `ponytail:` shortcut lacking an upgrade trigger becomes a tech-debt card on the board. See the `ponytail` skill — the YAGNI ladder (does it need to exist; stdlib before custom; native before dependency; one line before fifty), never cutting validation, error handling, security, or accessibility.
