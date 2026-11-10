---
description: Run the LinkedIn GTM morning (health, signals, research and drafts) and present the ONE approval batch. Stops at the gate; sends nothing.
argument-hint: "[--date YYYY-MM-DD]"
allowed-tools: [Read, Write, Edit, Bash]
---

# /linkedin-gtm:li-day

Load the `linkedin-gtm` skill, then run in order:

1. `li-health`. If RED, report the cause and stop. No batch today.
2. `li-signals`.
3. `li-research-draft`, into a new ledger for today (`batch_ledger.py new`).
4. `li-approval-batch`: budget fit, render, present.

Then stop and wait for Dorian's decisions. Do not execute anything in this command, even if he answers quickly; record his decisions with `li-approval-batch` and run `/li-execute` when the engagement window opens.
