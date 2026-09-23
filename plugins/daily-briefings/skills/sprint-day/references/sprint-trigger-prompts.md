# Sprint trigger prompts

The exact bodies registered as scheduled tasks. Used verbatim. They are thin on purpose: the skill owns the steps, and a second copy of those steps inside a prompt drifts from the skill on the first edit.

`{{...}}` placeholders are filled at registration time from the config and the ledger. Nothing else in these prompts is variable.

---

## 1. Plan: recurring, registered by `/briefings-setup`

Normally not registered on its own. The planner runs at the end of the existing 07:00 commitment-calendar task, reusing the commitments that run already resolved. Register this only if the calendar task is not running.

```
Run the `/sprint-day` skill from the `daily-briefings` plugin in `plan` mode, following it exactly. Read the owner config at `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/briefings.config.json`.

Unattended scheduled run: work autonomously, ask no clarifying questions, offer no connector suggestions. Do not restate or re-derive the skill's steps; the skill owns them.

RUN CONTEXT: this fires at {{planTime}} {{timezone}} on a weekday morning. Anchor the day on today in {{timezone}}, not on the sandbox's UTC date.

CONFIG LOCATION: the vault is not mountable from a scheduled cloud run. The same `briefings.config.json` exists in the owner's Google Drive; find it with `mcp__Google_Drive__search_files` on `title contains 'briefings.config'` and read it with `read_file_content`. Parse it in full. If the Drive copy is also unreadable, stop and say so; do not plan a day against a guessed curve.

The curve, the frog window and the ledger directory all come from the `ultradian` block in that config. Do not state any of them here.
```

## 2. Check: one-shot, registered by `plan`, one per block with a commitment

```
Run the `/sprint-day` skill from the `daily-briefings` plugin in `check` mode for block {{blockId}}, following it exactly.

Unattended scheduled run: work autonomously, ask no clarifying questions. Do not restate the skill's steps.

BLOCK: {{blockId}}, {{start}} to {{end}} {{timezone}}, on the ledger for {{date}}. Resolve the block by its start time, not by its position in the array.

LEDGER: `{{ledgerDirectory}}/{{date}}.json`, read through Google Drive (`mcp__Google_Drive__search_files` on the filename, then `read_file_content`). If it is missing or unparseable, stop and report that. Do not reconstruct the day.

EVIDENCE: query only the surfaces this block's `evidence.expect` names. Nothing wider. An artifact only counts when its own timestamp falls inside {{start}} to {{end}}. Write what you saw into `verifiedBy` as {surface, id, at, detail}, never as a boolean.

REPORT: one line. If the block is not `verified`, end with the single question the artifacts could not answer.
```

## 3. Close: one-shot, registered by `plan`, one per day

```
Run the `/sprint-day` skill from the `daily-briefings` plugin in `close` mode, following it exactly.

Unattended scheduled run: work autonomously, ask no clarifying questions. Do not restate the skill's steps.

LEDGER: `{{ledgerDirectory}}/{{date}}.json`, read through Google Drive. If it is missing or unparseable, stop and report that.

DELIVERY: email the summary to {{ownerEmail}} with `mcp__Gmail__send_message`, email-safe: inline `style` attributes on every element, literal hex colours, tables for layout, borders instead of shadows, max-width around 900px. Gmail strips CSS custom properties and box-shadow. One email, never split.

Subject: `Sprint day {{date}}: {{verified}} of {{planned}} verified`.

Carry all of it: the four counts, each block with its status, the artifact behind every `verified` block, the open question on every block that is not, the curve source and its date, and every evidence source that came back `unavailable` or `not checked`. A summary that drops its caveats is the failure `source-discipline.md` exists to prevent.

Then append the rollup row and say in one clause whether the email sent.
```

---

## Registration notes

- Use `mcp__claude-code-remote__create_trigger`, never `CronCreate`. The local cron tools run inside a session and are lost when it ends, so anything scheduled with them silently never fires.
- Check-ins and the close task are `run_once_at`, never cron. They fire today and disable themselves.
- `permission_mode` is the owner's decision and is made once, in `/briefings-setup`. A task left at default stops on the first action needing approval, which in an unattended run means it stops for good.
- Every registered id goes into the ledger. An id this skill did not write is never deleted by it.
