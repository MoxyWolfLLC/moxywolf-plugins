---
name: team-kanban
description: >
  This skill should be used when the user says "team kanban", "update the team board",
  "post the kanban to Slack", "what's the team working on", "team task board",
  "sync the kanban", "team status board", "push tasks to Slack", "update #general board",
  "team kanban update", "kanban sync", or any request to aggregate tasks from multiple
  sources into a team-visible Slack kanban board. Also trigger when the user asks to
  "set up the team board", "create the team canvas", or references the #general kanban.
  This skill aggregates from Obsidian KANBAN_VIEW.md, Google Drive Active Tasks,
  Google Calendar, Gmail, Slack DMs/group DMs/threads, and project channels
  (#sams, #stig-viewer, #assured-book, #jtbd_analyzer, #team-edify, #cms-migration) —
  then posts to a persistent Slack Canvas and sends a daily digest message to #general.
---

# Team Kanban — Multi-Source Task Board for Slack

Aggregate tasks from the personal operations stack (Obsidian vault, Google Drive Active Tasks, Google Calendar, Gmail) and Slack conversations (DMs, group DMs, threads, and project channels: #sams, #stig-viewer, #assured-book, #jtbd_analyzer, #team-edify, #cms-migration) into a team-visible Slack Canvas kanban board with six columns. Post a daily formatted digest to #general. Support manual team input via Slack threads.

---

## Team Roster

The following people can be assigned tasks. Use their short name in `#assigned/` tags in Obsidian, or their Slack user ID for Canvas/message mentions.

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
  is_critical: boolean
}
```

**IMPORTANT:** The `source` (obsidian, slack, gmail, etc.) is internal metadata for deduplication only. NEVER display source tags on the Canvas or in digest messages. Tasks should show: title, project, assignee @-mention, and context — nothing else.

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
  context: "brief quote or summary of the conversation"
}
```

Note: Track the source internally for deduplication, but NEVER render source tags (like `slack`, `obsidian`, `gmail`) on the Canvas or in digest messages. The board should only show: task title, project, assignee, and relevant context.

**Priority assignment from Slack:**
- Explicit urgency ("ASAP", "today", "blocking", "before the meeting") → P0
- This-week commitments ("this week", "by Friday", general assignments) → P1
- Vague or future items → Backlog

**Deduplication:** Compare extracted Slack tasks against the Obsidian kanban and Google Drive tasks. Many Slack conversations will reference work already tracked. Only add genuinely new items. If a Slack conversation adds context to an existing task (e.g., a blocking dependency), update the existing task's notes rather than creating a duplicate.

---

#### Step 6: Merge and Reconcile

Combine all sources into a single task list. Resolution rules:

1. **Dual-authority completion model: Obsidian AND the Slack Canvas are both authoritative for task completion status.** If an item is checked `[x]` in *either* Obsidian or the Slack Canvas, it is considered complete. During sync, apply the *union* of checked states — whichever source has the item marked off wins, and the other source is updated to match. This means team members can check items off on the Canvas and Dorian can check items off in Obsidian, and neither will be overwritten. For all other task metadata (title, tags, column, priority), Obsidian remains the primary source. New tasks found only in the Canvas (added by team via thread replies) are treated as additions.
2. **Google Drive tasks** that don't exist in Obsidian get added
3. **Calendar tasks** only appear if no existing task covers the same commitment
4. **Gmail tasks** only appear if genuinely new action items, not duplicates of tracked work
5. **Slack tasks** only appear if they represent commitments/assignments not already tracked in Obsidian or Google Drive. Slack is the richest source of team-distributed action items — many tasks are agreed upon in DMs but never make it to the formal kanban. These are high-value additions.
6. Enforce column limits: P0 max 3, P1 max 7. If over limit, flag for Dorian's triage
7. **Never display source metadata on the board.** Source tracking is internal only — used for deduplication logic. The Canvas and digest messages show only: task title, project (italic), assignee (@-mention), blocking context, and deadlines.
8. **Checked items → In Review (not Done).** When a task is found with `- [x]` (checked) on the Canvas or in the Obsidian kanban (per the dual-authority rule above), do NOT move it directly to Done. Instead, move it to the **In Review** column. Resolve the reviewer using this priority order:

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
   - A task only moves from In Review → Done when the reviewer explicitly confirms (by checking it off from In Review, or by posting confirmation in a Slack thread).
   This ensures every completed task gets a second pair of eyes before closure.

#### Step 7: Check for Team Input from Slack

Search the existing Slack Canvas (if one exists) and the #general channel for team-contributed tasks:

1. Search Slack for the existing Team Kanban Canvas: `slack_search_public` with query `"Team Kanban" type:canvas in:#general`
2. If a Canvas exists, read it with `slack_read_canvas` to get its ID and current content
3. Search for thread replies to the most recent kanban digest message that contain task additions (team members posting new items in the thread)
4. Parse any thread contributions as potential new tasks with `source: team-input` and the contributor's name

#### Step 8: Build the Slack Canvas

Format the merged task list into Canvas-flavored Markdown. Read `references/slack-canvas-format.md` for the exact template.

**If no Canvas exists yet:**
- Create one with `slack_create_canvas` titled "Team Kanban — MoxyWolf"
- Post the Canvas link to #general with context message

**If Canvas already exists:**
- Update it with `slack_update_canvas` using `action: replace` (full board refresh)
- The Canvas ID should be stored from the previous run — search for it if needed

**Standup sync marker:** The Canvas header includes two timestamps:
- `*Last updated:*` — set to the current date/time of this team-kanban sync
- `*Last standup read:*` — **preserve the existing value** from the previous Canvas content. Do NOT overwrite it. This timestamp is written by the morning standup (personal-os plugin) when it reads the Canvas, so the standup can determine which Done/In Review items are new since the last read. If the Canvas is being created for the first time, set this to "never".

When the personal-os morning standup reads the Canvas (Step 2 of its flow), it should:
1. Read the `Last standup read` timestamp to filter Done items to only those confirmed after that date
2. After completing the standup, update ONLY the `Last standup read` line on the Canvas to the current timestamp using `slack_update_canvas` with `action: replace` on just the header section — or carry the new timestamp forward to the next team-kanban sync

#### Step 9: Post Daily Digest to #general

After updating the Canvas, post a formatted summary message to #general using `slack_send_message`. Read `references/slack-canvas-format.md` for the message template.

The digest includes:
- Quick stats: total tasks, items by column, new items since last sync
- P0 items in full (these are urgent — everyone should see them)
- Blocked items with escalation status
- Link to the full Canvas for the complete board
- A prompt inviting team members to add tasks by replying in the thread

#### Step 10: Sync Back to Obsidian

This step is **mandatory** for completion state changes and **approval-gated** for new tasks.

**10a) Completion sync-back (automatic, no approval needed):**
If any items were checked on the Slack Canvas but unchecked in Obsidian (detected in Step 6 via the dual-authority rule), update `${VAULT}/Tasks/KANBAN_VIEW.md` to match:
- Change the item from `- [ ]` to `- [x]` in its current column
- Move the item to the `## 🔍 In Review` section with the appropriate `#review/name` tag
- This ensures Obsidian and the Canvas stay in sync — no manual reconciliation needed

