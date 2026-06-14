---
description: Prepare a signed blog post for publish. The plugin auto-commits with the Summary + Description filled in. You click "Push origin" in GitHub Desktop to deploy.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob, mcp__cowork__request_cowork_directory, mcp__cowork__allow_cowork_file_delete]
---

# /4d-blog-engine:blog-publish — prepare the commit; you click Push

Invoke the `publish` skill. Takes a Phase-4-signed post, applies the typographer's-quote transform, normalizes status to `published`, bumps `dateModified` to today, copies the post + hero into the GitHub repo's `content/blog/` and `public/blog-hero/` folders (or your generator's equivalents), and creates a commit with an **auto-generated Summary and Description**. The writer doesn't write the commit message.

After the commit is prepared, you click GitHub Desktop's **"Push origin"** button. One click. That's it.

**The piece directory is the draft.** Every blog starts in draft state — that's the file at `<blog-project-dir>/Posts/<slug>/04-diligence/blog.md`, which Phase 4 sign-off copies to a clean handoff at `<blog-project-dir>/drafts/<slug>.md`. The writer reviews and refines from `drafts/`.

`/blog-publish` is the one and only repo-write operation. No `--draft` flag, no `content/draft/` folder in the repo, no token configuration.

**Argument:**

- `$1` — the piece slug, e.g., `2026-05-26-my-post`. If omitted, the skill picks the most recently signed-but-not-yet-published piece. If there are several, it asks.

**What the skill does:**

1. Verifies Phase 4 signed (`Verified — <initials>, <date>` in `changelog.md`).
2. Mounts the publishing repo if it isn't already (no mid-flow friction).
3. Auto-detects the posts, images, media, and social subfolders inside the repo (Hugo's `content/blog/`, Next.js's `public/blog-hero/`, `public/blog-media/`, `content/blog/social/`, etc.).
4. Applies the typographer's-quote transform reliably via the vendored `scripts/smart_quotes.py` — YAML frontmatter and JSON-LD `<script>` blocks are preserved verbatim.
5. Normalizes the post's `status:` to `published`.
6. Bumps `dateModified` to today (so byte-identical republishes still create a real diff and fire the site rebuild).
7. Rewrites the hero image reference in the frontmatter to its in-repo path.
8. **Parses the `media:` array in the YAML frontmatter** and copies each referenced file from `<blog-project-dir>/drafts/blog-media/<basename>` to the repo's `public/blog-media/<basename>`. Creates `public/blog-media/` if it doesn't exist. Halts pre-flight if any referenced media file is missing from `drafts/blog-media/`.
9. **If `/blog-social` has been run for this piece**, detects the social derivatives at `<piece>/04-diligence/social/` (LinkedIn article + teaser, Twitter thread, Facebook post, plus scorecards) and ships them to the repo at `<social-subfolder>/<slug>/` — defaulting to `content/blog/social/<slug>/` if no existing convention is detected. Rewrites each social file's `source_blog:` frontmatter to the in-repo path of the published post so downstream distribution automation resolves cleanly. If no social derivatives exist, the social step is silently skipped — no warning, no flag, same behavior as pre-v0.9.
10. Copies post + hero + media + social into the repo.
11. **Registers the spoke in the pillar's linking map** (hub-and-spoke upkeep): adds the post to the pillar's spoke inventory, ensures the spoke→hub link on the pillar's `hub_term` (held if the hub page isn't live yet), and includes the updated linking map in the same commit. See STEP 9b in the skill.
12. Runs `git add` + `git commit` with auto-generated Summary (`Publish: <title>`) and Description (a structured body naming the files, media, social bundle, status, slug).
13. Reports the prepared commit and tells you to click "Push origin" in GitHub Desktop.

**How media files work:** drop any non-hero attachments (spreadsheets, PDFs, audio, etc.) into `<blog-project-dir>/drafts/blog-media/`. Reference them in your post's YAML as:

```yaml
media:
  - file: /blog-media/your-file.xlsx
    caption: "Short description shown alongside the download link"
```

The plugin handles copy + commit + create-the-dir-if-missing automatically.

**How social derivatives work (new in v0.9):** run `/4d-blog-engine:blog-social` *after* Phase 4 sign-off to generate the LinkedIn / Twitter / Facebook source files. Then re-run `/4d-blog-engine:blog-publish <slug>` — the social bundle gets included in the same commit as the post. Re-running publish after social adds the social files to the repo; the post itself is treated as a republish (the `dateModified` bump fires the site rebuild). If you don't want social on a piece, just don't run `/blog-social` — publish stays post-only with no warning.

**What the skill never does:**

- Publish an unsigned post (use `--force` only if you really know what you're doing).
- Post to LinkedIn, Twitter, or Facebook on your behalf. The skill ships the source files into the repo; the paste-and-post step on each platform stays manual, by design.
- Push to the remote — GitHub Desktop does that. Plugin only prepares the commit.
- Open a pull request — the commit targets the default branch directly.
- Configure any GitHub token / PAT / API auth — none needed; GitHub Desktop's existing auth handles the push.
- Modify the source post in `<piece>/04-diligence/blog.md` — the piece archive stays untouched.

**Lockfile recovery:** if GitHub Desktop's file-watcher races the commit (rare), the plugin silently recovers via `mcp__cowork__allow_cowork_file_delete` + `rm` + retry. Only after two failed silent retries will it ask you to quit GitHub Desktop briefly.

Read `skills/blog-publish/SKILL.md` for the full workflow.
