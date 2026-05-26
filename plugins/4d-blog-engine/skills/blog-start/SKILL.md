---
name: blog-start
description: |
  This skill should be used when the user runs /4d-blog-engine:blog-start or asks any variant of "open my blog project," "resume my blog work," "start a blog session," "what's in progress on the blog," or "load the blog plugin." It locates the user's blog-project-instructions.md marker file, mounts the two declared directories (blog project + GitHub repo), surfaces in-progress and unpublished pieces, and proposes the next step. Do NOT use this skill for: first-time setup (use /4d-blog-engine:blog-init), running the pipeline (use /4d-blog-engine:blog), or publishing (use /4d-blog-engine:publish).
allowed-tools: [Read, Glob, Grep, Bash, AskUserQuestion]
---

# Blog-Start — open or resume a blog session

> **Read this when:** the user runs `/4d-blog-engine:blog-start`. Your job is to find the marker file, mount the two directories, surface state, and propose the next action.

## STEP 1 — Find the blog-project-instructions.md marker

Walk up from the current working directory looking for `blog-project-instructions.md` at any ancestor's root. Use Bash:

```bash
find_blog_project() {
  local d="$PWD"
  while [ "$d" != "/" ]; do
    if [ -f "$d/blog-project-instructions.md" ]; then
      echo "$d"
      return 0
    fi
    d="$(dirname "$d")"
  done
  echo ""
  return 1
}
BLOG_PROJECT_DIR=$(find_blog_project)
```

If the walk finds nothing, also check the standard fallback locations (in order):

1. `~/Documents/MyBlog/blog-project-instructions.md`
2. `~/Blog/blog-project-instructions.md`
3. `$HOME/4d-blog-engine-work/blog-project-instructions.md`

If still nothing, halt with:

> *No blog project found. I walked up from the current directory and checked the standard locations but didn't find a `blog-project-instructions.md` file. Run `/4d-blog-engine:blog-init` first to set up your blog project.*

If exactly one is found, proceed. If multiple are found at different fallback locations, ask the user which to use via `AskUserQuestion`.

## STEP 2 — Read the marker file

Read `<BLOG_PROJECT_DIR>/blog-project-instructions.md` in full. Extract from the "Project Setup" section:

