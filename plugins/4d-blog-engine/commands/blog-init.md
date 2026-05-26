---
description: One-time setup. Tell the plugin where your blog project lives, where its GitHub repo is, and where new posts go inside that repo.
argument-hint: (no arguments — runs interactively)
allowed-tools: [Read, Write, AskUserQuestion, Bash, Glob]
---

# /4d-blog-engine:blog-init — one-time blog project setup

Invoke the `blog-init` skill. It walks you through three or four short questions and writes a single `blog-project-instructions.md` file to the top of your blog project directory. After that, `/4d-blog-engine:blog-start` will know how to find your project, and `/4d-blog-engine:publish` will know how to ship a finished post to your live site.

This command only needs to run once per blog project. If you need to change anything later, re-run it — it'll preserve your existing answers as defaults.

The four questions:

1. **Blog project directory.** The folder where the plugin writes drafts, hero images, slop reports, and signed posts. If you don't have one yet, the skill suggests creating `~/Documents/MyBlog/` (or similar) and helps you make it.
2. **GitHub repo for publishing.** The local clone of the GitHub repo your live site is built from. Usually under `~/Documents/GitHub/<your-blog-repo>/`. The plugin reads its `.git/config` to confirm there's a remote — if not, it stops and tells you to clone the repo first.
3. **Posts folder inside the repo.** Where finished posts land. Default `content/blog/` (Hugo). Jekyll users override to `_posts/`, Astro to `src/content/blog/`.
4. **Images folder inside the repo.** Where hero images land. Default `static/images/blog/`.
5. **Live site URL pattern, optional.** Used after `/publish` to preview the live URL. Example: `https://myblog.com/{YYYY}/{MM}/{slug}/`. Skip if you don't know it — `/publish` will still work, you just won't see a predicted link.

After the skill writes the file, it tells you how to verify the setup (start a fresh session, run `/4d-blog-engine:blog-start`, confirm the plugin reports your project).

Read `skills/blog-init/SKILL.md` for the full flow.
