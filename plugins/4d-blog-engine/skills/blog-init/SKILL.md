---
name: blog-init
description: |
  This skill should be used when the user runs /4d-blog-engine:blog-init or asks any variant of "set up the blog plugin," "configure 4d-blog-engine for my repo," "initialize a new blog project," "wire up the blog engine to my GitHub repo," or "tell the plugin where to put my posts." It runs an interactive 4-question setup that produces a blog-project-instructions.md file at the root of the user's blog project directory. This file is the marker that /4d-blog-engine:blog-start and the 4d-blog-engine orchestrator's STEP 1 discovery walk look for. Do NOT use this skill for: starting a session on an already-initialized project (use /4d-blog-engine:blog-start), running the actual pipeline (use /4d-blog-engine:blog), or publishing a finished post (use /4d-blog-engine:publish).
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob]
---

# Blog-Init — one-time setup for a blog project

> **Read this when:** the user runs `/4d-blog-engine:blog-init` or asks to set up the 4d-blog-engine plugin for their blog repo. The skill collects four pieces of configuration and writes a single marker file to the blog project directory.

## What this skill produces

A single file at `<blog-project-dir>/blog-project-instructions.md`. The orchestrator's discovery walk treats this file as the marker that identifies a blog project. The skill also creates the directory if it doesn't exist yet and sets up `Posts/` as a subdirectory (where pipeline pieces will land).

After running this once, the user runs `/4d-blog-engine:blog-start` to load the project, then `/4d-blog-engine:blog <base-doc>` to actually write a post, then `/4d-blog-engine:publish <slug>` to ship it.

## STEP 0 — Check if this is a re-init

Before asking anything, check whether the user already has a `blog-project-instructions.md` somewhere on disk. Use `Glob` against a small set of common paths the user might point you at later. If you find an existing file, read its frontmatter and tell the user:

> *I found an existing setup at `<path>`. Re-running blog-init will update it. Your existing answers are pre-filled as defaults; press enter to keep each one or type a new value.*

Use the existing answers as defaults in the questions below. If no existing file is found, proceed with empty defaults.

## STEP 1 — Question 1: Blog project directory

Ask via `AskUserQuestion`:

> *Where is (or should be) your blog project directory? This is where the plugin writes drafts, hero images, slop reports, and signed posts. It's separate from your GitHub repo — think of it as your workshop, the GitHub repo is your storefront.*

Provide 3 options:

1. `~/Documents/MyBlog` (Recommended) — Standard location. Skill will create it if missing.
2. `~/Blog` — Shorter path, also fine.
3. Other — Free-text input, user supplies their own path.

After the user picks, expand `~` to the absolute path. Use Bash to check whether the directory exists. If it doesn't, ask:

> *That directory doesn't exist yet. Create it now?*

If yes, `mkdir -p` the directory. If no, halt with: *"Blog project directory must exist before init can continue. Create it manually and re-run /4d-blog-engine:blog-init."*

Store the absolute path as `BLOG_PROJECT_DIR`.

## STEP 2 — Question 2: GitHub repo for publishing

Ask:

> *Where is the local clone of the GitHub repo your live blog site is built from? This is the repo `/4d-blog-engine:publish` will commit your finished posts into. It's the repo whose `git push` triggers your site rebuild on GitHub Pages / Vercel / Netlify / whatever you use.*

Provide options:

1. `~/Documents/GitHub/<your-blog-repo>` — Standard MoxyWolf location, Mac default.
2. Other — Free-text input.

After the user supplies a path, validate it with Bash:

```bash
test -d "<path>/.git" && echo "valid_git_repo" || echo "not_a_repo"
```

If `not_a_repo`, halt with:

