---
description: One-time setup. Five short questions — folder pick, folder pick, your name, a hero image vibe, optional live URL. Everything else is auto-detected.
argument-hint: (no arguments — runs interactively)
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob, Grep, mcp__cowork__request_cowork_directory]
---

# /4d-blog-engine:blog-init — one-time setup

Built for writers, not developers. The plugin assumes Payload CMS as the backend, but it figures out everything technical on its own by reading your `payload.config.*` and `.env.local`. You answer five short questions:

1. **Pick your blog project folder** via the OS folder picker. This is the workshop where the plugin keeps drafts and working files.
2. **Pick the GitHub repo for your blog** via the OS folder picker. The plugin checks that it's a Payload project and detects your collections in the background.
3. **Your name** for the post byline.
4. **A hero image vibe** — neutral, warm, bold, or dark. Each one has a fixed palette baked in.
5. **Live site URL pattern, optional** — used to preview the live link after publishing. Skip if you don't have one yet.

That's it. The plugin auto-detects which Payload collection to publish into, which collection holds media, your Payload API base URL, and whether you have an API key configured. If any of those are wrong, you can edit them later in `blog-project-instructions.md` — but you don't need to touch them at setup time.

Read `skills/blog-init/SKILL.md` for the full workflow.
