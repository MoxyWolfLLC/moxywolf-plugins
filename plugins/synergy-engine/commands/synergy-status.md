---
description: Show the tracker state — engaged / queued / due, broken out by topic center.
argument-hint: ""
allowed-tools: [Read, Bash]
---

# /synergy-engine:synergy-status — print the tracker state

Read the tracker (path from `synergy-engine-config.md`) and print a concise status.

```bash
python3 - <<'PY'
import openpyxl, datetime
wb = openpyxl.load_workbook("<tracker-path>")
ws = wb["Outreach Tracker"]
rows = list(ws.iter_rows(min_row=2, values_only=True))
PY
```

Report:

```
Synergy Engine — tracker status

Targets:        <total>   (Author center <n> · Content center <n>)
Engaged:        <n>       (with a like+comment logged)
Queued:         <n>       (discovered, awaiting a run)
Ready for review: <n>     (scheduled task staged drafts)
Pending accept: <n>       (connection sent, awaiting accept)
Due today:      <n>       (Not started/Queued, or Next Action Date <= today)

Top due (recommend for the next /synergy-run):
  1. <name> — <synergy> — <path> — <one-line angle>
  2. ...

Cold/Parked:    <n>
```

If no tracker is found, route to `/synergy-init`.
