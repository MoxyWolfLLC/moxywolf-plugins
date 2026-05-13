---
name: session-end
description: This skill should be used when the user says "session-end", "end session", "wrap session", "save handoff", "/session-end", "we're done", "sign off", or any request to wrap up a Cowork session and persist what was done plus what's next for the following session. It scans the conversation for what landed, what's still open, what's uncommitted, asks who authored this handoff and whether it's a baton-pass to a teammate, then writes a canonical-named handoff document (with `author` and optional `for` frontmatter fields auto-populated) to the project's `00 – Project Hub/cowork-session-handoff.md`. Supports `--author=<name>`, `--handoff-to=<name>`, and `--solo` flags to skip the prompts. Step 5c keeps each writable GitHub repo's README.md current against the canonical 16-section structure. The companion `/session-start` skill reads the handoff file to brief next-session Claude.
---

# Session End

Wrap a Cowork session by extracting what was done plus what's queued for next time, and persisting it to a canonical-named handoff document. The companion `/session-start` skill reads that exact file to brief next-session Claude in one step.

## When to use

Trigger when the user is wrapping a Cowork session and wants the work persisted in a way the next session can pick up. Common triggers:

- `/session-end [project-name]`
- `/session-end [project-name] --author=<name>` *(skip the author prompt)*
- `/session-end [project-name] --handoff-to=<name>` *(skip the baton-pass prompt; implies an active handoff)*
- `/session-end [project-name] --solo` *(skip the baton-pass prompt; writes no `for:` field)*
- `/session-end [project-name] --archive` *(also write a dated archive copy)*
- "session-end" / "end session" / "wrap session"
- "save handoff" / "save the handoff for tomorrow"
- "we're done for the day"
- "sign off"
- "write the continuation prompt"

The skill assumes the project has been initialized via `/init-project` and has a saved `cowork-project-instructions.md` in its `00 – Project Hub/`. If not, route the user to `/init-project` first.

## Standard handoff filename

The canonical path is **`[project]/00 – Project Hub/cowork-session-handoff.md`**. Single file. Overwritten each session-end. Drive versioning preserves history.

This filename is **fixed**. `/session-start` reads exactly this path. Don't add date suffixes, don't write to a different location, don't split into multiple files. Free-form continuation prompts can still live in `06 – Engineering/` or wherever for project-specific use, but the canonical handoff is at this fixed path.

If the user wants an explicit dated archive in addition to the canonical file, the `--archive` flag writes a copy to `00 – Project Hub/Session Handoffs/handoff-YYYY-MM-DD-HHMM.md`. The canonical file is still written; the archive is an additional copy.

## Steps

### Step 1: Resolve which project

If the user passed a project name with the slash command (e.g. `/session-end Nexus`), use it directly. Otherwise, in order:

a. Check the currently-mounted folders. If exactly one Taskade subfolder is mounted (e.g. `Taskade/Nexus`), assume that's the project. Confirm via a single AskUserQuestion before proceeding.

b. If none is obviously mounted, scan `Taskade/` and `MoxyWolf Vault/Projects/` for subfolders that contain `00 – Project Hub/cowork-project-instructions.md`. Sort by recency of modification of the saved instructions file. Present the top ~6 candidates via AskUserQuestion.

c. If the user passes a name that doesn't match any folder, list available project folders and ask them to pick (don't create new ones — that's `/init-project`'s job).

### Step 2: Read the saved Project Instructions (for context)

Read `Taskade/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` (or `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` for vault-only projects).

This gives you:

- The active Taskade subfolder name
- The list of active GitHub repo(s)
- Any project-specific overrides

You'll cite specific repo names in the handoff's "Uncommitted code" section so next-session Claude knows where to look.

### Step 3: Scan the session for extractable handoff content

Review the full Cowork conversation. Identify items in each of the canonical handoff sections:

#### a. What landed this session

One short paragraph (3–6 sentences) summarizing what shipped, what state changed in production data, and what production rows / counts moved. Concrete numbers where possible. No lists in this section — it's the elevator-pitch context.

Examples:
- "Multi-axis classifier shipped end-to-end. 3,233/3,323 nouns now carry real entity_type values. Browse pages render the live distribution. PostgREST 1000-row cap workaround landed."
- "Wrote the Strike Graph reseller v4 contract. Added MSA addendum for the 70/30 split. Filed both in 01 – Admin & Legal."

