---
description: Execute ONLY the approved items in today's LinkedIn batch, one at a time via preview then confirm; stops a bucket on any limit and everything on a checkpoint. High-stakes.
argument-hint: "[--block engagement|network|inbox] [--item ID]"
allowed-tools: [Read, Write, Bash]
---

# /linkedin-gtm:li-execute

Run the `li-execute` skill for the given block (default: the block whose window is open) or a single item. Every call goes through `gtm_mcp.py execute`; the client refuses anything without the Release Owner's recorded decision for today. Report outcomes per item and any stops.
