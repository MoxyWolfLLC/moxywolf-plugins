---
name: blog-init
description: |
  This skill should be used when the user runs /4d-blog-engine:blog-init or asks any variant of "set up the blog plugin," "configure 4d-blog-engine for my repo," "initialize a new blog project," "wire up the blog engine to my Payload site," or "tell the plugin where to publish my posts." It runs an interactive setup that produces a blog-project-instructions.md file at the root of the user's blog project directory. The plugin assumes a Payload CMS backend — content publishes to a Payload collection via the REST API, not as markdown files in a static-site-generator folder. Do NOT use this skill for: starting a session on an already-initialized project (use /4d-blog-engine:blog-start), running the actual pipeline (use /4d-blog-engine:blog), or publishing a finished post (use /4d-blog-engine:publish).
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob, mcp__cowork__request_cowork_directory]
---

# Blog-Init — one-time setup for a Payload-backed blog

> **Read this when:** the user runs `/4d-blog-engine:blog-init` or asks to set up the 4d-blog-engine plugin. The plugin is hard-wired to Payload CMS — don't ask the user what static site generator they're using. The output is a single `blog-project-instructions.md` file at the root of their blog project directory.

## What this skill produces

A single file at `<blog-project-dir>/blog-project-instructions.md`. The orchestrator's discovery walk treats this file as the marker that identifies a blog project. The skill also ensures `Posts/` exists inside the blog project directory (where the pipeline writes its working drafts).

After running this once, the user runs `/4d-blog-engine:blog-start` to load the project, then `/4d-blog-engine:blog <base-doc>` to write a post, then `/4d-blog-engine:publish <slug>` to ship it (in v0.3.0 publish still uses git; the Payload-API publish flow is a planned change).

## Folder-picker convention — use the OS picker, not text inputs

For directory questions, **call `mcp__cowork__request_cowork_directory` with no `path` argument** — that opens the native OS folder picker in local Cowork sessions. The user sees a real Finder dialog, picks the folder visually, and the tool returns the path string. Do not present text-input fallbacks unless the picker is unavailable (only in remote sessions, where the user has no local filesystem).

Specifically: never ask the user to type a path like `/Users/<you>/Documents/GitHub/my-blog` into a textarea. That's the friction the picker eliminates.

## STEP 0 — Check if this is a re-init

Before asking anything, use `Glob` to look for an existing `blog-project-instructions.md` in standard locations. If one is found, Read it and tell the user:

> *I found an existing setup at `<path>`. Re-running blog-init will update it. Your existing answers are pre-filled as defaults below.*

Use the existing answers as defaults below.

## STEP 1 — Pick the blog project directory

Call `mcp__cowork__request_cowork_directory` with no path. The user picks a folder via the OS dialog.

After the user picks, the response includes the absolute path. Use Bash to confirm it exists. Store as `BLOG_PROJECT_DIR`.

If the user dismisses the picker without selecting, ask once via `AskUserQuestion` whether to retry the picker or cancel.

## STEP 2 — Pick the Payload GitHub repo

Call `mcp__cowork__request_cowork_directory` again with no path. The user picks the local clone of their Payload site's GitHub repo.

After the user picks, validate it's a Payload project + git repo:

```bash
# Is it a git repo?
test -d "<picked-path>/.git" && echo "yes_git" || echo "no_git"

# Does it have a payload.config.ts (or .js)?
find "<picked-path>" -maxdepth 4 -name "payload.config.*" -type f 2>/dev/null | head -1
```

If either check fails, tell the user clearly what's missing and offer to retry the picker:

- Not a git repo → *"That folder isn't a git repo. Pick the cloned repo's root folder (the one that contains the .git directory)."*
- No payload.config.* → *"I couldn't find a payload.config.ts (or .js) in that folder. The plugin assumes Payload CMS — pick the root of your Payload project."*

Also capture the remote URL for the user-facing summary:

```bash
git -C "<picked-path>" config --get remote.origin.url 2>/dev/null
```

Store as `PAYLOAD_REPO_DIR`, `PAYLOAD_CONFIG_PATH` (the path to payload.config.*), and `PAYLOAD_GIT_REMOTE`.

## STEP 3 — Detect Payload collections

Read `PAYLOAD_CONFIG_PATH` and any imported collection files to identify what collections the user has. Look for the `collections:` array in the config and the collection slugs they reference.

Surface the detected collections to the user via `AskUserQuestion`:

> *Your Payload config has these collections: `<detected list>`. Which one do new blog posts get written to?*

Provide each detected collection as an option, plus a "Custom — type the slug" fallback.

Default recommendation: if a collection named `posts` exists, recommend it (the Payload-template convention). Otherwise recommend the first collection that is neither a media/upload collection nor an auth/user collection.

Also identify the **media collection** automatically (usually `media`) by looking for a collection with `upload: true` or `type: 'upload'` fields. If multiple, ask. Store as `MEDIA_COLLECTION` (default `media`).

