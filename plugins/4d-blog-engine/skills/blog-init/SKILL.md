---
name: blog-init
description: |
  This skill should be used when the user runs /4d-blog-engine:blog-init or asks any variant of "set up the blog plugin," "configure 4d-blog-engine for my repo," "initialize a new blog project," or "wire up the blog engine." The plugin's user is a WRITER, not a developer — so this skill auto-detects every Payload-technical value (collections, server URL, auth) from payload.config.* and .env.local rather than asking the user. The interactive form asks only what a writer can answer: folder picks, author name, and a hero-image brand vibe. Output is a single blog-project-instructions.md file at the root of the blog project directory. Do NOT use this skill for: starting a session on an already-initialized project (use /4d-blog-engine:blog-start), running the actual pipeline (use /4d-blog-engine:blog), or publishing a finished post (use /4d-blog-engine:publish).
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob, Grep, mcp__cowork__request_cowork_directory]
---

# Blog-Init — writer-friendly setup

> **Read this when:** the user runs `/4d-blog-engine:blog-init`. The user is a WRITER. They don't know what a Payload collection is. They don't have a Payload API base URL in their head. Don't ask them about any of that. Detect it from the repo and the env file. The form asks the writer ONLY what a writer can answer.

## Hard rules — read these first

These rules exist because earlier versions of this skill kept regressing toward asking the writer technical Payload questions. Don't.

1. **Do not ask about Payload collections.** Read `payload.config.*` and detect them. Pick the content collection and the media collection by the heuristics below. Record the choices in the marker file. If the writer wants to override, they edit the marker file by hand — that's a power-user path, not a setup-form question.
2. **Do not ask about Payload API base URL.** Read `<repo>/.env.local` for `PAYLOAD_PUBLIC_SERVER_URL`, `NEXT_PUBLIC_PAYLOAD_URL`, `PAYLOAD_API_URL`, `PAYLOAD_SERVER_URL`, or `NEXT_PUBLIC_SERVER_URL` (in that priority order). Fall back to `http://localhost:3000` if none. No question.
3. **Do not ask about auth mode.** Detect whether `<repo>/.env.local` has `PAYLOAD_API_KEY` set; record `apiKey` if yes, `unconfigured` if no. The writer fixes this later by adding the key to `.env.local` when they're ready to publish. No question.
4. **Never add a brand option named after any specific blog or site, even if the user's selected folder belongs to one.** The plugin is generic. The four brand vibes below are the only allowed options. Do not infer additional brand options from context.
5. **Total writer-facing question count: 5.** Folder pick (project dir), folder pick (repo), author name, brand vibe, optional live URL pattern. Anything beyond that needs explicit re-spec.

## STEP 0 — Re-init check (silent)

Use `Glob` to look for an existing `blog-project-instructions.md` at standard locations. If found, read it and use its values as pre-filled defaults below. Don't surface the re-init banner unless something asks — silently use the existing values.

## STEP 1 — Pick the blog project directory (folder picker)

Call `mcp__cowork__request_cowork_directory` with no `path` argument. The user picks via the OS folder picker.

If the user dismisses without picking, ask once whether to retry or cancel.

Store as `BLOG_PROJECT_DIR`.

## STEP 2 — Pick the publishing repo (folder picker)

Call `mcp__cowork__request_cowork_directory` again with no `path`. The user picks the local clone of their Payload-backed blog repo.

Validate behind the scenes (no question to the user unless validation fails):

```bash
test -d "<picked>/.git" || echo "not_git"
find "<picked>" -maxdepth 4 -name "payload.config.*" -type f 2>/dev/null | head -1
```

If either check fails, surface a clear single-line message and ask whether to retry the picker:

- Not a git repo → *"That folder isn't a git repo. Pick the root of your cloned blog repo (the folder containing `.git`)."*
- No payload.config.* → *"I couldn't find a `payload.config.ts` (or `.js`) in that folder. The plugin assumes Payload CMS. Pick the root of your Payload project."*

Store as `PAYLOAD_REPO_DIR`. Capture for the marker file (silently, no user question):

- `PAYLOAD_CONFIG_PATH` — path to the payload.config.* file
- `PAYLOAD_GIT_REMOTE` — `git -C <repo> config --get remote.origin.url` (may be empty)

## STEP 3 — Auto-detect Payload config (silent)

