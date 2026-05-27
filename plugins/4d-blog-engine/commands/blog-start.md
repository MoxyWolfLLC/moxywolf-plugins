---
description: Start or resume a blog session. Mounts your blog project directory and your blog's GitHub repo, surfaces any in-progress pieces, and proposes what to do next.
argument-hint: (no arguments — auto-resolves from the current session)
allowed-tools: [Read, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:blog-start — open or resume a blog session

Invoke the `blog-start` skill. It does for the 4d-blog-engine what `/session-start` does for full MoxyWolf projects — except scoped to just two directories and just the blog work.

The skill:

1. Locates your `blog-project-instructions.md` (either by walking up from the current working directory, or by checking known standard locations).
2. Mounts your blog project directory and your blog's GitHub repo using the Cowork directory-mount tool.
3. Reads the instructions file and reports the resolved paths back to you.
4. Scans `<blog-project-dir>/Posts/` for in-progress pieces (anything with a `state.md` that hasn't reached Phase 4 sign-off) and signed pieces awaiting publish.
5. Proposes the most likely next step:
   - Resume the most recent in-progress piece (`/4d-blog-engine:<phase>`).
   - Publish a signed-but-not-yet-pushed piece (`/4d-blog-engine:publish <slug>`).
   - Start a new piece (`/4d-blog-engine:blog-pipeline <base-doc>`).

If no `blog-project-instructions.md` is found, the skill stops and tells you to run `/4d-blog-engine:blog-init` first.

Read `skills/blog-start/SKILL.md` for the full flow.
