---
description: Prepare a signed blog post for publish. The plugin auto-commits with the Summary + Description filled in. You click "Push origin" in GitHub Desktop to deploy.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob, mcp__cowork__request_cowork_directory, mcp__cowork__allow_cowork_file_delete]
---

# /4d-blog-engine:publish — prepare the commit; you click Push

Invoke the `publish` skill. Takes a Phase-4-signed post, applies the typographer's-quote transform, normalizes status to `published`, bumps `dateModified` to today, copies the post + hero into the GitHub repo's `content/blog/` and `public/blog-hero/` folders (or your generator's equivalents), and creates a commit with an **auto-generated Summary and Description**. The writer doesn't write the commit message.

After the commit is prepared, you click GitHub Desktop's **"Push origin"** button. One click. That's it.

**The piece directory is the draft.** Every blog starts in draft state — that's the file at `<blog-project-dir>/Posts/<slug>/04-diligence/blog.md`, which Phase 4 sign-off copies to a clean handoff at `<blog-project-dir>/drafts/<slug>.md`. The writer reviews and refines from `drafts/`.

`/publish` is the one and only repo-write operation. No `--draft` flag, no `content/draft/` folder in the repo, no token configuration.

**Argument:**

- `$1` — the piece slug, e.g., `2026-05-26-my-post`. If omitted, the skill picks the most recently signed-but-not-yet-published piece. If there are several, it asks.

**What the skill does:**

1. Verifies Phase 4 signed (`Verified — <initials>, <date>` in `changelog.md`).
2. Mounts the publishing repo if it isn't already (no mid-flow friction).
3. Auto-detects the posts and images subfolders inside the repo (Hugo's `content/blog/`, Jekyll's `_posts/`, Next.js's `public/blog-hero/`, etc.).
4. Applies the typographer's-quote transform reliably via the vendored `scripts/smart_quotes.py` — YAML frontmatter and JSON-LD `<script>` blocks are preserved verbatim.
5. Normalizes the post's `status:` to `published`.
6. Bumps `dateModified` to today (so byte-identical republishes still create a real diff and fire the site rebuild).
7. Rewrites the hero image reference in the frontmatter to its in-repo path.
8. Copies post + hero into the repo.
9. Runs `git add` + `git commit` with auto-generated Summary (`Publish: <title>`) and Description (a structured body naming the files, status, slug).
10. Reports the prepared commit and tells you to click "Push origin" in GitHub Desktop.

**What the skill never does:**

- Publish an unsigned post (use `--force` only if you really know what you're doing).
- Push to the remote — GitHub Desktop does that. Plugin only prepares the commit.
- Open a pull request — the commit targets the default branch directly.
- Configure any GitHub token / PAT / API auth — none needed; GitHub Desktop's existing auth handles the push.
- Modify the source post in `<piece>/04-diligence/blog.md` — the piece archive stays untouched.

**Lockfile recovery:** if GitHub Desktop's file-watcher races the commit (rare), the plugin silently recovers via `mcp__cowork__allow_cowork_file_delete` + `rm` + retry. Only after two failed silent retries will it ask you to quit GitHub Desktop briefly.

Read `skills/publish/SKILL.md` for the full workflow.
