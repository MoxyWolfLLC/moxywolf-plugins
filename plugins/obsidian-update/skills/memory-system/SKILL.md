---
name: memory-system
description: ""
---

# Memory System — Vault-Native Read/Write Operations

> Sub-skill for the obsidian-update plugin. Handles all memory persistence operations.
> Called by the personal-os skill — not typically invoked directly.
> Also called by the Council deliberation-engine and pattern-memory skills for cross-plugin vault operations.

---

## MEMORY FILE LOCATIONS

All memory files live in the MoxyWolf Obsidian vault:

```
${VAULT}/
├── _System/
│   ├── MEMORY.md              # Layer 1: Tacit knowledge (THE critical file)
│   ├── IDENTITY.md            # Operating identity and principles
│   └── backups/               # MEMORY.md backup copies
│       └── MEMORY-YYYY-MM-DD-HHMMSS.md
├── Daily Journal/             # Layer 2: Daily notes
│   ├── YYYY-MM-DD.md
│   └── ...
├── Projects/                  # Layer 3: Project knowledge
│   └── [Project]/11-Knowledge/*.md
├── _Shared Knowledge/         # Layer 3: Cross-cutting knowledge
│   ├── [Area]/*.md
│   └── Agents and Plugins/
│       ├── council-model-performance.md    # Synced from Council pattern-memory
│       ├── council-routing-intelligence.md # Synced from Council pattern-memory
│       └── council-deliberation-log.md     # Deliberation history log
├── People/                    # Layer 3: Contact knowledge
│   └── [Full Name].md
├── Tasks/                     # Kanban + individual task files
│   ├── KANBAN_VIEW.md
│   ├── DASHBOARD.md           # Read-only (Dataview)
│   └── *.md
└── GOALS.md
```

**Dual access pattern:** In interactive Cowork sessions, the vault is the mounted workspace folder — read/write using standard Read/Write/Edit tools. In scheduled task VMs, the vault must be accessed via Google Drive API (`proxy_execute` via `RUBE_REMOTE_WORKBENCH` with Composio googledrive, `supportsAllDrives=true`). The parent personal-os skill resolves the vault path and determines which access method to use.

---

## OPERATION: READ MEMORY

Called at the start of every session (Step 0 in main skill).

### Interactive session (vault mounted):
```
1. Read ${VAULT}/_System/IDENTITY.md
2. Read ${VAULT}/_System/MEMORY.md
3. List files in ${VAULT}/Daily Journal/ sorted descending by filename
4. Read top 3 daily note files
5. Return combined context (do NOT echo to user)
```

### Scheduled task VM (Google Drive API):
```
1. Search Google Drive for "IDENTITY.md" in MoxyWolf Vault/_System/
   - Use proxy_execute GET /files with q="name='IDENTITY.md'" and supportsAllDrives=true
2. Read content via proxy_execute GET /files/{id} with alt=media
3. Repeat for MEMORY.md
4. Search for files in MoxyWolf Vault/Daily Journal/ sorted by name desc
5. Read top 3 results
```

If MEMORY.md doesn't exist, return warning string for the main skill to handle.

---

## OPERATION: WRITE DAILY NOTE

Called during standup, triage, review, or extraction.

**Input:** Structured data from the calling mode (energy, priorities, events, facts).

**Process:**
1. Determine today's date: `YYYY-MM-DD`
2. Check if `${VAULT}/Daily Journal/YYYY-MM-DD.md` exists
   - If yes: append to existing note under appropriate section headers (use Edit tool)
   - If no: create new daily note from template (use Write tool)
3. Write file to disk

**Template:**
```markdown
---
title: "YYYY-MM-DD — Day of Week"
date: YYYY-MM-DD
type: standup
tags: [daily, standup]
participants: [dorian]
status: active
---

# YYYY-MM-DD — Day of Week

## Energy
- Sleep: [data or "not available"]
- Assessment: [green/yellow/red]
- Stepson week: [yes/no/unknown]

## Today's Board

### 🔥 P0 — Do Today (Max 3)
- [ ] Task #priority/p0 #cat/category #status/n

### ⭐ P1 — This Week
- [ ] Task #priority/p1 #cat/category #status/n

### ⏳ Waiting On
- [ ] Task — waiting on [person] since YYYY-MM-DD #status/w

## Calendar
- [HH:MM] Event description

## Inbox Intelligence
- [Priority] Email summary → action needed

## Decisions Made
- [Decision with rationale]

## Facts Extracted
- [Durable facts discovered today]

## Open Threads
- [Items needing follow-up tomorrow]

## Extraction Status
- Extracted: no
```

**Note:** The "Today's Board" section is populated during standup by pulling P0 and P1 tasks from `${VAULT}/Tasks/KANBAN_VIEW.md`. These checkboxes are compatible with the Obsidian Tasks plugin — Dorian can check them off during the day.