> *That folder isn't a git repo. Clone your blog's repo locally first (GitHub Desktop's "Clone a repository from the Internet" works, or `git clone <url>` in Terminal), then re-run /4d-blog-engine:blog-init.*

If `valid_git_repo`, also read the remote URL so you can show it back to the user later:

```bash
git -C "<path>" config --get remote.origin.url 2>/dev/null
```

If git is unavailable in the sandbox, skip this read — it's just for the confirmation summary. The publish command does its own checks.

Store the absolute path as `GITHUB_REPO_DIR` and the remote URL as `GITHUB_REMOTE_URL` (may be empty).

## STEP 3 — Question 3: Posts folder inside the repo

Ask:

> *Where inside that repo do new posts go? The default depends on your static site generator:*

Provide options:

1. `content/blog/` (Recommended) — Hugo default.
2. `_posts/` — Jekyll default.
3. `src/content/blog/` — Astro default.
4. Other — Free-text input.

Store as `POSTS_SUBFOLDER`. Trailing slash optional; the publish skill normalizes.

If the user picks one and Bash shows the folder doesn't exist inside the repo yet, ask whether to create it. Don't force the create — some site generators are fussy about which folder triggers them.

## STEP 4 — Question 4: Images folder inside the repo

Ask:

> *Where do hero images go inside the repo?*

Provide options:

1. `static/images/blog/` (Recommended) — Hugo convention.
2. `assets/images/` — Jekyll convention.
3. `public/images/blog/` — Astro convention.
4. Other — Free-text input.

Store as `IMAGES_SUBFOLDER`.

## STEP 5 — Question 5: Live site URL pattern (optional)

Ask:

> *What's your live site URL pattern, if you know it? After `/publish` runs, the plugin uses this to show you the predicted live URL. Use `{YYYY}`, `{MM}`, `{DD}`, and `{slug}` as placeholders. Example: `https://myblog.com/{YYYY}/{MM}/{slug}/`. Type "skip" if you don't know or don't have one.*

This is free-text. Store as `LIVE_URL_PATTERN` (may be empty/skip).

## STEP 6 — Question 6: Author name

Ask:

> *What name should appear as the author in post frontmatter and commit messages?*

Free-text. Store as `AUTHOR_NAME`.

## STEP 7 — Write blog-project-instructions.md

Compose the file content and write it to `<BLOG_PROJECT_DIR>/blog-project-instructions.md`:

```markdown
---
title: "4D Blog Engine — Project Instructions"
date: <today YYYY-MM-DD>
type: reference
status: active
plugin: 4d-blog-engine
plugin_version_at_init: 0.2.0
schema: blog-project-instructions/v1
---

# 4D Blog Engine — Project Instructions

This file is the marker the 4d-blog-engine plugin uses to find your blog project. Don't move or rename it — the plugin walks up the filesystem looking for it.

## Project Setup

- **Blog project directory:** `<BLOG_PROJECT_DIR>`
- **GitHub repo for publishing:** `<GITHUB_REPO_DIR>`
- **GitHub remote URL:** `<GITHUB_REMOTE_URL or "(unknown)">`
- **Posts folder inside repo:** `<POSTS_SUBFOLDER>`
- **Images folder inside repo:** `<IMAGES_SUBFOLDER>`
- **Live site URL pattern:** `<LIVE_URL_PATTERN or "(not set)">`
- **Author:** `<AUTHOR_NAME>`

## How the plugin uses these

When you run `/4d-blog-engine:blog <base-doc>`, the plugin writes pieces to:

`<BLOG_PROJECT_DIR>/Posts/<YYYY-MM-DD-slug>/`

Each piece directory holds the four-phase artifacts (delegation, description, discernment, diligence) plus the signed blog and LinkedIn pair.

When you run `/4d-blog-engine:publish <slug>`, the plugin:

1. Copies `<BLOG_PROJECT_DIR>/Posts/<slug>/04-diligence/blog.md` → `<GITHUB_REPO_DIR>/<POSTS_SUBFOLDER>/<slug>.md`
2. Copies the hero image → `<GITHUB_REPO_DIR>/<IMAGES_SUBFOLDER>/<slug>.png`
3. Rewrites the image reference in the post's frontmatter to point to the new path.
4. Auto-generates a plain-text commit message (`Publish: <title>`).
5. Runs `git add` + `git commit` + `git push` against the default branch.
6. Reports the GitHub commit URL and (if set above) the predicted live URL.

The plugin never publishes for you automatically. `/publish` only runs when you explicitly ask it to, and only on a piece that has passed Phase 4 (the Release Owner Gate) and been signed by hand.

## Rules

- This file is the marker. Don't move or rename it.
- The plugin reads this file every time you run `/blog-start`, `/blog`, or `/publish`.
- If anything moves on disk, re-run `/4d-blog-engine:blog-init` to update the paths.
```

Write the file at `<BLOG_PROJECT_DIR>/blog-project-instructions.md`.

## STEP 8 — Create the Posts/ subdirectory

If `<BLOG_PROJECT_DIR>/Posts/` doesn't exist, create it with Bash:

```bash
mkdir -p "<BLOG_PROJECT_DIR>/Posts"
```

## STEP 9 — Sanity-check the repo's posts and images folders

For each of `POSTS_SUBFOLDER` and `IMAGES_SUBFOLDER`, test whether the path exists inside `GITHUB_REPO_DIR`. If either is missing, ask:

> *`<subfolder>` doesn't exist inside `<GITHUB_REPO_DIR>` yet. Create it now? (Some site generators expect it to exist; others auto-create on first post. Pick "yes" if unsure.)*

On yes, `mkdir -p` the path. On no, leave it; `/publish` will fail clearly later if the folder is required.

## STEP 10 — Report back to the user

End the skill with a summary:

```
Blog project initialized.

  Blog project dir:     <BLOG_PROJECT_DIR>
  GitHub repo:          <GITHUB_REPO_DIR>
  Posts → repo path:    <GITHUB_REPO_DIR>/<POSTS_SUBFOLDER>
  Images → repo path:   <GITHUB_REPO_DIR>/<IMAGES_SUBFOLDER>
  Live URL pattern:     <LIVE_URL_PATTERN or "(not set)">
  Author:               <AUTHOR_NAME>

Instructions file written: <BLOG_PROJECT_DIR>/blog-project-instructions.md

Next steps:
  1. Open a fresh Cowork session inside <BLOG_PROJECT_DIR>.
     (Or stay here — but blog-start works best in a session rooted at your blog dir.)
  2. Run /4d-blog-engine:blog-start to confirm the plugin sees your project.
  3. Run /4d-blog-engine:blog <path-to-your-base-document> to write your first post.

If anything's wrong above, re-run /4d-blog-engine:blog-init — it'll keep your previous answers as defaults.
```

## What this skill does NOT do

- It does not install the plugin. The user already did that to reach this command.
- It does not write to the GitHub repo. Only `<BLOG_PROJECT_DIR>/blog-project-instructions.md` and (optionally, with the user's nod) the `Posts/` subdirectory inside the blog project dir.
- It does not validate that the GitHub repo has a remote that the user can push to. That check belongs in `/publish`.
- It does not run the discovery walk that the orchestrator uses. It just writes the marker file the walk looks for.

## Degradation behaviors

- **`mkdir -p` fails** (permission denied, full disk): surface the error and halt. Don't try to write the instructions file elsewhere.
- **User picks an existing path that has a different layout than expected** (e.g., already contains a Posts/ folder with old content): just use it. The plugin doesn't reorganize anything that's already there.
- **Bash is unavailable** (extremely rare in Cowork): fall back to plain Read/Write checks and ask the user to confirm paths manually.
- **GitHub remote URL is `git@github.com:...` rather than `https://...`**: store as-is. Both work for `git push`.
