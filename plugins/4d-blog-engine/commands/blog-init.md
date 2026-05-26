---
description: One-time setup for a Payload-backed blog. Pick your blog project folder, pick your Payload GitHub repo, and the skill captures the rest.
argument-hint: (no arguments — runs interactively with native folder pickers)
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob, mcp__cowork__request_cowork_directory]
---

# /4d-blog-engine:blog-init — one-time blog project setup

The plugin is hard-wired to **Payload CMS** as the publishing backend. It does not ask you whether you're using Hugo or Jekyll, because the answer is always Payload — published posts land in your Payload database via the REST API, hero images upload to your media collection, and the live site reads from Payload. The plugin is independent of any particular Payload site — it auto-detects your collections and adapts to your setup.

The skill walks you through:

1. **Pick your blog project directory** via the native folder picker — this is where the plugin writes drafts, hero images, slop reports, and signed posts. Think of it as your workshop.
2. **Pick the local clone of your Payload GitHub repo** via the same folder picker — the skill confirms it's a git repo and finds your `payload.config.ts`.
3. **Auto-detect your Payload collections** and ask which one new posts go to (the typical Payload-blog convention is `posts`, but the skill recommends whichever content-shaped collection your config actually has). Auto-detects the media collection too.
4. **Payload API base URL** — typically `http://localhost:3000` for dev or your production domain.
5. **Auth approach for the Payload API** — Staff API key (recommended), or email/password.
6. **Live site URL pattern, optional** — used to show you the predicted live URL after publish.
7. **Author name** for post frontmatter and commit messages.

After the skill writes `blog-project-instructions.md` to the top of your blog project directory, run `/4d-blog-engine:blog-start` to confirm setup, then `/4d-blog-engine:blog <base-doc>` to write your first post.

Read `skills/blog-init/SKILL.md` for the full flow.

**Note on publish flow:** v0.3.0 still uses git-based publishing (carried over from v0.2.0). The Payload REST-API publish flow — POST the hero image to `/api/<media-collection>`, POST the post fields to `/api/<content-collection>` — is the next planned change. `blog-init` captures the Payload config now so that upgrade is a drop-in.
