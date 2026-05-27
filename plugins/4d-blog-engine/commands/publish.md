---
description: Ship a signed blog post to your live site. One command, one confirmation. The plugin commits and pushes for you — no git words, no GitHub Desktop, no commit messages to write.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob, mcp__cowork__request_cowork_directory, mcp__cowork__allow_cowork_file_delete]
---

# /4d-blog-engine:publish — ship a signed post

Invoke the `publish` skill. Takes a Phase-4-signed post and ships it to the GitHub repo you declared in `/blog-init`. The writer never types a git command, never writes a commit message, never picks a branch.

**The piece directory is the draft.** Every blog starts in draft state — that's the file at `<blog-project-dir>/Posts/<slug>/04-diligence/blog.md`. The writer reviews and refines it there. There's no "publish to draft" step because there's nothing to publish to: the draft already exists, locally, in the piece directory.

`/publish` is the one and only repo-write operation. It writes the signed post to `content/blog/<slug>.md` (or your generator's equivalent) with status `published`, copies the hero, commits, pushes.

**Argument:**

- `$1` — the piece slug, e.g., `2026-05-26-my-post`. If omitted, the skill picks the most recently signed-but-not-yet-published piece. If there are several, it asks.

**What the skill does:**

1. Verifies Phase 4 signed (`Verified — <initials>, <date>` in `changelog.md`).
2. Mounts the publishing repo if it isn't already (no mid-flow friction).
3. Auto-detects the posts and images subfolders inside the repo (Hugo's `content/blog/`, Jekyll's `_posts/`, Next.js's `public/blog-hero/`, etc.).
4. Applies the typographer's-quote transform reliably via the vendored `scripts/smart_quotes.py` — YAML frontmatter and JSON-LD `<script>` blocks are preserved verbatim.
5. Normalizes the post's `status:` to `published`.
6. Rewrites the hero image reference in the frontmatter to its in-repo path.
7. Copies post + hero to the repo.
8. Auto-generates the commit message (`Publish: <title>` or `Republish: <title>` on overwrite).
9. Runs `git add` + `git commit` + `git push` against the default branch.
10. Reports the GitHub commit URL and the predicted live URL.

**What the skill never does:**

- Publish an unsigned post (use `--force` only if you really know what you're doing).
- Push to anything other than the default branch.
- Modify the source post in `<piece>/04-diligence/blog.md` — the piece archive stays untouched.
- Open a pull request.
- Ask you to close GitHub Desktop, run a git command, or care about a local clone. The push happens via GitHub's API; your local clone (if you have one) drifts from origin until you next fetch.

**First-time setup (one-time):** the plugin needs a GitHub Personal Access Token wired into your Cowork MCP config to authenticate the push. If your first `/publish` attempt halts with a "GitHub push access isn't configured yet" message, the skill walks you through three short steps: generate a fine-grained PAT on github.com, paste it into your Cowork MCP server's config as `GITHUB_TOKEN`, and restart the session. After that, all publishes are silent. The PAT only needs **Contents: Read and write** scope on the specific repo you're publishing to.

Read `skills/publish/SKILL.md` for the full workflow.
