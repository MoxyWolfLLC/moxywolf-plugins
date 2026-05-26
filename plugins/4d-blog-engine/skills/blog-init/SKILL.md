---
name: blog-init
description: |
  This skill should be used when the user runs /4d-blog-engine:blog-init or asks any variant of "set up the blog plugin," "configure 4d-blog-engine for my repo," or "initialize a new blog project." The plugin's user is a WRITER. The setup form asks only what a writer can answer in plain English. Output is a single blog-project-instructions.md file in the writer's blog project directory. Do NOT use this skill for: starting a session on an already-initialized project (use /4d-blog-engine:blog-start), running the actual pipeline (use /4d-blog-engine:blog), or publishing a finished post (use /4d-blog-engine:publish).
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob, mcp__cowork__request_cowork_directory]
---

# Blog-Init — minimal writer-friendly setup

> **Read this when:** the user runs `/4d-blog-engine:blog-init`. The user is a writer. The form asks what the writer knows. Nothing else. The marker file records what the writer said. Nothing else.

## Hard rules — read these first

These rules exist because earlier versions of this skill repeatedly regressed toward asking the writer technical questions or stuffing detected backend values into the user-facing output. Stop.

1. **Do not ask the writer about Payload collections, Payload API URLs, Payload auth modes, server addresses, environment files, static site generators, or any backend infrastructure.** The writer doesn't know and doesn't need to.
2. **Do not read `.env.local`, `payload.config.*`, or any other backend config during setup.** Detection at setup time has no purpose — the writer hasn't published anything yet. Whatever publish needs, publish will figure out at publish time.
3. **Do not display backend values in the setup summary.** No "API base: localhost:3000". No "Auth status: unconfigured". No "Content collection: posts". The writer's eyes should see only what the writer answered.
4. **Do not infer brand options from context.** The four hero vibes below are the only options. The writer's folder choice is not a hint for additional brand options.
5. **Total writer-facing questions: at most 5.** Two folder picks, one name, one vibe, one optional live URL. Nothing more.

## STEP 0 — Re-init check (silent)

Use `Glob` to look for an existing `blog-project-instructions.md` at standard locations. If found, read it silently and use its values as defaults below. Don't announce the re-init.

## STEP 1 — Pick the blog project directory

Call `mcp__cowork__request_cowork_directory` with no `path`. The OS folder picker opens. The writer picks visually.

If they dismiss without picking, ask once whether to retry or cancel.

Store as `BLOG_PROJECT_DIR`.

## STEP 2 — Pick the publishing repo

Call `mcp__cowork__request_cowork_directory` again with no `path`. The writer picks the local clone of their blog's GitHub repo.

Validate only that it's a git repo (silent on pass):

```bash
test -d "<picked>/.git" || echo "not_git"
```

If not a git repo, ask whether to retry the picker: *"That folder isn't a git repo. Pick the folder that contains your blog's `.git` directory."*

Do **not** check for `payload.config.*` here. Do **not** read `.env.local`. The writer might be picking this folder before they've finished setting up the backend, and that's fine — setup doesn't need to know.

Store as `PUBLISHING_REPO_DIR`.

## STEP 3 — Author name

> *What name should appear as the author on posts you publish?*

Free-text. Store as `AUTHOR_NAME`.

## STEP 4 — Hero image vibe

The Release Owner Gate generates a hero image for each post. The vibe sets the palette and style keywords for the image prompt.

Present exactly these four options via `AskUserQuestion`. **Do not add additional options inferred from the writer's folder choice or any other context.**

| Vibe | Palette | Style keywords |
|---|---|---|
| Neutral / minimalist (Recommended) | `#F4F4F2`, `#1A1A1A` | abstract, geometric, minimalist |
| Warm / editorial | `#F8F1E5`, `#2C3E50`, `#C9A66B` | organic, soft, textured |
| Bold / graphic | `#FFFFFF`, `#000000`, `#FF3333` | high-contrast, graphic, modern |
| Dark / atmospheric | `#0A0A0A`, `#E8E8E8`, `#6B7280` | minimalist, atmospheric, monochrome |

