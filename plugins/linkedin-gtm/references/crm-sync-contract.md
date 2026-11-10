# CRM sync contract

The MoxyWolf CRM is the system of record for people, organizations, stages and suppression. LinkedIn must not become a second, unmanaged pipeline. This file says what this plugin hands the CRM, and what it reads from it.

## The integration point

This plugin does not write to any CRM API. It produces touch records; the MoxyWolf CRM's own integration (or a person) loads them. Until that integration is named in the config, the records are a file:

```
python3 "$P/scripts/batch_ledger.py" crm-export --ledger "$L" > crm-touches-2026-11-10.jsonl
```

`crm_target` in the config is `moxywolf-crm` by default. Adding Attio or Clarify (`crm_extra_targets`) is one of Dorian's open decisions; until he makes it, nothing goes to them, and no skill writes to a CRM it found connected in the session. A CRM write is a write to a customer system, which is high-stakes under the charter: if a skill ever loads the records itself, each load is a gated action with its own approval.

## Touch record (one JSON object per line)

| Field | Meaning |
|---|---|
| `source` | always `linkedin-gtm` |
| `touch_id` | `li-<item id>`, stable, safe to load twice |
| `occurred_at` | when the action ran (UTC ISO-8601) |
| `channel` | `linkedin` |
| `touch_type` | reaction, comment, repost, post, connect, dm, reply, accept, ignore, withdraw, mark_unread, visit, endorse |
| `lane` | A, B, C, D or OWN |
| `person` | `name`, `identifier` (LinkedIn public identifier), `url`, `company` |
| `sequence` | `{name, step}` when the touch is a sequence step |
| `text` | the exact text sent (comment, DM, note) |
| `linkedin_ref` | URNs or sids the API returned |
| `approved_by` | the Release Owner who approved it |
| `send_status` | `sent`, or `uncertain` (checked with `check_linkedin_*_sent` before anyone acts on it) |

Only executed and uncertain items are exported. Drafts, struck items and stopped items aren't touches.

## Events the CRM also needs (from inbox triage)

li-inbox-triage writes these as a second JSONL file, same `source` and `person` shape, with `event` set to one of:

| Event | When | CRM effect |
|---|---|---|
| `reply` | a person replied | log the reply, stop their sequence |
| `meeting_requested` | they asked to meet | hand to Dorian; stage change only after he books it |
| `referral` | they pointed to someone else | log both people |
| `not_now` | interested later | set `nurture_on` (a date) |
| `stop` | no, stop, not interested | suppress (and add to the suppression file the same day) |
| `accepted` | a connection request was accepted | start the on_accept step |

## What the plugin reads from the CRM

Before adding an outreach item (connect, dm), the drafter checks:

- Is the person suppressed or marked "no"?
- Are they in an active email sequence for the same campaign?
- Are they a customer with an account owner?
- Did someone already reach out in the last 30 days?

If the CRM can't be read in this session, export the suppression list to the `suppression_file` and say in the batch that the CRM check was file-only. Don't skip the check silently.

## Dedupe key

LinkedIn public identifier (`linkedin.com/in/<identifier>`), lowercased. The profile URL normalizes to it. When only a member id (`ln_id`) is known, carry it in `person` and let the CRM match.