---

## OPERATION: UPDATE MEMORY.MD

Called during weekly review and nightly extraction.

**Process:**
1. Read current `${VAULT}/_System/MEMORY.md`
2. **Create backup** before modifying (see BACKUP SAFETY below)
3. Parse into sections (split on `## ` headers)
4. For each new fact to add:
   a. Determine which section it belongs to
   b. Check for duplicates or superseded facts
   c. If superseding an old fact: mark old fact with `~~strikethrough~~` and `[superseded YYYY-MM-DD]`
   d. Add new fact with timestamp
5. Apply hybrid memory decay (frequency + recency):
   - **High frequency (5+) + recent (< 14 days):** keep hot — active knowledge
   - **High frequency (5+) + stale (14-30 days):** keep warm — monitor
   - **High frequency (5+) + old (30+ days):** demote to Cold Storage
   - **Low frequency (1-2) + recent (< 14 days):** keep warm — new, give it time
   - **Low frequency (1-2) + stale (14-30 days):** demote to Cold Storage
   - **Low frequency (1-2) + old (30+ days):** Cold Storage — archive candidate
   - **Resurrection:** if a cold-storage fact is accessed, immediately promote back + reset decay clock
   - Also apply to `## Shorthand & Decoder Ring`: terms/people used 3+ times this week stay hot; not used in 2+ weeks AND low total access → demote
6. Update the header timestamp: `> Last updated: YYYY-MM-DD HH:MM UTC`
7. Update the fact count: `> Facts: N active, M superseded`
8. Write the complete updated file to `${VAULT}/_System/MEMORY.md`

**CRITICAL RULES:**
- NEVER delete facts. Supersede them.
- NEVER overwrite MEMORY.md without reading it first.
- Always preserve the file structure (headers, sections).
- If unsure about a fact's section, put it in "Preferences & Patterns" as default.
- Security/credential facts go in "Security & Access" — NEVER store actual secrets, only patterns and access notes.

---

## OPERATION: UPDATE VAULT KNOWLEDGE

Replaces the old "Update Knowledge Graph" operation. Called during nightly extraction when significant new entities are encountered.

**Process:**
1. Identify entities from the day's work (projects, people, tools, concepts)
2. For each entity:
   a. **If it maps to an existing project** → write/update in `${VAULT}/Projects/[Project]/11-Knowledge/`
   b. **If cross-cutting** → write/update in `${VAULT}/_Shared Knowledge/[relevant area]/`
   c. **If it's a person** → write/update in `${VAULT}/People/[Full Name].md`
3. All vault notes MUST use the vault's YAML frontmatter convention:
   ```yaml
   ---
   title: Note Title
   date: YYYY-MM-DD
   project: project-name
   type: research | insight | reference
   tags: [relevant, tags]
   status: active
   ---
   ```
4. Use wikilinks for cross-references: `[[Projects/SAMS/00-Hub/SAMS Index]]`
5. File naming: kebab-case with dates per CLAUDE.md conventions

**Entity naming convention:**
- Projects: match existing vault project folder names
- People: `Full Name.md` (e.g., `Brian Kelley.md`)
- Topics: `descriptive-slug-YYYY-MM-DD.md`

---

## OPERATION: MEMORY SEARCH

Called when Dorian asks "what do you know about X?"

**Process:**
1. Search `${VAULT}/_System/MEMORY.md` for keyword matches (case-insensitive)
2. Search `${VAULT}/Daily Journal/` (last 30 days) for keyword matches
3. Search `${VAULT}/Projects/` and `${VAULT}/_Shared Knowledge/` for keyword matches
4. Read matching files for full context
5. Compile results with source attribution:
   - "[From MEMORY.md]" — tacit knowledge
   - "[From Daily Journal YYYY-MM-DD]" — specific date context
   - "[From Projects/SAMS/11-Knowledge/note-name]" — project knowledge
   - "[From People/Brian Kelley]" — contact knowledge
6. Return compiled results to user

---

## OPERATION: COUNCIL INTEGRATION

Cross-plugin operations that connect the Council deliberation engine to the vault's knowledge layer. The memory-system acts as the vault's write gatekeeper — Council skills prepare data, memory-system writes it in the correct format.

### Sub-operation A: Provide Context to Council

Called by the Council deliberation-engine Pre-Step A when it requests vault context before running a deliberation.

**This is a READ-ONLY operation.** The Council reads; it doesn't write to the memory system during this step.

**Process:**

1. Read `${VAULT}/_System/MEMORY.md` and summarize to ~500 tokens:
   - Active projects (names + one-line status)
   - Current priorities (P0/P1 items if available)
   - Relevant shorthand/decoder entries
   - Key relationships (if the query references people)
   - Omit Cold Storage, Security & Access, and superseded facts
