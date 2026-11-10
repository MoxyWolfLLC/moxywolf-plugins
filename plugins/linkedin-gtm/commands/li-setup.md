---
description: Set up or change the linkedin-gtm config (account sid, Release Owner, lanes and the Lane A hold, approval time, meeting handling, CRM target, suppression file, ledger and gate-log paths).
argument-hint: "[field to change]"
allowed-tools: [Read, Write, Edit, Bash]
---

# /linkedin-gtm:li-setup

Writes `${LINKEDIN_GTM_CONFIG:-$HOME/.config/linkedin-gtm/linkedin-gtm.json}` starting from `${CLAUDE_PLUGIN_ROOT}/config/linkedin-gtm.example.json`. Side effect: a local config file only.

Walk through, one question at a time, showing the current value:

1. **Connection**: OAuth or API key (`references/connection.md`). Never ask for the key in chat; tell the operator where to put it.
2. **Account**: list accounts with `gtm_mcp.py read search_linkedin_accounts --args '{}'` and confirm the `account_sid` (default `ln_ac_0voWEjtk3uzK`, Dorian Cougias, Premium, no Sales Navigator).
3. **Release Owner**: a named person (default Dorian Cougias). Not a team, not the operator.
4. **Lanes**: keywords per lane. **Lane A mode**: `engagement-only` (default) or `full-outreach`. Only Dorian changes this; confirm it's him.
5. **Approval time** (default 10:15 America/Los_Angeles) and publish days (default Tue, Thu).
6. **Meetings**: `hand-to-dorian` (default) or `booking-link` with the link.
7. **CRM target**: `moxywolf-crm` only (default), or also Attio or Clarify. Extra targets stay empty until Dorian decides.
8. **Paths**: suppression file, ledger directory, gate-log directory (`GitHub/Projects/_gate-log`).
9. **Ramp start date** (default the day the account was connected).

Validate the JSON, show a diff of what changed, and write it. A change to `release_owner` or `lanes.A.mode` is reported to Dorian and logged with `record_decision.py` like any other high-stakes decision. Then run `/li-health` once to confirm the connection works.