- `BLOG_PROJECT_DIR` (confirm matches the walk's result)
- `GITHUB_REPO_DIR`
- `POSTS_SUBFOLDER`
- `IMAGES_SUBFOLDER`
- `LIVE_URL_PATTERN`
- `AUTHOR_NAME`

If the file's schema version (`schema:` field in frontmatter) is unknown to this plugin version, warn the user but proceed with best-effort parsing.

## STEP 3 — Mount both directories in Cowork

Use the Cowork directory-mount tool (`mcp__cowork__request_cowork_directory`) once for each path:

1. `BLOG_PROJECT_DIR`
2. `GITHUB_REPO_DIR`

The user approves each mount in Cowork. If a mount is already active, the tool reports that and continues without prompting.

If running outside Cowork (e.g., Claude Code CLI), the file tools (Read/Write/Edit/Glob/Grep) already have host-level access — the mount step is a no-op there. Detect this gracefully: if the mount tool isn't available, skip it and continue.

## STEP 3.5 — Voice file inventory

Glob `<BLOG_PROJECT_DIR>/*-voice.md` to enumerate voice files. The set determines what's shown to the writer:

- **Zero voice files:** flag this in the briefing. The pipeline can't write a post without a voice profile. The "What to do next" prompt should lead with *"Run `/4d-blog-engine:blog-voice` to capture your voice."*
- **One voice file:** record its path as `SELECTED_VOICE_FILE` silently. Mention it on a single line in the briefing as the active voice. No question asked.
- **Two or more voice files:** list them in the briefing with the author name pulled from each file's frontmatter, but do not auto-pick. The "What to do next" prompt for a `/blog` action will ask which voice to use at that point (the orchestrator handles this at pipeline STEP 0). This skill just surfaces the available voices.

Capture the count and the author-name list in `VOICE_FILES_AVAILABLE` for use in STEP 5.

## STEP 4 — Scan for in-progress pieces

List `<BLOG_PROJECT_DIR>/Posts/`. For each piece subdirectory:

```bash
ls -1 "<BLOG_PROJECT_DIR>/Posts/" 2>/dev/null
```

For each piece, read `<piece>/state.md` if present. Capture:

- `slug` (from frontmatter)
- `title` (from frontmatter)
- `current_phase` (01 / 02 / 03 / 04 / done)
- `gates_passed` (list)
- Last modification timestamp of `state.md`

Bucket the pieces into three categories:

- **In-progress** — `gates_passed` does not include `04` (Phase 4 not yet signed)
- **Signed but not yet published** — `04` is in `gates_passed`, AND `<piece>/04-diligence/blog.md` exists, AND there's NO file at `<GITHUB_REPO_DIR>/<POSTS_SUBFOLDER>/<slug>.md` (check with Glob)
- **Published** — `04` in `gates_passed`, AND the post file exists in the GitHub repo

Sort each bucket by `state.md` mtime descending (most recent first).

## STEP 5 — Display the briefing

Compose a structured briefing to the user. Skip empty sections.

```
Blog session ready.

Project:               <BLOG_PROJECT_DIR>
Publishing repo:       <PUBLISHING_REPO_DIR>
Live URL pattern:      <LIVE_URL_PATTERN or "(not set)">
Default author:        <AUTHOR_NAME>

Voices available:
  <If 0 voice files:>
    None yet — run /4d-blog-engine:blog-voice before /blog.
  <If 1 voice file:>
    • <author-name-from-frontmatter> (<filename>)
  <If 2+ voice files:>
    • <author-1> (<filename-1>)
    • <author-2> (<filename-2>)
    ... (the pipeline will ask which voice to use when you start writing)

In-progress pieces (most recent first):
  • <slug-1>  —  Phase <N>, gates passed [<list>]  —  last touched <date>
  • <slug-2>  —  …
  (or "None")

Signed but not yet published:
  • <slug-3>  —  signed <date>
  (or "None")

Recently published (last 5):
  • <slug-4>  —  in <GITHUB_REPO_DIR>/<POSTS_SUBFOLDER>/<slug-4>.md
  (or "None")
```

## STEP 6 — Propose the next step

Use `AskUserQuestion` with options pulled from the briefing in this priority order:

1. **If signed-but-not-published exists:** lead with *"Publish `<most-recent-signed-slug>` to your live site"* (runs `/4d-blog-engine:publish <slug>`).
2. **If in-progress exists:** offer *"Resume `<most-recent-in-progress-slug>` at Phase <N>"* (runs the appropriate phase command).
3. **Always:** offer *"Start a new piece"* (prompts for a base doc, then runs `/4d-blog-engine:blog`).
4. **Always:** offer *"Just looking — exit"* so the user can stop without picking.

Cap the question at four options. If there are more than two in-progress or signed pieces, only surface the most recent and note in the prompt body that older pieces exist (user can ask explicitly).

## STEP 7 — Hand off

When the user picks, route to the appropriate command. For publish, format the invocation: `/4d-blog-engine:publish <slug>`. For resume, route to the matching phase command. For new, prompt for the base doc path and then call `/4d-blog-engine:blog`.

If the user picks "just looking — exit," report cleanly and stop.

## What this skill does NOT do

- It does not write any files. Read-only briefing.
- It does not run the discovery walk that the orchestrator skill (`4d-blog-engine`) uses during pipeline runs. That walk is in the orchestrator's STEP 1. This skill uses a simpler walk because at session-start the user hasn't necessarily told us a piece slug yet.
- It does not validate the GitHub repo. That's `/publish`'s job at publish time.

## Degradation behaviors

- **`Posts/` directory missing entirely:** report "No `Posts/` directory yet — your first `/4d-blog-engine:blog` run will create it." Then go straight to the "start a new piece" prompt.
- **A piece directory has no `state.md`:** skip it silently. Likely an aborted run; the user can clean up manually.
- **GitHub repo path is invalid or moved:** report the failure, recommend re-running `/4d-blog-engine:blog-init` to update paths. Don't halt the briefing — in-progress writing work can continue without the repo being reachable.
- **The mount tool isn't available** (CLI-only environment): silently skip the mount step. The file tools already have host access there.
