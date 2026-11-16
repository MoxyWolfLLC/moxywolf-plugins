# The CRM sync health scheduled prompt

This is the canonical text of the `CRM sync health` scheduled task's prompt (EV-015). `/briefings-setup` registers it word for word. It carries no checks and no repairs: those live only in `skills/crm-sync-health/SKILL.md`, so a scheduled run can never follow a stale copy of them. A task registered before daily-briefings 0.3.2 carries its own copy; replace its prompt with the text below.

> Run the `/crm-sync-health` skill from the `daily-briefings` plugin and follow it end to end. This is an unattended scheduled run: work autonomously and do not ask clarifying questions. The skill must be daily-briefings 0.3.2 or later, which you can tell because its Step 2 runs six checks and names check 6 (derive jobs). If the skill is not installed, or its Step 2 has no check 6, reply with exactly `CRM health check unavailable: daily-briefings 0.3.2+ not installed` and run no checks and no repairs.