All share: forbidden = `text, logos, people, faces, hands`; aspect ratio = `16:9`; dimensions = `1600x900`.

Store the picked vibe's `BRAND_VIBE_NAME`, `BRAND_PALETTE`, `BRAND_KEYWORDS`, plus the fixed `BRAND_FORBIDDEN`, `BRAND_ASPECT`, `BRAND_DIMENSIONS`.

## STEP 5 — Live site URL pattern (optional)

> *Optional. What's your blog's live URL pattern? Used to show you the live link after publishing. Use `{slug}` for the post slug. Example: `https://myblog.com/blog/{slug}/`. Leave blank to skip.*

Free-text, blank-allowed. Store as `LIVE_URL_PATTERN`.

## STEP 6 — Write the marker file

Compose and write to `<BLOG_PROJECT_DIR>/blog-project-instructions.md`:

```markdown
---
title: "4D Blog Engine — Project Instructions"
date: <today YYYY-MM-DD>
type: reference
status: active
plugin: 4d-blog-engine
plugin_version_at_init: 0.3.3
schema: blog-project-instructions/v3
---

# 4D Blog Engine — Project Instructions

This file is the marker the 4d-blog-engine plugin uses to find your blog project. Don't move or rename it.

## Setup

- **Blog project directory:** `<BLOG_PROJECT_DIR>`
- **Publishing repo:** `<PUBLISHING_REPO_DIR>`
- **Author:** `<AUTHOR_NAME>`
- **Hero image vibe:** `<BRAND_VIBE_NAME>`
- **Live site URL pattern:** `<LIVE_URL_PATTERN or "(not set)">`

## Hero image brand style

The Release Owner Gate uses this block to compose the hero-image prompt for each post. Edit values here to change the look without re-running `/blog-init`.

- **Palette:** `<BRAND_PALETTE>`
- **Style keywords:** `<BRAND_KEYWORDS>`
- **Forbidden elements:** `<BRAND_FORBIDDEN>`
- **Aspect ratio:** `<BRAND_ASPECT>`
- **Dimensions:** `<BRAND_DIMENSIONS>`

## How to change anything

Edit values above directly. The plugin reads this file every time you run `/blog-start`, `/blog`, or `/publish`. No need to re-run `/blog-init` unless the directory paths themselves change.
```

## STEP 7 — Create Posts/ subdirectory

```bash
mkdir -p "<BLOG_PROJECT_DIR>/Posts"
```

Silent. No announcement.

## STEP 8 — Report back

```
Blog project ready.

  Project folder: <BLOG_PROJECT_DIR>
  Publishing to:  <PUBLISHING_REPO_DIR>
  Author:         <AUTHOR_NAME>
  Hero vibe:      <BRAND_VIBE_NAME>

Next: run /4d-blog-engine:blog <path-to-your-base-document> to write your first post.
```

That's the entire summary. No "auth status," no "API base," no "content collection," no Payload anything. The writer sees what the writer chose.

## What this skill does NOT do

- It does not read `payload.config.*`.
- It does not read `.env.local`.
- It does not detect, store, or display backend infrastructure values.
- It does not validate that the publishing repo is a Payload project. (Publish will check that at publish time, when the writer is actually trying to publish.)
- It does not infer brand vibes from context.

## Degradation behaviors

- **Folder picker unavailable** (remote Cowork session): fall back to `AskUserQuestion` with a couple of plausible default paths plus a "Custom" free-text option. Surface a one-line note that the picker is unavailable.
- **Writer wants a brand vibe outside the 4 options:** tell them they can edit the brand-style block in `blog-project-instructions.md` directly to customize the palette and keywords. Don't add a fifth option in this skill.