**10b) New task sync-back (requires Dorian's approval):**
If team members added tasks via Slack threads (Step 7), offer to write them back to `${VAULT}/Tasks/KANBAN_VIEW.md`:
- Present new team-contributed items for Dorian's approval
- If approved, add them to the appropriate column in KANBAN_VIEW.md
- Use the Edit tool to append to the correct section — never overwrite the entire file

---

### Mode 2: Quick Update

**Triggers:** "quick kanban update", "just refresh the board", "push current tasks to Slack"

Skip Steps 4, 5, and 5b (calendar/email/Slack DM scanning). Only read Obsidian + Google Drive, merge, and push to Slack. Faster for mid-day refreshes when the full intelligence scan isn't needed.

---

### Mode 3: Setup

**Triggers:** "set up the team kanban", "create the team board", "initialize the kanban canvas", or the `/team-kanban-setup` command.

One-time setup flow:

1. **Find #general:** Use `slack_search_channels` to find the #general channel and capture its channel ID
2. **Create the Canvas:** Create the initial Team Kanban Canvas with `slack_create_canvas`
3. **Post introduction:** Send an introductory message to #general explaining the board, how to add tasks (reply in thread), and linking to the Canvas
4. **Store config:** Write a config note to `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md` with:
   - Canvas ID
   - #general channel ID
   - Date of setup
   - Column configuration
5. **Offer to set up a scheduled task** using the Cowork scheduled-tasks system for daily automated posting

---

## Finding Existing Config

Before creating anything new, always check for existing config:

1. Read `${VAULT}/_Shared Knowledge/Agents and Plugins/team-kanban-config.md` if it exists
2. If it contains a Canvas ID, verify the Canvas still exists with `slack_read_canvas`
3. If it contains a #general channel ID, use it directly instead of searching

If the config file doesn't exist or the Canvas is gone, fall back to search or prompt for setup.

---

## Voice and Formatting

The Slack digest message should be direct and scannable:

- Lead with the date and a one-line status summary
- Use Slack mrkdwn formatting (`*bold*` not `**bold**`, `<url|text>` for links)
- No hedging. "3 items blocked" not "there appear to be some blocked items"
- Include specific names for blocked items: "Waiting on Mark Johnston since March 18"
- The Canvas uses Canvas-flavored Markdown (standard Markdown headers, links, checklists)
- Keep the digest message under 300 words — the Canvas has the full detail

---

## Error Handling

- **Vault not mounted:** Ask Dorian to mount it. Don't proceed without the Obsidian kanban.
- **Google Drive unreachable:** Post what you have from Obsidian alone. Note the gap in the digest.
- **Canvas creation fails:** Fall back to posting the full board as a Slack message instead.
- **Slack send fails:** Save the formatted output to `${VAULT}/Tasks/team-kanban-latest.md` as a backup.
- **Column limits exceeded:** Don't silently drop items. Flag the overflow in the digest: "P0 has 5 items (limit: 3). Triage needed."