2. If the deliberation query references a known project (match against project names in MEMORY.md or folder names in `${VAULT}/Projects/`), read that project's index file (`00-Hub/[Project] Index.md`) and summarize key context: current phase, recent decisions, open questions.
3. If `${VAULT}/_Shared Knowledge/Agents and Plugins/council-deliberation-log.md` exists, read the last 5 entries from the table.
4. Return the combined context as a structured block:

```
VAULT CONTEXT (for Council Stage 1 injection):
- memory_summary: [500-token MEMORY.md summary]
- project_context: [project index summary, or null if no project match]
- recent_deliberations: [last 5 log entries, or empty if no log exists]
```

**Callers:** deliberation-engine Pre-Step A.

### Sub-operation B: Accept Council Decision Records

Called by the Council deliberation-engine Step 8d (after each deliberation) and pattern-memory Operation 7 (vault sync).

**This is the WRITE path.** Council sends structured data; memory-system writes it to the vault in the correct format.

**Process:**

1. **Validate incoming data.** The caller provides:
   - `record_type`: one of `decision_record`, `model_performance`, `routing_intelligence`, `deliberation_log_entry`
   - `project`: project name (or `null` for cross-cutting knowledge)
   - `content`: the note body (markdown)
   - `frontmatter`: YAML frontmatter fields (title, date, type, tags, etc.)
   - `deliberation_id`: for dedup checking

2. **Deduplicate.** Check if a note with this `deliberation_id` already exists:
   - For decision records: search the target project folder for files containing the deliberation ID
   - For log entries: check the last 20 rows of `council-deliberation-log.md`
   - If duplicate found: skip write, return `already_exists: true`

3. **Write based on record type:**

   - **`decision_record`**: Write to `${VAULT}/Projects/[project]/11-Knowledge/DR-NNN-council-[query-slug].md` if project is specified, or `${VAULT}/_Shared Knowledge/Agents and Plugins/council-decision-[query-slug]-YYYY-MM-DD.md` if cross-cutting. Validate frontmatter includes required fields (title, date, project, type: decision, tags, status). Add cross-links: `[[_Shared Knowledge/Agents and Plugins/council-deliberation-log|Deliberation Log]]`.

   - **`model_performance`**: Write/overwrite `${VAULT}/_Shared Knowledge/Agents and Plugins/council-model-performance.md`. This is a living reference document — always overwritten with the latest data.

   - **`routing_intelligence`**: Write/overwrite `${VAULT}/_Shared Knowledge/Agents and Plugins/council-routing-intelligence.md`. Same pattern — living reference, always current.

   - **`deliberation_log_entry`**: Append a row to the table in `${VAULT}/_Shared Knowledge/Agents and Plugins/council-deliberation-log.md`. If the file doesn't exist, create it with the template from FIRST-RUN INITIALIZATION step 2.5. Keep the last 50 entries visible in the main table; if the table exceeds 50 rows, move older entries into a collapsed `<details>` block at the bottom.

4. **Update project index** (decision records only). If the decision record maps to a project, edit that project's index file (`00-Hub/[Project] Index.md`) to add a one-line entry under "Recent Activity" or "Key Decisions" with a wikilink to the new note.

**Callers:** deliberation-engine Step 8d, pattern-memory Operation 7.

### Sub-operation C: Accept Council Verification Feedback

Called by the obsidian-update skill Step 2.5 (Council Verification Gate) when Council has evaluated a knowledge extraction plan.

**Process:**

1. Receive the Council's assessment, which includes:
   - `adjustments`: array of suggested changes (re-attribute to different project, add missing item, remove ephemeral item)
   - `approved_items`: items Council agreed should be captured
   - `flagged_items`: items Council flagged as questionable (ephemeral state, already documented, wrong attribution)

2. For each adjustment Dorian approved:
   - **Re-attribution**: update the target path for the affected item in the extraction plan
   - **Add missing item**: append a new item to the extraction plan with Council's suggested content and path
   - **Remove flagged item**: remove the item from the extraction plan

3. Return the adjusted extraction plan to obsidian-update for Step 3 (Write the Notes).

**Callers:** obsidian-update Step 2.5.

### Cross-Plugin Coordination Notes

- **Memory-system is the ONLY writer to the vault.** Council skills (deliberation-engine, pattern-memory) prepare structured data and pass it to memory-system sub-operations. This prevents write conflicts and ensures all vault notes conform to frontmatter conventions, naming patterns, and cross-linking rules.
- **Deduplication is memory-system's job.** If both Council (Step 8d) and obsidian-update want to write about the same deliberation, memory-system checks the deliberation ID against existing log entries and decision records. First write wins; second write gets `already_exists: true`.
- **Vault availability is optional.** If the vault isn't mounted or accessible, Council operations proceed normally — they just skip the vault write steps. Pattern-memory's `council-memory.json` remains the authoritative working copy. The vault notes are the durable, cross-linked, human-browsable layer on top.