Read `PAYLOAD_CONFIG_PATH` and any imported collection files. Detect:

### Content collection

Scan the `collections:` array. Pick the content collection using these heuristics in order:

1. A collection named `posts` exists → pick it.
2. Otherwise: the first collection that has BOTH a `slug` field AND a rich-text/lexical/textarea body-shaped field, AND is NOT an upload collection (`upload: true`) AND is NOT obviously an auth/user collection (slug like `users`, `staff`, `authors`, `members`, `admins`).
3. Otherwise: the first non-upload, non-auth collection.
4. Otherwise: default to `posts` and record `auto_detected: false` in the marker file.

Store as `CONTENT_COLLECTION`.

### Media collection

Scan the `collections:` array. Pick the media collection using these heuristics:

1. A collection with `upload: true` (or `type: 'upload'` on any field) AND a slug of exactly `media` → pick it.
2. Otherwise: the first collection with `upload: true`.
3. Otherwise: default to `media` and record `auto_detected: false`.

Store as `MEDIA_COLLECTION`.

### Payload API base URL

Read `<PAYLOAD_REPO_DIR>/.env.local`. Look for these variable names in priority order:

1. `PAYLOAD_PUBLIC_SERVER_URL`
2. `NEXT_PUBLIC_PAYLOAD_URL`
3. `PAYLOAD_API_URL`
4. `PAYLOAD_SERVER_URL`
5. `NEXT_PUBLIC_SERVER_URL`

If none, fall back to `http://localhost:3000`. Store as `PAYLOAD_API_BASE`. Never ask the user.

### Auth status

Check whether `<PAYLOAD_REPO_DIR>/.env.local` defines `PAYLOAD_API_KEY` (any non-empty value).

- If yes → `PAYLOAD_AUTH_STATUS = "apiKey configured"`.
- If no → `PAYLOAD_AUTH_STATUS = "unconfigured — add PAYLOAD_API_KEY to .env.local before first publish"`.

Never read or store the key value itself. Only the presence flag.

## STEP 4 — Ask the writer for their name (free text)

> *What name should appear as the author on posts you publish?*

Free-text. Store as `AUTHOR_NAME`.

## STEP 5 — Ask the writer for a hero image vibe

The Release Owner Gate generates a hero image for each post. The vibe sets the palette and style keywords used when composing the image prompt.

Present exactly these four options via `AskUserQuestion`. **Do not add additional options inferred from context. Do not name any option after a specific site or brand.**

| Vibe | Palette | Style keywords |
|---|---|---|
| Neutral / minimalist (Recommended) | `#F4F4F2`, `#1A1A1A` | abstract, geometric, minimalist |
| Warm / editorial | `#F8F1E5`, `#2C3E50`, `#C9A66B` | organic, soft, textured |
| Bold / graphic | `#FFFFFF`, `#000000`, `#FF3333` | high-contrast, graphic, modern |
| Dark / atmospheric | `#0A0A0A`, `#E8E8E8`, `#6B7280` | minimalist, atmospheric, monochrome |

All four share a fixed forbidden list: `text, logos, people, faces, hands`. All four use 16:9 at 1600×900.

Store the picked vibe's palette as `BRAND_PALETTE`, keywords as `BRAND_KEYWORDS`, plus `BRAND_FORBIDDEN`, `BRAND_ASPECT`, `BRAND_DIMENSIONS` (the last three fixed). Also store `BRAND_VIBE_NAME` for the marker file's human-readable label.

If the writer wants something other than these four, they edit the marker file by hand. That's deliberate — vibes are easy to pick; bespoke palettes are easy to type into a markdown file.

## STEP 6 — Live site URL pattern (optional, single text question)

> *Optional. What's your blog's live URL pattern? Used to show you the live link after publishing. Use `{slug}` for the post slug. Example: `https://myblog.com/blog/{slug}/`. Leave blank to skip.*

Free-text, blank-allowed. Store as `LIVE_URL_PATTERN` (may be empty).

## STEP 7 — Write blog-project-instructions.md

Compose and write to `<BLOG_PROJECT_DIR>/blog-project-instructions.md`:

```markdown
---
title: "4D Blog Engine — Project Instructions"
date: <today YYYY-MM-DD>
type: reference
status: active
plugin: 4d-blog-engine
plugin_version_at_init: 0.3.2
schema: blog-project-instructions/v2
backend: payload
---

# 4D Blog Engine — Project Instructions

This file is the marker the 4d-blog-engine plugin uses to find your blog project. Don't move or rename it.

## What you told the plugin

- **Blog project directory:** `<BLOG_PROJECT_DIR>`
- **Publishing repo:** `<PAYLOAD_REPO_DIR>`
- **Author:** `<AUTHOR_NAME>`
- **Live site URL pattern:** `<LIVE_URL_PATTERN or "(not set)">`
- **Hero image vibe:** `<BRAND_VIBE_NAME>`

## What the plugin detected (you don't need to touch these)

- **Payload config path:** `<PAYLOAD_CONFIG_PATH>`
- **Git remote:** `<PAYLOAD_GIT_REMOTE or "(unknown)">`
- **Content collection:** `<CONTENT_COLLECTION>` (auto-detected from `payload.config.*`)
- **Media collection:** `<MEDIA_COLLECTION>` (auto-detected)
- **Payload API base URL:** `<PAYLOAD_API_BASE>` (from `.env.local`, or `http://localhost:3000` default)
- **Auth status:** `<PAYLOAD_AUTH_STATUS>`

## Hero image brand style

The Release Owner Gate uses this block to compose the hero-image prompt for each post. Edit values directly to change the look without re-running blog-init.

- **Palette:** `<BRAND_PALETTE>`
- **Style keywords:** `<BRAND_KEYWORDS>`
- **Forbidden elements:** `<BRAND_FORBIDDEN>`
- **Aspect ratio:** `<BRAND_ASPECT>`
- **Dimensions:** `<BRAND_DIMENSIONS>`

## How to override anything

If something the plugin detected is wrong (a different collection should receive posts, a different server URL, a different vibe), edit the values above directly. The plugin reads this file every time you run `/blog-start`, `/blog`, or `/publish`. No need to re-run `/blog-init` for an override.

If the directory paths themselves change (you move folders), re-run `/blog-init`.
```

## STEP 8 — Create Posts/ subdirectory (silent)

```bash
mkdir -p "<BLOG_PROJECT_DIR>/Posts"
```

No question, no announcement.

## STEP 9 — Report back (keep it short)

End the skill with a concise summary. Don't list every detected value — surface what the writer needs to know:

```
Blog project ready.

  Project folder: <BLOG_PROJECT_DIR>
  Publishing to:  <PAYLOAD_REPO_DIR>
  Author:         <AUTHOR_NAME>
  Hero vibe:      <BRAND_VIBE_NAME>

Setup file: <BLOG_PROJECT_DIR>/blog-project-instructions.md

<one-line auth note if PAYLOAD_AUTH_STATUS is unconfigured:>
Before you publish your first post, add `PAYLOAD_API_KEY=<your-key>` to
<PAYLOAD_REPO_DIR>/.env.local. You only do this once.

Next: run /4d-blog-engine:blog <path-to-your-base-document>
to write your first post.
```

If `PAYLOAD_AUTH_STATUS` is `"apiKey configured"`, drop the auth note entirely.

## What this skill does NOT do

- It does not install the plugin.
- It does not write to the publishing repo.
- It does not read, store, or transmit the actual Payload API key value.
- It does not ask the writer technical Payload questions. Auto-detect, don't interrogate.
- It does not add brand vibes inferred from the user's folder choice. The four vibes above are the only options.

## Degradation behaviors

- **Folder picker unavailable** (remote Cowork session): fall back to `AskUserQuestion` with plausible default paths plus a "Custom" free-text option. Surface a one-line note that the picker is unavailable.
- **`payload.config.*` not found** in the picked repo: ask the user whether to proceed (some Payload setups use non-standard config locations). If yes, set `PAYLOAD_CONFIG_PATH = (unknown)`, default `CONTENT_COLLECTION = posts`, `MEDIA_COLLECTION = media`, mark both as `auto_detected: false`, and continue.
- **`.env.local` not found:** silently use the default `PAYLOAD_API_BASE = http://localhost:3000` and set `PAYLOAD_AUTH_STATUS = "unconfigured — no .env.local found"`. Mention in the auth note that they'll need to create one.
- **Collection auto-detection ambiguous** (multiple plausible content collections): default to `posts`; don't ask. The writer can edit the marker file if the default is wrong.
- **User wants something outside the 4 brand vibes:** point them at the marker file's brand-style block. Don't add a fifth option to this skill.
