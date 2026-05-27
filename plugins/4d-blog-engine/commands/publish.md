---
description: Ship a signed blog post to your live site. One command, no git words required.
argument-hint: [<piece-slug>] [--draft]
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob, mcp__cowork__request_cowork_directory]
---

# /4d-blog-engine:publish — ship a signed post

Invoke the `publish` skill. Takes a Phase-4-signed post and ships it to the GitHub repo you declared in `/blog-init`. The writer never types a git command, never writes a commit message, never picks a branch.

**Arguments:**

- `$1` — the piece slug, e.g., `2026-05-26-my-post`. If omitted, the skill picks the most recently signed-but-not-yet-published piece. If there are several, it asks.
- `--draft` — optional. Ships at `status: draft` instead of the default `published`. Useful when your site has a staging environment that picks up drafts so you can preview before going live. Without the flag, the post goes live on push.

**What the skill does:**

1. Verifies Phase 4 signed (`Verified — <initials>, <date>` in `changelog.md`).
2. Mounts the publishing repo if it isn't already (no mid-flow friction).
3. Auto-detects the posts and images subfolders inside the repo (Hugo's `content/blog/`, Jekyll's `_posts/`, Next.js's `public/blog-hero/`, etc.).
4. Applies the typographer's-quote transform reliably via the vendored `scripts/smart_quotes.py` — YAML frontmatter and JSON-LD `<script>` blocks are preserved verbatim. The bug from the earlier hand-rolled Python script can't return.
5. Normalizes the post's `status:` to `published` (or `draft` with the flag).
6. Rewrites the hero image reference in the frontmatter to its in-repo path.
7. Copies post + hero to the repo.
8. Auto-generates the commit message (`Publish: <title>`).
9. Runs `git add` + `git commit` + `git push` against the default branch.
10. Reports the GitHub commit URL and the predicted live URL.

**What the skill never does:**

- Publish an unsigned post (use `--force` only if you know what you're doing).
- Push to anything other than the default branch.
- Modify the source post in `<piece>/04-diligence/blog.md` — the transform writes to the repo path; the piece archive stays untouched.
- Open a pull request.

**Heads-up the skill will surface during the publish confirmation:** Cmd+Q GitHub Desktop before the push. The Cowork sandbox's file watcher conflicts with GitHub Desktop and can leave a stale `.git/index.lock`.

Read `skills/publish/SKILL.md` for the full workflow.