Store the chosen content collection as `CONTENT_COLLECTION`.

## STEP 4 — Payload server URL

Ask via `AskUserQuestion`:

> *What's the Payload server URL the publish command should POST to?*

Options:

1. `http://localhost:3000` — local dev server (Payload + Next.js default)
2. `https://<your-site>.com` — production
3. Both (dev for drafts, prod for final) — Custom routing
4. Custom — type your own

Store as `PAYLOAD_API_BASE` (single value for v0.3.0; multi-environment publishing is a v0.4+ concern).

Hint to the user: the publish flow that ships in v0.3.0 still uses git; the Payload REST API publish flow is the next planned change. Store this value so it's ready when that lands.

## STEP 5 — Auth approach for the Payload API

Ask:

> *How should `/publish` authenticate to your Payload API?*

Options:

1. **API key on a Staff user (Recommended)** — Add an `apiKey: true` field on your Staff collection. The publish command reads the key from `<repo>/.env.local` as `PAYLOAD_API_KEY` (gitignored).
2. **Email/password login** — publish performs `POST /api/staff/login` at publish time to get a session token. Slower; not ideal for automated workflows.
3. **Configure later** — skip this now. Set up before first publish.

Store as `PAYLOAD_AUTH_MODE`.

If option 1, also tell the user the exact change to make in their Staff collection (`apiKey: true` flag, regenerate types) and where to drop the key (`<repo>/.env.local`).

## STEP 6 — Live site URL pattern (optional)

Ask:

> *What's your live site URL pattern? Used to preview the live URL after publish. Use `{YYYY}`, `{MM}`, `{DD}`, `{slug}` as placeholders. Example: `https://myblog.com/posts/{slug}/`. Skip if you don't have one.*

Free-text. Store as `LIVE_URL_PATTERN`.

## STEP 7 — Hero image brand style

The Release Owner Gate's Stage 3 generates a hero image for each post. The image prompt is composed from a brand-style block + the post's central metaphor. The plugin reads the brand-style block from this file at gate time — so it stays per-blog instead of being hardcoded to any particular site's look.

Ask via `AskUserQuestion`:

> *What style should hero images use?*

Options:

1. **Neutral / minimalist (Recommended)** — abstract, geometric, no text, no logos, no people. Two-tone palette (off-white + dark gray). Safe default for any blog.
2. **Configure custom** — supply your own palette, style keywords, and forbidden-element list.
3. **Skip** — fall back to the neutral default. You can edit `brand_style:` in `blog-project-instructions.md` later.

If the user picks **Configure custom**, ask three follow-up questions in sequence:

- **Palette.** Free-text. Expect 2-5 hex codes, comma-separated. Example: `#1A1A1A, #FFFFFF, #C9A66B`.
- **Style keywords.** Free-text. Expect 2-5 words/phrases, comma-separated. Example: `geometric, abstract, soft gradient`.
- **Forbidden elements.** Free-text. Defaults to `text, logos, people, faces, hands`. Expand if the user has specific exclusions.

Store the four values as `BRAND_PALETTE`, `BRAND_KEYWORDS`, `BRAND_FORBIDDEN`. For the neutral default, populate them as:

- `BRAND_PALETTE = "#F4F4F2, #1A1A1A"`
- `BRAND_KEYWORDS = "abstract, geometric, minimalist"`
- `BRAND_FORBIDDEN = "text, logos, people, faces, hands"`

Also fix `BRAND_ASPECT = "16:9"` and `BRAND_DIMENSIONS = "1600x900"` — these are standard for OpenGraph / social-share heroes and not worth asking about. Users who want different dimensions can edit the marker file by hand.

## STEP 8 — Author name

Ask:

> *What name should appear as the author in post frontmatter and commit messages?*

Free-text. Store as `AUTHOR_NAME`. (For Payload, "author" maps to an Authors collection record — handling that mapping is a publish-flow concern, deferred.)

## STEP 9 — Write blog-project-instructions.md

Compose and write the file to `<BLOG_PROJECT_DIR>/blog-project-instructions.md`:

