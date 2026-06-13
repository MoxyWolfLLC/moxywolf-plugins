# Clarify objects, tools, and activity model

How the `crm-maintenance` skill reads from and writes to Clarify. Clarify's MCP exposes a small, stable tool set over a workspace-configurable schema — so this skill **reads the live schema first** rather than hard-coding field names.

## Golden rule — call `get-schema` before writing

Clarify workspaces have built-in objects (companies, people, deals, meetings, tasks) plus custom fields and custom objects the owner may have added. Field names are not universal. **Always call `get-schema` for the entity you're about to touch** and adapt to the fields that actually exist. If a field this skill wants (e.g. a "next step" or "last activity" field) isn't present, skip it gracefully — never invent or assume HubSpot-style API names.

## Tools used

| Tool | Used for |
|---|---|
| `get-schema` | Read the live entity schema before any query or write. |
| `query-data` | Search/analyze across companies, people, deals, meetings, tasks. |
| `get-records` | Full details for specific records by ID, including relationships + AI summaries. |
| `create-or-update-records` | Create or update records in bulk (people, companies, deals, meetings, tasks). |
| `merge-records` | Merge duplicate records into one primary — the dedupe primitive. Fields, relationships, list memberships, and notes are preserved. |
| `add-comment` | Attach a markdown note/summary to any record (the activity-logging mechanism). |

## People (contacts) — write

Set only what you can derive from email signatures or calendar invites. Use the workspace's actual field keys from `get-schema`; typical built-ins:

| Concept | Usage |
|---|---|
| email | Primary identifier for lookup + dedupe. Always set on creation. |
| first name / last name | Set from signature or invite if available; leave blank if unknown. |
| company (relationship) | Link to the company record from the email domain or invite organization. |

Do not write owner, lifecycle, or lead-source fields — those are owner-managed.

## People — read (for lookup)

Search by email (case-insensitive exact match) via `query-data`. Use `get-records` to pull the record ID for associating to deals/meetings, plus name/company for ambiguity resolution shown to the user.

## Deals — read (cleanup + resolution)

Via `query-data` / `get-records`: deal name (fuzzy-match against email/meeting topic), stage (read-only during cleanup — flag discrepancies, never change), amount, close date, and the deal's associated people. Use the record's AI summary and last-activity signal (from `get-records`) to detect stale deals.

## Deals — write (cleanup path only, with approval)

Propose updates and write only with explicit user approval, via `create-or-update-records`: next-step/notes field (if present in schema), close date, amount, and adding missing deal participants. **Never** change deal stage, pipeline, or owner during cleanup — owner-managed.

## Activity logging — comments, meetings, tasks

Clarify has no HubSpot-style typed "engagement" objects. Model activity natively:

| What you're logging | How |
|---|---|
| Email summary on a record | `add-comment` (markdown) on the person and/or deal. |
| A meeting that happened | `create-or-update-records` on the **meetings** object, associated to the people + deal; summarize in the body. |
| A follow-up to do | `create-or-update-records` on the **tasks** object, associated to the deal/person. |
| A flag for future review | `add-comment` on the relevant record. |

## Association rules

- Every logged activity (comment, meeting, task) associates to the deal AND at least one person.
- If a person is created on the fly during logging, associate it to the deal in the same `create-or-update-records` call so it appears on both timelines.
- Only associate a person to a deal if they're an actual participant in that email thread or meeting.

## Dedupe

Use `merge-records` to combine duplicate people or companies into a single primary — it preserves fields, relationships, list memberships, and notes. This replaces any manual field-by-field merge logic.
