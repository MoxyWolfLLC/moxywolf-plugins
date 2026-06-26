---
description: "Show ponytail's measured impact scoreboard (less code, cost, time)"
---

Show the ponytail gain scoreboard. One shot, change nothing: do not switch mode, write flag files, or persist anything. Render the published benchmark medians (real Claude Code agentic sessions on a FastAPI + React repo; source benchmarks/ and the README) as plain ASCII bars: Lines of code, tokens, cost, and time, each as a percent of the no-skill baseline. The bar length shows the measured figure, the label carries the exact number. These are benchmark medians, not this repo. NEVER print a per-repo savings number: the unbuilt version was never written, so there is no real baseline to subtract from in a live repo. For real per-repo figures, point to /ponytail-debt (the counted shortcut ledger) and /ponytail-audit (what is still cuttable). Report only.