```markdown
---
title: "4D Blog Engine — Project Instructions"
date: <today YYYY-MM-DD>
type: reference
status: active
plugin: 4d-blog-engine
plugin_version_at_init: 0.3.0
schema: blog-project-instructions/v2
backend: payload
---

# 4D Blog Engine — Project Instructions (Payload backend)

This file is the marker the 4d-blog-engine plugin uses to find your blog project. Don't move or rename it — the plugin walks up the filesystem looking for it.

## Project Setup

- **Blog project directory:** `<BLOG_PROJECT_DIR>`
- **Payload repo:** `<PAYLOAD_REPO_DIR>`
- **Payload config path:** `<PAYLOAD_CONFIG_PATH>`
- **Git remote:** `<PAYLOAD_GIT_REMOTE or "(unknown)">`
- **Content collection:** `<CONTENT_COLLECTION>` (typical Payload-blog default: `posts`)
- **Media collection:** `<MEDIA_COLLECTION>` (default `media`)
- **Payload API base URL:** `<PAYLOAD_API_BASE>`
- **Auth mode:** `<PAYLOAD_AUTH_MODE>`
- **Live site URL pattern:** `<LIVE_URL_PATTERN or "(not set)">`
- **Author:** `<AUTHOR_NAME>`

## Hero image brand style

The Release Owner Gate's Stage 3 reads this block to compose the hero-image prompt for each post. Edit the values directly to change the look without re-running blog-init.

- **Palette:** `<BRAND_PALETTE>`
- **Style keywords:** `<BRAND_KEYWORDS>`
- **Forbidden elements:** `<BRAND_FORBIDDEN>`
- **Aspect ratio:** `<BRAND_ASPECT>` (default `16:9`)
- **Dimensions:** `<BRAND_DIMENSIONS>` (default `1600x900`)

## How the plugin uses these

When you run `/4d-blog-engine:blog <base-doc>`, the plugin writes pieces to:

`<BLOG_PROJECT_DIR>/Posts/<YYYY-MM-DD-slug>/`

Each piece directory holds the four-phase artifacts plus the signed blog and LinkedIn pair.

When you run `/4d-blog-engine:publish <slug>` (current behavior in v0.3.0 is git-based; Payload REST-API publishing is a planned upgrade):

1. Verifies Phase 4 signed (`Verified — <initials>, <date>` in changelog.md).
2. Uses the values above to ship the post.

## Planned: Payload REST-API publish flow

In a future plugin version, `/publish` will:

1. POST the hero image to `<PAYLOAD_API_BASE>/api/<MEDIA_COLLECTION>` using the configured auth.
2. POST the structured fields (title, slug, subtitle, abstract, keyIdeas, citations, status) to `<PAYLOAD_API_BASE>/api/<CONTENT_COLLECTION>`.
3. Link the hero image record to the content record.
4. Report the admin URL and the live URL.

The current file captures the config so that upgrade is a drop-in.

## Rules

- This file is the marker. Don't move or rename it.
- The plugin reads this file every time you run `/blog-start`, `/blog`, or `/publish`.
- If anything moves on disk or the Payload config changes, re-run `/4d-blog-engine:blog-init` to update.
```

## STEP 10 — Create the Posts/ subdirectory

If `<BLOG_PROJECT_DIR>/Posts/` doesn't exist, create it:

```bash
mkdir -p "<BLOG_PROJECT_DIR>/Posts"
```

## STEP 11 — Report back to the user

End the skill with a concise summary:

```
Blog project initialized for Payload.

  Blog project dir:    <BLOG_PROJECT_DIR>
  Payload repo:        <PAYLOAD_REPO_DIR>
  Payload config:      <PAYLOAD_CONFIG_PATH>
  Content collection:  <CONTENT_COLLECTION>
  Media collection:    <MEDIA_COLLECTION>
  API base:            <PAYLOAD_API_BASE>
  Auth mode:           <PAYLOAD_AUTH_MODE>
  Live URL pattern:    <LIVE_URL_PATTERN or "(not set)">
  Hero brand style:    palette=<BRAND_PALETTE>; keywords=<BRAND_KEYWORDS>
  Author:              <AUTHOR_NAME>

Instructions file:     <BLOG_PROJECT_DIR>/blog-project-instructions.md

Next steps:
  1. Run /4d-blog-engine:blog-start to confirm the plugin sees your project.
  2. Run /4d-blog-engine:blog <path-to-base-doc> to write your first post.
  3. (When the Payload-API publish flow lands.) Add the apiKey field to your
     Staff collection and drop your key in <repo>/.env.local.

If anything's wrong above, re-run /4d-blog-engine:blog-init — it'll keep your
previous answers as defaults.
```

## What this skill does NOT do

- It does not install the plugin.
- It does not write to the Payload repo. Only `<BLOG_PROJECT_DIR>/blog-project-instructions.md` and (optionally) `<BLOG_PROJECT_DIR>/Posts/`.
- It does not validate Payload auth, generate API keys, or touch `.env.local`. It just records the user's stated intent.
- It does not POST anything to the Payload API. That's the publish skill's job.

## Degradation behaviors

- **Folder picker isn't available** (remote Cowork session): fall back to `AskUserQuestion` with two or three plausible default paths plus a "Custom" free-text option. Surface a one-line warning that the picker is unavailable.
- **payload.config.* not found** in the picked repo: don't auto-fail — ask the user whether to proceed anyway (some Payload setups use non-standard locations). If yes, set `PAYLOAD_CONFIG_PATH` to `(unknown)` and continue.
- **Collection auto-detection fails** (config too dynamic to parse statically): fall back to asking the user to type the collection slug. Suggest `posts` as the typical Payload-blog default.
- **User cancels mid-flow:** save partial answers to a stash file at `<BLOG_PROJECT_DIR>/.blog-init-draft.md` so the next run picks up where they left off.
