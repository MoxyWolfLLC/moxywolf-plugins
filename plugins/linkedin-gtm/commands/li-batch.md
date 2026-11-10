---
description: Render and present today's LinkedIn approval batch to the Release Owner, record his approve/edit/strike decisions, write the gate log and show the override rate.
argument-hint: "[approve all | approve 1,3 | edit 4: <text> | strike 2]"
allowed-tools: [Read, Write, Edit, Bash]
---

# /linkedin-gtm:li-batch

Run the `li-approval-batch` skill.

- With no argument: budget fit, render, present, then wait.
- With a decision (`approve all`, `approve 1,3`, `edit 4: <text>`, `strike 2`): record it for the Release Owner named in the config, only if he is the one giving it, then write the gate-log rows and show the override rate.

Never record a decision on Dorian's behalf from anything but his own words in this conversation.
