# daily-ops — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

Every skill and command below declares a risk tier and is held to the five tests:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action (sending messages, creating external events, writing to shared systems).
2. **A named human signs** — high-tier output requires one *named* human to approve, and the approval is recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

## Risk surface

daily-ops is a self-directed personal-operations system. Its external side effects are: writing task state to Google Drive / the Obsidian vault (standup, triage, review — write-back after confirmation), and the fitness flow's auto-create of a Google Calendar event plus auto-send of an iMessage. The fitness calendar/message path now requires Dorian to see the workout, the recipient, and the time and approve before the calendar create and the iMessage send. Pure standup, fitness recommendations, and analysis that produce no external write are local generation.

## Skill / command risk tiers

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `daily-ops` — Mode 1 Morning Standup (read + write-back to ACTIVE TASKS after confirm) | side-effectful-gated | Reads health/calendar/email/tasks; reprioritization write-back to Drive/vault confirmed before writing. |
| `daily-ops` — Mode 2 Backlog Triage (write-back after confirm) | side-effectful-gated | Presents the full triage; writes ACTIVE TASKS back only after Dorian confirms. Dedup/ambiguity flagged, not guessed. |
| `daily-ops` — Mode 3 Weekly Review (write-back after confirm) | side-effectful-gated | Appends WEEKLY LOG + overwrites ACTIVE TASKS only after Dorian confirms. |
| `daily-ops` — Mode 4 Fitness: calendar-event create + iMessage send | side-effectful-gated (now gated) | Confirm checkpoint (Step 5.5) — show workout + recipient + time; Dorian approves before the calendar create (Step 6 / weekly Step 8) and iMessage send (Step 7). Never auto-create or auto-send. |
| `daily-ops` — Mode 4 Fitness: workout prescription, weekly/monthly progress reports, nutrition guidance | generate | Local recommendations; no external write until the gated calendar/iMessage step. |
| `/daily-ops` (command) | side-effectful-gated | Dispatches the four modes; inherits the gates above — the fitness calendar/iMessage path stays confirm-gated. |
