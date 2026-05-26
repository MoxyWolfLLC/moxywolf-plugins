---
description: Ship a signed blog post to your live site. Copies post + hero into your blog's GitHub repo, commits, and pushes — so the site rebuild fires automatically.
argument-hint: <piece-slug>
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob]
---

# /4d-blog-engine:publish — ship a signed post to your live site

Invoke the `publish` skill. The skill takes a signed piece (Phase 4 passed, changelog signed by hand) and ships it to your live site via the GitHub repo you declared in `/4d-blog-engine:blog-init`.

You never write a commit message. You never type a git command. You see a confirmation dialog and a "pushed" message.

**Arguments:**

- `$1` — the piece slug, e.g., `2026-05-26-how-ai-changes-marketing`. Match the folder name under `<blog-project-dir>/Posts/`. If omitted, the skill picks the most recently signed-but-not-yet-published piece. If there isn't one, it lists candidates and asks.

**What the skill does, end to end:**

1. Verifies the piece passed Phase 4 (`changelog.md` contains a `Verified — <initials>, <YYYY-MM-DD>` line).
2. Reads `blog-project-instructions.md` for the repo path, posts subfolder, images subfolder, and live URL pattern.
3. Validates the GitHub repo (it's a real git repo, has a remote, the working tree is clean).
4. Stages the post + hero image with a destination preview.
5. Asks you to `Cmd+Q` GitHub Desktop (its file-watcher conflicts with multi-file writes).
6. Copies files, rewrites the image reference in the post's frontmatter to point to the new in-repo path, and runs `git add` + `git commit` + `git push` against the default branch.
7. Reports the GitHub commit URL and (if you configured a live URL pattern) the predicted live URL.
8. Marks the piece as published in its `state.md`.

**What the skill never does:**

- Push a piece that hasn't signed Phase 4. The Release Owner Gate is the prerequisite, not a suggestion.
- Run on a dirty working tree without explicit confirmation. If your blog repo has uncommitted edits unrelated to this post, the skill stops and asks before mixing them into the publish commit.
- Auto-resolve git conflicts. If the push is rejected because your local is behind the remote, the skill stops and tells you to pull/sync in GitHub Desktop, then retry.

Read `skills/publish/SKILL.md` for the full workflow.