#### b. Open work, in priority order

A numbered list. Each item gets:

- Title
- 1–3 sentence description of what it is and why it's queued
- The exact commands (if applicable) to run, in fenced code blocks
- Any inspection criteria for "done"

Items should be ordered by what next-session Claude should do **first**. Push uncommitted code typically goes first because most other work depends on it.

#### c. Uncommitted code

For every set of changes sitting in a working tree without a commit, write a full commit block: file list, summary line (under ~72 chars, imperative mood), description body in fenced code blocks. The point is that next-session Claude can paste these directly into GitHub Desktop without re-deriving them.

Per the operating norm `norm-commit-messages-always-supplied-2026-05-08.md`: every commit prompt must include both summary and description ready to paste.

If there's no uncommitted code, write `_(none — working tree clean as of session end)_` and skip the section.

#### d. Procedural reminders for next-Claude

A bulleted list of cross-session memory references and project-specific gotchas. Pull from:

- The Cowork session-memory layer (`feedback_*` and `reference_*` memories that apply)
- The vault's Operating Norms folder
- This-session-specific traps: "FileMaker import is dead — don't propose running it" / "Sandbox can't run tsx — execute on Mac" / etc.

Don't repeat universal rules (the `cowork-project-instructions.md` covers those). Capture the project-specific gotchas next-session Claude wouldn't otherwise know.

#### e. Suggested opening line

A short quoted paragraph the user can paste into a fresh Cowork chat as the first message. Should orient next-session Claude in 1–3 sentences: what state we're in, what to do first.

**Always end this paragraph with a final sentence pointing to the full handoff file's path**, so next-Cowork knows where to read the full detail rather than working from the opening-line alone. Use the path relative to the mounted Cowork roots:

- Taskade-based project: `Taskade/[PROJECT_NAME]/00 – Project Hub/cowork-session-handoff.md`
- Vault-only project: `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-session-handoff.md`

The pointer sentence should be formatted exactly as: *"The full handoff is at `Taskade/[PROJECT_NAME]/00 – Project Hub/cowork-session-handoff.md`."* (backticks around the path). This wording is what `/session-start` looks for — keep it predictable.

Example: *"Picking up after the multi-axis classifier landed. Two commits to push (Bloom's importer + term-def backfill), then run the term-def backfill, then we can spec variant morphology. The full handoff is at `Taskade/Nexus/00 – Project Hub/cowork-session-handoff.md`."*

### Step 3.5: Capture the handoff author and (optional) baton-pass target

Every handoff carries an `author` field, and any explicit baton-pass to a teammate is captured as a `for` field. These were previously hand-added to the frontmatter; this step auto-writes them.

Ask both questions in a **single `AskUserQuestion` call** so the user only sees one prompt. Don't ask if the answers are already supplied via flags (see "Flag overrides" below).

Question 1 — **"Who authored this handoff?"** (header: "Author")
Options, in this order:
- `Dorian`
- `Michael`
- `Phil`
- `Steven`

Question 2 — **"Is this a baton-pass to a teammate, or are you just stopping for the day?"** (header: "Handoff target")
Options, in this order:
- `Just stopping for the day` *(default — writes no `for` field)*
- `Dorian`
- `Michael`
- `Phil`
- `Steven`

Normalize both answers to lowercase first names (`dorian`, `michael`, `phil`, `steven`). Store them as `AUTHOR` and `FOR`. If the user answered "Just stopping for the day" to Question 2, leave `FOR` unset — the `for:` key is omitted entirely from the frontmatter in that case (it is NOT written as `for: null` or `for: ""`).

If the user picks the same person for both Question 1 and Question 2, treat that as "just stopping for the day" — you don't baton-pass to yourself. Drop the `FOR` value silently; no need to re-prompt.

#### Flag overrides

The slash command accepts three optional flags that skip the prompt:

- `--author=<name>` — sets the author without asking. Example: `/session-end Nexus --author=michael`.
- `--handoff-to=<name>` — sets the baton-pass target without asking. Example: `/session-end Nexus --handoff-to=phil`. Implies an active baton-pass.
- `--solo` — explicitly marks a non-handoff session. Skips Question 2 (writes no `for` field) but still asks Question 1 unless `--author` is also passed.

Combining flags is fine: `/session-end Nexus --author=dorian --handoff-to=michael` skips both prompts. If a flag value isn't one of the four known names, fall back to asking the corresponding question rather than writing a bad value.

