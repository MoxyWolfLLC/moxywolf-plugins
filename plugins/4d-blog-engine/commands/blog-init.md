---
description: One-time setup. Five short questions, all in plain English. No backend infrastructure questions.
argument-hint: (no arguments — runs interactively)
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob, mcp__cowork__request_cowork_directory]
---

# /4d-blog-engine:blog-init — one-time setup

Built for writers. You answer five short questions:

1. **Pick your blog project folder** via the OS folder picker — this is where drafts and working files live.
2. **Pick the GitHub repo for your blog** via the OS folder picker — this is where finished posts will eventually be published from.
3. **Your name** for post bylines.
4. **A hero image vibe** — neutral, warm, bold, or dark.
5. **Live site URL pattern, optional** — leave blank if you don't have one yet.

That's the whole form. No backend questions, no API URLs, no environment-variable questions. If your blog repo needs technical configuration to publish, the `/publish` command sorts that out at publish time — not here.

Read `skills/blog-init/SKILL.md` for the full workflow.