---

## BACKUP SAFETY

On every MEMORY.md write:
1. Create timestamped backup: `${VAULT}/_System/backups/MEMORY-YYYY-MM-DD-HHMMSS.md`
2. Keep last 7 backups. Delete older ones.
3. This protects against accidental corruption during writes.

---

## FIRST-RUN INITIALIZATION

If `${VAULT}/_System/` doesn't exist (first time using this plugin with the vault):

1. **Create directories:**
   - `${VAULT}/_System/`
   - `${VAULT}/_System/backups/`
   - `${VAULT}/Daily Journal/` (if not exists)
   - `${VAULT}/Tasks/` (if not exists)

2. **Create IDENTITY.md** at `${VAULT}/_System/IDENTITY.md`:
   ```markdown
   # IDENTITY

   **Name:** Chief of Staff
   **Role:** Dorian's executive operating partner — a persistent AI chief of staff who manages priorities, tracks context across sessions, and pushes back when needed.
   **Operator:** Dorian Cougias, CEO of MoxyWolf LLC
   **Platform:** Claude Desktop (Cowork mode) with scheduled tasks, MCP integrations, and plugin ecosystem

   ## Operating Principles

   1. **Be direct.** No hedging, no filler. Say what needs to be said.
   2. **Set context.** Always explain the "why" before the "what."
   3. **Close the loop.** Every task gets a resolution — done, blocked, or deferred with a reason.
   4. **Push back.** Flag problems, point out context-switching, suggest better approaches.
   5. **Persist.** Write durable facts to memory. If it matters tomorrow, it gets written down today.

   ## Communication Style

   - Professional but warm. Never corporate-speak.
   - MoxyWolf voice: wild intelligence through structured precision.
   - Match Dorian's energy level (inferred from health data and time of day).
   - Ask clarifying questions rather than guessing.

   ## Trust Level

   Rung 3 of 4: **Act Within Bounds**
   - Read all data sources freely
   - Draft content and queue for approval before sending externally
   - Execute internal operations (task management, memory updates, file organization)
   - Escalate: financial transactions, public-facing content, security-sensitive operations
   ```

2.5. **Create Council integration files:**
   - Create `${VAULT}/_Shared Knowledge/Agents and Plugins/` directory if it doesn't exist
   - Create empty `council-deliberation-log.md` at `${VAULT}/_Shared Knowledge/Agents and Plugins/council-deliberation-log.md`:
     ```markdown
     ---
     title: "Council Deliberation Log"
     date: YYYY-MM-DD
     type: reference
     tags: [council, deliberation-log]
     status: active
     ---

     # Council Deliberation Log

     > Cross-linked from [[_Shared Knowledge/Agents and Plugins/council-model-performance|Model Performance]] and [[_Shared Knowledge/Agents and Plugins/council-routing-intelligence|Routing Intelligence]].

     | ID | Date | Query Summary | Chairman | Confidence | Cost | Rating |
     |----|------|---------------|----------|------------|------|--------|
     ```

3. **Create MEMORY.md** at `${VAULT}/_System/MEMORY.md`:
   ```markdown
   # Memory — Dorian Cougias
   > Last updated: YYYY-MM-DD HH:MM UTC
   > Facts: 0 active, 0 superseded

   ## Shorthand & Decoder Ring
   > Hot cache — target ~30 people, ~30 terms.

   | Nickname | Resolves To | Context |
   |----------|-------------|---------|

   | Term | Meaning | Context |
   |------|---------|---------|

   | Codename | Project |
   |----------|---------|

   ## Who Dorian Is

   ## Preferences & Patterns

   ## Active Projects

   ## Relationships & Contacts

   ## Security & Access

   ## Decisions Log

   ## Life Rhythm

   ## Cold Storage
   ```

4. **Create empty KANBAN_VIEW.md** at `${VAULT}/Tasks/KANBAN_VIEW.md` (if not exists):
   ```markdown
   ---

   kanban-plugin: board

   ---

   ## 📥 Backlog

   ## 🔥 P0 - Today (Max 3)

   ## ⭐ P1 - This Week (Max 7)

   ## 📅 P2 - Scheduled

   ## 💭 P3 - Someday

   ## ⏳ Waiting On

   ## ✅ Done

   %% kanban:settings
   {"kanban-plugin":"board"}
   %%
   ```

5. **Log initialization** in a new daily note at `${VAULT}/Daily Journal/YYYY-MM-DD.md`

6. **Notify Dorian:** "First-run initialization complete. Created _System/ directory with empty MEMORY.md and IDENTITY.md. I'll build context as we work."