#### When to remind the user to ping Slack

If `FOR` is set (a baton-pass happened), include a one-line reminder in the Step 8 final report: *"Baton passed to **[FOR]** — ping them in Slack so they know to pick this up."* Per the marketplace README's handoff protocol, the Slack ping is required when explicitly handing off; if you're just stopping for the day, no ping needed.

### Step 4: Compose the handoff document

Use this exact structure. The frontmatter format is fixed so `/session-start` can parse it.

```markdown
---
title: "Session Handoff — [Project Name]"
date: YYYY-MM-DD
session_ended: YYYY-MM-DDTHH:MM:SS-08:00
project: [Project Name]
type: session-handoff
status: active
author: [AUTHOR from Step 3.5]
for: [FOR from Step 3.5]   # OMIT THIS LINE ENTIRELY if FOR is unset
---

# Session Handoff — [Project Name]

**Session ended:** YYYY-MM-DD HH:MM PT
**Author:** [AUTHOR, title-cased]   [— **baton-passed to [FOR, title-cased]**]   (drop the "— baton-passed…" suffix if no FOR)

## What landed this session

[paragraph]

## Open work, in priority order

### 1. [Task title]

[description + commands]

### 2. [Task title]

[description + commands]

[...]

## Uncommitted code

### Commit A — [short title]

Files:

- `path/to/file1.ext`
- `path/to/file2.ext`

**Summary:**
\`\`\`
[commit summary line]
\`\`\`

**Description:**
\`\`\`
[commit description body]
\`\`\`

[repeat per commit, or write _(none — working tree clean as of session end)_]

## Procedural reminders for next-Claude

- **[Reminder title]:** [body]. (Memory: `feedback_xxx`. Operating Norm: `path/to/norm.md`.)
- ...

## Suggested opening line

> *"[one- to three-sentence orientation paragraph]. The full handoff is at `Taskade/[PROJECT_NAME]/00 – Project Hub/cowork-session-handoff.md`."*
```

(For vault-only projects, substitute `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-session-handoff.md` for the path.)

### Step 5: Write the handoff file

Use the `Write` tool to write the composed document to:

```
[project's Taskade subfolder]/00 – Project Hub/cowork-session-handoff.md
```

For vault-only projects: `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-session-handoff.md`.

Always overwrite. Drive versioning preserves the previous version. Don't ask the user to confirm overwrite — the canonical file is meant to be replaced each session.

### Step 5b: (Optional) Write the dated archive copy

If the user passed `--archive` (e.g. `/session-end Nexus --archive`), also write a copy to:

```
[project's Taskade subfolder]/00 – Project Hub/Session Handoffs/handoff-YYYY-MM-DD-HHMM.md
```

Create the `Session Handoffs/` subfolder if it doesn't exist. Use the user's local time for the filename timestamp.

The archive copy has identical content to the canonical file; it's just a dated record for cases where Drive versioning isn't trusted.

### Step 5c: Update each writable GitHub repo's README.md if warranted

For every GitHub repo flagged **READ/WRITE** in the project's saved `cowork-project-instructions.md`, keep that repo's `README.md` as a living document. The point: never have to remember to update a repo's GitHub landing page by hand. Each session-end pass scans for changes that should propagate to README, drafts the edits, writes the file, and surfaces the change as a separate commit block in the handoff.

Read-only repos are skipped entirely, even if the session referenced their code.

#### Trigger criteria

Propose a README diff when the session touched any of:

- **package.json scripts** — new `npm run …` commands, renamed scripts, removed scripts
- **Schema migrations** — new files under `supabase/migrations/`, `prisma/migrations/`, or equivalent; new/dropped tables, columns, enums
- **Environment variables** — new keys in `.env.*.example`, new required env in code, renamed env vars
- **Dependencies** — new top-level `dependencies` / `devDependencies` (lockfile-only changes don't count); new internal workspace packages
- **Version bumps** — `package.json` `version` field changed, or a workspace package's version changed
- **Key features** — a feature shipped this session that materially changes what the repo does (new pipeline, new classifier axis, new route family, new auth posture)
- **Routes** — net-new `app/**/page.tsx` (or framework equivalent), or removed routes
- **Architecture shifts** — engine extraction, adapter rewrite, store-contract changes, deployment-target changes

If the session is purely bug fixes, test additions, comment edits, or no-op cleanups, **skip** Step 5c. Don't fabricate a README diff to fill space.

#### Canonical README structure

When updating (or initializing) a repo's README, it must carry these 16 sections in this order. The structure is canonical; the content within each section is repo-specific.

1. **Header + badges + one-liner** — repo name, short subtitle, status/version/framework badges, one-sentence description of what the repo is.
2. **Table of contents** — anchor links to every following section.
3. **Environments** — table of environments the repo supports (local dev, rehearsal, staging, production Vercel/AWS if applicable). Include how to point at each (env file, project ref, etc.).
4. **Quick Start** — prereqs table (tools + versions), commands reference table (every `npm run` / `make` target), local-dev runbook.
5. **Architecture** — Mermaid diagram showing the high-level system (e.g. Next.js App Router → Supabase → engine package). State whether the system is internal-only or a public API. Include a sequence diagram for any non-obvious flow (import, classify, deploy, etc.).
6. **Database Schema** — table of core tables with one-line purpose each, plus a Mermaid ERD covering the main relationships. For workbench/UI repos that don't own the schema, point at the source-of-truth project and note the type-regeneration command.
7. **Data Initialization** — every importer / seed / backfill script the repo ships. Mark dry-run posture per script. Where data comes from.
8. **Key Features** — bulleted list of what the repo actually does. Lead with the load-bearing ones. Reference concrete production state where possible (row counts, latest milestones).
9. **API / Server Actions** — table of routes, server actions, or endpoints. If the repo is a UI workbench reading directly from Supabase / a backing store with no API surface, **say so explicitly** in this section (don't omit it).
10. **Common Workflows** — common operator tasks step-by-step: re-running a classifier, paging through records, regenerating types, etc. Curl examples for APIs; npm-script invocations for tools.
11. **Troubleshooting** — table mapping symptom → cause/fix. Always include known operational gotchas: PostgREST 1000-row cap (if Supabase), Cowork sandbox unlink limitation (if applicable), GitHub Desktop push reminder (for any repo Dorian pushes manually), env-var missing errors.
12. **Security** — RLS posture for the database, service-role-key vs anon-key separation, secret hygiene rules, any auth flow. Use a small table for control + status + implementation.
13. **Technology Stack** — table of category → technology → version. Pin to **TECH-STACK-V4.3** as the canonical reference; only deviate when the repo legitimately uses something newer/older and explain why.
14. **Project Structure** — `text`-fenced tree of top-level directories with one-line purpose each. Don't enumerate every file — show the shape.
15. **Deployment** — current deployment state (local-only, Vercel preview, AWS prod, etc.), env-var configuration, rollback path. If not yet deployed, say so honestly and describe the planned target.
16. **License** — license name and pointer to the LICENSE file. If license is TBD, say so.

Optional 17th section if the repo has unusual contributor conventions: **Contributing & Commit Workflow** (direct-to-main vs PRs, push step, commit-message rules, npm-scope rules).

#### How to update

1. **Read the current `README.md`** in the writable repo.
2. **Identify the exact sections that need updating.** Resist rewriting untouched sections.
3. **Apply minimal edits via the Edit tool.** Preserve voice, structure, section ordering, badge style, and table conventions already in place.
4. **Cascade derived sections.** If a new script lands in the Commands Reference table, check Data Initialization, Common Workflows, Project Structure, and Key Features for cascade edits. If a migration lands, refresh the Database Schema migrations list and the ERD if a table was added/dropped.
5. **Bump version badges** if a real version bump landed.
6. **Don't commit.** Just write the README file. The commit lands via GitHub Desktop next session.

#### Surface the README change in the handoff

In the handoff's `## Uncommitted code` section, add a **separate commit block** for the README change. Per operating norm `feedback_commit_messages_always`, every commit prompt includes both summary and description in fenced code blocks. Example:

````markdown
### Commit B — Update README for v0.2 dedup migration

Files:

- `README.md`

**Summary:**
```
docs: surface dedup migration + dedup:nouns scripts in README
```

**Description:**
```
- Add migration 20260511180000_lexicon_noun_lemma_key_unique.sql to the
  migrations table
- Add lexicon_dedup_review_queue to Database Schema
- Add migrate-noun-dedup.ts to Data Initialization with dry-run and
  production npm scripts
- Note the partial-unique index posture on lexicon_nouns.lemma_key
```
````

Order the README commit **after** the substantive code commits (the README documents the code, so code lands first).

#### Initializing a README for a repo that doesn't have one yet

If a writable repo has no README (or just a create-next-app boilerplate), and the session involved substantive changes, treat that as a signal to author a fresh README using the 16-section canonical structure. Don't fabricate content — pull from the repo's actual code, package.json, schema, env files, and the project's cowork-project-instructions.md. If the session didn't produce enough material to fill the structure responsibly, flag "Author initial README" as a follow-up task in the handoff's Open work section and continue.

#### Edge cases

- **Multiple writable repos changed this session.** Update each one independently. Each gets its own commit block in the handoff's "Uncommitted code" section.
- **README diff would be huge.** If the README needs a substantial restructure (not just additive edits), don't try to do it inside session-end. Flag it as a follow-up task in the handoff and let the next session schedule a dedicated rewrite.
- **Session changed code that no README section covers.** That's a signal of a README gap. Add a short new section if the change is small; otherwise flag the gap as follow-up work.
- **Project has no writable GitHub repos listed.** Skip Step 5c entirely. Don't ask the user to point at a repo — the project instructions are the source of truth.

### Step 6: Update Cowork session-memory (if warranted)

If the session produced significant new context that future Claude sessions should know without reading the handoff (operating norms, durable architecture decisions, gotchas that apply across all projects), update the Cowork session-memory layer:

- New `feedback_*.md` for behavioral rules surfaced this session
- New `project_*.md` for project-state changes
- New `reference_*.md` for durable references
- Update `MEMORY.md` index

This step is optional — only do it if the handoff alone won't carry the weight. Most session-end runs don't need a memory update.

### Step 7: Run `/obsidian-update` to persist cross-project knowledge to the vault

After the handoff is written, **always invoke the `/obsidian-update:obsidian-update` skill** to capture the session's durable knowledge into the MoxyWolf Obsidian vault.

Invocation: call the `Skill` tool with `skill: "obsidian-update:obsidian-update"`. The skill scans the current conversation for decisions made, research findings, meeting discussions, cross-project insights, action items, and new contacts, then writes properly formatted, cross-linked Markdown notes into the vault.

This is the layer above the project-scoped handoff:

- **Handoff (Step 5)** is project-scoped — lives in the project's `00 – Project Hub/` and tells next-session Claude how to resume *this* project specifically.
- **Cowork session-memory (Step 6)** is Claude-scoped — lives in Claude's own memory system and applies across all future Cowork sessions.
- **Obsidian vault (Step 7)** is organization-scoped — lives in `MoxyWolf Vault/_Shared Knowledge/`, daily notes, project notes, and people notes. Surfaces cross-project patterns and durable institutional knowledge that `/session-start` won't necessarily look at but humans and search will.

All three layers run together at session-end so the wrap-up is one command, not three.

If `/obsidian-update` finds nothing extractable (quick clarification session, casual chat), it will say so honestly and produce no notes — that's fine. Pass it through; don't suppress.

If the `obsidian-update` skill is unavailable in this Cowork install (rare — both plugins ship in the MoxyWolf marketplace), log a one-line warning in the final report and continue. Don't abort the session-end wrap-up because the vault update step is unavailable.

### Step 8: Report what was written

Output a short summary in chat:

```
## Session handoff saved

✅ [project]/00 – Project Hub/cowork-session-handoff.md

Author: [AUTHOR, title-cased]   [→ baton-passed to [FOR, title-cased]]

Top of stack for next session:
1. [first open-work item title]
2. [second open-work item title]
3. [third open-work item title, if applicable]

[N] uncommitted commits drafted in the handoff.
[N] procedural reminders captured.

[If FOR is set (baton-pass):]
🪝 **Ping [FOR, title-cased] in Slack** so they know to pick this up.

[If Step 5c wrote README updates:]
README updates written:
- [repo-name]/README.md — [one-line summary of what changed]
(Commits drafted in the handoff; push via GitHub Desktop next session.)

[If --archive was used:]
Archive: [project]/00 – Project Hub/Session Handoffs/handoff-YYYY-MM-DD-HHMM.md

## Vault updated via /obsidian-update

[Summary that /obsidian-update returned: N decision notes, N research notes, N daily-journal entries, N people notes, etc. — or "nothing extractable" if that's what came back.]

Run `/session-start [project]` next time to pick up.
```

Keep it factual. Dorian can open the file in Obsidian to review the full handoff if he wants the detail.

## Edge cases

- **No saved Project Instructions for this project.** Stop and route to `/init-project` first. Don't write a handoff for a project that doesn't have a config.
- **Existing `cowork-session-handoff.md` from a previous session.** Overwrite. Drive versioning preserves the prior version. The canonical file is meant to reflect "the most recent handoff," not an append-only log.
- **Session had no extractable handoff content.** This happens — quick clarifications, casual chat, no work shipped. Say so honestly: "This session didn't produce work that needs a handoff. Nothing to write." Don't manufacture content.
- **Conversation referenced multiple projects.** Pick the dominant one and write the handoff there. If genuinely cross-project (rare), ask the user which project's handoff this should be. Don't write multiple handoffs from one session-end run.
- **Mounting issues — project's Taskade subfolder isn't currently mounted.** Use `mcp__cowork__request_cowork_directory` with the explicit path to mount it, then write.
- **User pasted an `/obsidian-update` mid-session, then runs `/session-end`.** Fine. `/session-end` invokes `/obsidian-update` again at Step 7. The second run is idempotent on already-captured content — it'll find less to extract since the mid-session run already wrote the bulk of it. No deduplication needed; obsidian-update handles "I've already seen this" itself.
- **`/obsidian-update` skill unavailable in this Cowork install.** Skip Step 7 with a one-line warning in the final report ("Vault update skipped: obsidian-update skill not available"). Don't abort — the handoff (Step 5) is the load-bearing artifact.
- **No writable GitHub repos listed in project instructions.** Skip Step 5c entirely — don't ask the user to nominate a repo. Project instructions are the source of truth for repo posture.
- **Writable repo's README would need from-scratch authoring.** Step 5c can initialize a README using the canonical 16-section structure if the session produced substantive material. If the session didn't, flag "Author initial README" as Open work and continue.
- **User declined or canceled the Step 3.5 prompt.** Default to `author: dorian` and no `for:` field. Mention the fallback in the Step 8 report (*"Author defaulted to Dorian — pass `--author=<name>` next time to override."*) so the user knows it happened. Don't block the handoff write on a missing answer; the handoff itself is the load-bearing artifact.
- **Flag value isn't one of the four known names** (e.g. `--author=mike` or `--handoff-to=phillip`). Fall back to asking the corresponding question. Don't silently rewrite the value — the four canonical lowercase names (`dorian`, `michael`, `phil`, `steven`) are the only acceptable values, so the user needs to confirm.
- **Author and baton-pass target are the same person.** Treat as "just stopping for the day"; drop the `FOR` and omit the `for:` field. Don't re-prompt.

## Why this filename, why this shape

- **Canonical filename `cowork-session-handoff.md`** — `/session-start` reads exactly this path. If we let session-end pick filenames freely, session-start can't find the handoff reliably. One canonical file, always at the same path, is the contract between the two skills.
- **`00 – Project Hub/`** — the same folder that holds `cowork-project-instructions.md` (the stable project config). Handoffs sit next to instructions; both are project-level metadata.
- **Standard sections in the handoff** — `/session-start` parses this structure to surface "Open work" and "Suggested opening line" in its briefing. Deviating from the section names breaks that parse.
- **Drive versioning as audit trail** — Google Drive auto-versions every save. The previous handoff is one click away in Drive's version history. Explicit dated archives (`--archive`) are available when you want a dated file in the filesystem; they're not the default.

## Notes

- This skill complements `/session-start` (read the handoff next time) and bundles `/obsidian-update` (extract durable knowledge to the vault) as a final step. One wrap-up command writes the project-scoped handoff AND captures cross-project knowledge in the vault — no need to remember to run two commands.
- The handoff is intentionally project-scoped. Cross-project knowledge belongs in the vault via `/obsidian-update`, which now runs automatically at Step 7.
- The skill writes but does not commit. Code commits are still Dorian-via-GitHub-Desktop; the handoff just makes sure the commit messages and the "what to commit" are drafted and ready to paste.
- Step ordering matters: handoff (Step 5) before Cowork session-memory (Step 6) before vault update (Step 7). The handoff is the load-bearing artifact for tomorrow; memory is Claude's own context; the vault is the long-term institutional record. If anything fails, the earlier steps stand on their own.
