---
name: publish
description: |
  This skill should be used when the user runs /4d-blog-engine:publish or asks any variant of "publish this post," "ship the blog," "push the post to my site," "deploy the post," "get this on the live site." It takes a Phase-4-signed post (staged as a clean draft at <blog-project-dir>/drafts/<slug>.md by the sign-off step), applies a reliable typographer's-quote transform via scripts/smart_quotes.py (preserves YAML frontmatter and JSON-LD verbatim), normalizes status to published, bumps dateModified to today, and pushes the post + hero into the user's GitHub repo via the GitHub MCP push_file API (two API calls, hero first then post). No bash git, no GitHub Desktop coordination, no working-tree validation, no lockfile races — the writer's local clone (if any) is irrelevant to the publish. The local drafts/ folder is the draft state — there is no --draft flag and no content/draft/ folder in the publishing repo. /publish always ships from drafts/ to content/blog/ with status=published. The user sees a one-line confirmation and a success message; no git words. Do NOT use this skill for: running the pipeline (use /4d-blog-engine:blog), publishing unsigned posts without --force (refuse), or pushing to anywhere other than the configured publishing repo.
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob, mcp__cowork__request_cowork_directory, mcp__417094ff-ba6a-4250-85fd-94569f9872e6__push_file, mcp__417094ff-ba6a-4250-85fd-94569f9872e6__list_branches]
---

# Publish — ship a signed post to the writer's blog

> **Read this when:** the user runs `/4d-blog-engine:publish [<slug>]`. Your job is to take a Phase-4-signed piece, copy its publication-ready files into the configured publishing repo with the typographer's-quote transform applied correctly, normalize status to `published`, and push to the default branch — without making the writer type a single git command and without the YAML-breaking quote bug.

## Design principles (read first)

1. **The writer never sees a git word, never sees GitHub Desktop mentioned, never picks a branch.** Push is automatic via the GitHub API. The plugin handles everything between "yes, publish" and "✓ done."
2. **Push via the GitHub MCP, not bash git.** Use `mcp__<github-mcp>__push_file` to commit files directly to the default branch. No bash git, no `.git/index.lock` races, no GitHub Desktop coordination. The writer's local clone (if they have one) may drift from origin after publish — that's fine; they can pull when they care, or never. Their local clone is not the source of truth, the GitHub remote is.
3. **The typographer's-quote transform is vendored, not improvised.** Use `scripts/smart_quotes.py` — it explicitly preserves YAML frontmatter and JSON-LD `<script>` blocks. Never write ad-hoc Python that touches the file's quote characters.
4. **The publishing repo must be reachable** — either mounted in the session so we can read `.git/config` to find the remote URL, or the writer supplies the remote URL directly. `blog-start` handles the mount; if missed, this skill mounts on demand.
5. **Source of truth is `<blog-project-dir>/drafts/<slug>.md`.** Phase 4 sign-off stages the signed post there as a clean writer-facing copy. `/publish` reads from `drafts/`, applies the transform, pushes to the GitHub repo's `content/blog/<slug>.md` with `status: published`. There is no `--draft` flag and no `content/draft/` folder in the publishing repo.

6. **The piece directory at `<blog-project-dir>/Posts/<slug>/` stays untouched.** Forensic archive (delegation, description, discernment, diligence artifacts).

7. **Byte-identical republish silently bumps `dateModified`.** Don't show the writer a dialog about "empty commit vs dateModified bump" — that's an implementation detail. Always pick: bump `dateModified` to today, transform, push. Site rebuild fires from the real diff.
5. **The post file in `<piece>/04-diligence/blog.md` is the source of truth.** Never re-edit it. The transform writes to the repo path; the source stays untouched.

## STEP 0 — Resolve the piece slug

If `$1` (the slug) was passed:

1. Verify `<BLOG_PROJECT_DIR>/Posts/<slug>/` exists.
2. Verify `<piece>/state.md` exists.

If `$1` was omitted:

1. Glob `<BLOG_PROJECT_DIR>/drafts/*.md` to enumerate signed-and-staged drafts.
2. Filter out drafts whose slug already exists in the publishing repo's posts folder (they've been published; you can still re-publish them by passing the slug explicitly).
3. **One unpublished candidate:** use it.
4. **Multiple candidates:** ask the user via `AskUserQuestion` which to publish.
5. **No candidates:** halt with: *"No drafts ready to publish. Sign a piece by completing Phase 4 first (`/4d-blog-engine:diligence`) — that stages a clean copy to `<blog-project-dir>/drafts/<slug>.md`."*

Store as `SLUG` and `PIECE_DIR = <BLOG_PROJECT_DIR>/Posts/<SLUG>`.

## STEP 1 — Read project config

Locate `blog-project-instructions.md` (walk up from PIECE_DIR; fall back to `<BLOG_PROJECT_DIR>/blog-project-instructions.md`). If missing, halt with: *"No `blog-project-instructions.md` found. Run `/4d-blog-engine:blog-init` first."*

Read it and extract:

- `BLOG_PROJECT_DIR`
- `PUBLISHING_REPO_DIR`
- `LIVE_URL_PATTERN` (may be empty)
- `AUTHOR_NAME`

The writer's marker file does not pin subfolders (per v0.3.x writer-first design). Detect them from the repo's content layout at publish time.

**Conceptual model:** Phase 4 sign-off stages the signed post at `<blog-project-dir>/drafts/<slug>.md` — that's the writer-facing draft file (clean, single, easy to find). The writer reviews and refines there if needed. `/publish` reads from `drafts/`, applies the transform, and ships to `content/blog/<slug>.md` in the publishing repo, status `published`. There's no `content/draft/` folder in the publishing repo and no `--draft` flag on `/publish` — the local `drafts/` folder IS the draft state.

**The audit-trail tradeoff (explicit by design):** `drafts/<slug>.md` is editable. If the writer fixes a typo, a broken link, or a small phrasing tweak in `drafts/` after Phase 4 signed, that change ships when `/publish` runs — and it does NOT propagate back to `Posts/<slug>/04-diligence/blog.md`. So the forensic archive shows "what the Release Owner Gate signed" and `drafts/` shows "what got published." For small polish, divergence is fine — the substantive content that passed the gate is still in the audit trail. For substantive edits, the framework's expectation is: go back to the pipeline, re-run Phase 3 or Phase 4, re-sign. Don't smuggle a structural rewrite past the gate through a post-sign-off `drafts/` edit.

```bash
# Posts folder — common static-site-generator conventions, priority order:
for posts_dir in "content/blog" "content/posts" "_posts" "src/content/blog" "src/content/posts" "posts"; do
  [ -d "$PUBLISHING_REPO_DIR/$posts_dir" ] && POSTS_SUBFOLDER="$posts_dir" && break
done

# Images folder:
for images_dir in "public/blog-hero" "public/images/blog" "static/images/blog" "assets/images/blog" "public/images" "static/images"; do
  [ -d "$PUBLISHING_REPO_DIR/$images_dir" ] && IMAGES_SUBFOLDER="$images_dir" && break
done
```

**Resolution rules:**

- **If both subfolders detected:** proceed.
- **If either detection fails:** ask via `AskUserQuestion` for the missing one, with the conventional defaults as options plus a "Custom — type the path" fallback.

Store the resolved choices in the writer's marker file under `## Publish paths (auto-detected)` so the next publish doesn't re-ask.

## STEP 2 — Reach the publishing repo (locally and via API)

We need two things from the repo:

- **Owner + repo name** — for the GitHub MCP push_file calls. Derived by parsing the `remote.origin.url` from the local clone's `.git/config`.
- **Default branch** — looked up via the GitHub API.

If the local clone is mounted in this session, read the remote URL directly from `<PUBLISHING_REPO_DIR>/.git/config`:

```bash
ls "$PUBLISHING_REPO_DIR/.git" >/dev/null 2>&1 && echo "mounted" || echo "not_mounted"
```

If `not_mounted`, call `mcp__cowork__request_cowork_directory` with `PUBLISHING_REPO_DIR` as the `path` argument. The writer approves the mount. Continue once mounted.

If mount fails, fall back: ask the writer once via `AskUserQuestion` for the GitHub URL of their repo (`https://github.com/<owner>/<repo>`). Parse owner + repo from that. Store both in the marker file so we don't re-ask.

Parse the remote URL into owner + repo:

```bash
REMOTE_URL=$(grep -E "^\s*url\s*=" "$PUBLISHING_REPO_DIR/.git/config" | head -1 | sed 's/.*=//; s/^[[:space:]]*//')
# Handles both git@github.com:owner/repo.git and https://github.com/owner/repo[.git]
OWNER=$(echo "$REMOTE_URL" | sed -E 's@^git@github\.com:@@; s@^https?://github\.com/@@; s@/.*$@@')
REPO=$(echo "$REMOTE_URL" | sed -E 's@.*github\.com[:/]@@; s@\.git$@@' | cut -d/ -f2)
```

Store as `OWNER` and `REPO`.

## STEP 3 — Verify Phase 4 signed (or --force)

Read `<PIECE_DIR>/changelog.md`. Search for a line matching:

```
Verified — <initials>, <YYYY-MM-DD>
```

The date must be today or earlier.

- **If the line exists:** proceed.
- **If missing AND `--force` flag NOT passed:** halt with *"Piece `<SLUG>` has not been signed. Run `/4d-blog-engine:diligence` and complete the Release Owner sign-off, or pass `--force` to publish anyway (not recommended)."*
- **If missing AND `--force` passed:** proceed but record `forced: true` in the changelog log entry.

Also verify `<BLOG_PROJECT_DIR>/drafts/<SLUG>.md` exists. If not, halt: *"Staged draft missing at `<blog-project-dir>/drafts/<SLUG>.md`. Re-run `/4d-blog-engine:diligence` to re-stage from the signed Phase 4 artifact."*

Store the source path as `DRAFT_PATH = <BLOG_PROJECT_DIR>/drafts/<SLUG>.md`.

## STEP 4 — Read post + extract title and hero ref

Read `$DRAFT_PATH`. Parse the frontmatter (YAML between leading `---` lines). Extract:

- `title` — for the commit message
- Hero image reference (check `og_hero`, `hero_image`, `image`, `cover` fields, in that priority order). The value is typically a relative filename like `og-hero.png` — we'll rewrite it to the in-repo path.

If no title, halt. Don't invent.

If no hero image reference in frontmatter, scan the first 20 lines of body for an inline `![<alt>](og-hero.png)` pattern. If found, treat that as the hero ref and we'll rewrite the inline path too. If still not found, warn but don't halt — some templates render the hero from a fixed convention based on the slug.

## STEP 5 — Look up the default branch via GitHub API

Use the GitHub MCP to resolve the repo's default branch (no local git needed):

```
mcp__<github>__list_branches with branch_name="HEAD" (or use list_repos to get default_branch)
```

If MCP returns `main`, use `main`. If `master`, use `master`. Other defaults are rare but accept whatever the API reports.

If the API call fails (no token, network issue), fall back: read `.git/refs/remotes/origin/HEAD` from the local clone if available; otherwise default to `main` and proceed.

Store as `DEFAULT_BRANCH`.

**No working-tree validation.** The local clone's working-tree state is irrelevant — we're not pushing from it. The writer's local clone might have uncommitted unrelated changes; those stay where they are. The plugin pushes only the publish content via the API.

## STEP 6 — Compute destination paths and stage the publish plan

```
DEST_POST = <PUBLISHING_REPO_DIR>/<POSTS_SUBFOLDER>/<SLUG>.md
DEST_HERO = <PUBLISHING_REPO_DIR>/<IMAGES_SUBFOLDER>/<SLUG>.png
```

Check whether either already exists:

- **If neither exists:** new publish. Commit message: `Publish: <title>`.
- **If `DEST_POST` already exists:** republish. Ask the writer to confirm overwrite: *"A previous version of `<title>` is already in the repo at `<DEST_POST>`. Overwrite (republish)?"* Commit message on accept: `Republish: <title>`.

Truncate the title in the commit subject to keep total subject ≤72 chars; add ellipsis if truncated.

If `LIVE_URL_PATTERN` is set in the marker file, compute the predicted live URL using `{slug}` substitution (and `{YYYY}` / `{MM}` / `{DD}` from the slug's leading date if present).

## STEP 7 — Show the publish plan and confirm

Display the plan to the writer. Keep it short and writer-shaped — no git words, no infrastructure leaks:

```
Ready to publish "<title>" to your live site.

  Source:        drafts/<SLUG>.md
  Repo:          <OWNER>/<REPO>
  Predicted URL: <computed URL or "(your site will pick it up on rebuild)">

Type "go" to publish, or "cancel" to stop.
```

Wait for the writer's reply. Accept "go" / "yes" / "publish" as confirmation. Anything else cancels.

(The plugin handles the push end-to-end via GitHub's API. No local repo coordination, no GitHub Desktop concerns — those are implementation details the writer doesn't need to think about.)

## STEP 8 — Run the typographer's-quote transform via the vendored script

Copy the source draft into a temp location, then apply the transform:

```bash
TMP=$(mktemp)
cp "$DRAFT_PATH" "$TMP"
python3 "$CLAUDE_PLUGIN_ROOT/scripts/smart_quotes.py" --in "$TMP" --in-place
```

If the script exits non-zero, halt with the script's stderr and tell the writer their draft may have malformed frontmatter — they should look at `$DRAFT_PATH`.

The transformed file at `$TMP` is what gets copied to the repo in STEP 9. The original at `<BLOG_PROJECT_DIR>/drafts/<SLUG>.md` is never modified — it remains as the canonical local draft, available for re-publish without going through Phase 4 again.

## STEP 9 — Normalize status, rewrite hero reference, copy files

Apply the status normalization in-memory (Python on the temp file):

- Find the `status:` field in the YAML frontmatter.
- Replace its value with `published`.
- If no `status:` field exists, insert `status: published` at the end of the frontmatter.

(The local `drafts/` folder is the draft state. `/publish` always ships to `published`.)

**Always bump `dateModified` to today.** This is what makes byte-identical republishes still produce a real diff (and trigger the site rebuild) without the writer needing to think about it.

- Find `dateModified:` in the YAML frontmatter. Replace with today's ISO date.
- If absent, insert `dateModified: <today YYYY-MM-DD>` at the end of the frontmatter.
- Also check inside any JSON-LD `<script>` block for a `dateModified` field (Schema.org BlogPosting); update that value too. The smart_quotes transform preserves the script block content, so a regex inside the JSON-LD region is safe.

Rewrite the hero image reference to its in-repo path. The repo's templates typically expect an absolute-from-repo-root path like `/blog-hero/<slug>.png`. Use:

```
/<IMAGES_SUBFOLDER_RELATIVE_TO_PUBLIC>/<SLUG>.png
```

Where `IMAGES_SUBFOLDER_RELATIVE_TO_PUBLIC` strips the `public/` prefix if the images dir starts with `public/` (Next.js convention — `public/blog-hero/x.png` is served at `/blog-hero/x.png`). For other generators, use the configured subfolder as-is.

Patterns to rewrite (in priority order in the frontmatter):

- `og_hero: og-hero.png` → `og_hero: /<resolved-path>`
- `hero_image: og-hero.png` → `hero_image: /<resolved-path>`
- `image: og-hero.png` → `image: /<resolved-path>`
- `cover: og-hero.png` → `cover: /<resolved-path>`

Also in body:

- `![<alt>](og-hero.png)` → `![<alt>](/<resolved-path>)`

Use Python on `$TMP` for this (not sed — sed can break on YAML edge cases). Embed the rewrite logic inline; it's straightforward.

Read the transformed file content into memory (will be passed to the GitHub MCP in STEP 10):

```bash
POST_CONTENT=$(cat "$TMP")
rm "$TMP"
```

For the hero image (binary PNG), base64-encode it for the API push:

```bash
HERO_B64=$(base64 < "$PIECE_DIR/04-diligence/og-hero.png" | tr -d '\n')
```

## STEP 10 — Push via the GitHub MCP

Two API calls — hero first (so the post's reference to it is valid in the second commit), then post:

**Call 1 — push the hero image:**

```
mcp__<github>__push_file with:
  owner: <OWNER>
  repo: <REPO>
  branch: <DEFAULT_BRANCH>
  path: <IMAGES_SUBFOLDER>/<SLUG>.png
  content: <HERO_B64>            (base64-encoded PNG bytes)
  message: "Publish hero: <title>"
```

Capture the returned commit SHA as `HERO_COMMIT_SHA`.

**Call 2 — push the post markdown:**

```
mcp__<github>__push_file with:
  owner: <OWNER>
  repo: <REPO>
  branch: <DEFAULT_BRANCH>
  path: <POSTS_SUBFOLDER>/<SLUG>.md
  content: <POST_CONTENT>        (UTF-8 markdown, transformed)
  message: <COMMIT_MESSAGE>      (e.g., "Publish: <title>")
```

Capture the returned commit SHA as `POST_COMMIT_SHA`. This is the commit URL shown to the writer.

**On `push_file` errors:**

- *"sha mismatch"* (file already exists with different content, push needs the existing blob's sha to update): re-fetch the existing file's sha via `read_file` or list_branches contents and retry the push_file call with the `sha` parameter.
- *"branch not found"*: halt and ask the writer to confirm the branch name — fallback list `main`, `master`, `production` via `AskUserQuestion`.
- *"401 / 403 unauthorized"*: halt with *"GitHub access isn't set up. Open Cowork → Settings → Connectors → GitHub and connect your account. Then re-run /4d-blog-engine:publish <slug>."* This is a one-time setup; after that publish works.
- *"network error"*: halt with the error, advise the writer to retry.

**Byte-identical content** (the file at `<POSTS_SUBFOLDER>/<SLUG>.md` on the remote has the same content we're pushing): push_file will silently no-op or return a "no change" indicator. In that case, the dateModified bump from STEP 9 normally already created a diff. If somehow we're still byte-identical (the dateModified was already today), surface a quiet note in the success report — the push went through but no actual diff resulted; site rebuild may not fire.

**Build the public commit URL** for the success message:

```
COMMIT_URL = https://github.com/<OWNER>/<REPO>/commit/<POST_COMMIT_SHA>
```

## STEP 11 — Update piece state

Append to `<PIECE_DIR>/state.md`:

```markdown
- [x] Published to live site (<published | draft>)
```

And to the process log:

```
<ISO-8601 now> — Published to <REMOTE_URL> branch <DEFAULT_BRANCH> at commit <SHORT_SHA>. Status: <published|draft>.
```

Update the state.md frontmatter:

- `published: <YYYY-MM-DD>`
- `published_commit: <short SHA>`
- `published_status: <published|draft>`

## STEP 12 — Report back

```
✓ Published "<title>".

Commit:  <COMMIT_URL>
Files:
  - <POSTS_SUBFOLDER>/<SLUG>.md
  - <IMAGES_SUBFOLDER>/<SLUG>.png

Predicted live URL: <computed URL or "(check your hosting dashboard for the actual URL)">

Your site rebuild should fire automatically from the push. Most static-site
hosting (GitHub Pages, Vercel, Netlify) takes 1-5 minutes.
```

## What this skill does NOT do

- It does not publish to LinkedIn. The LinkedIn artifacts live at `<PIECE_DIR>/04-diligence/linkedin-{article,teaser}.md` for you to paste by hand.
- It does not open a pull request. Direct push to default branch only.
- It does not delete the source draft at `<BLOG_PROJECT_DIR>/drafts/<SLUG>.md`. The draft stays as the canonical local copy. Re-running `/publish <slug>` re-publishes it.
- It does not delete files in `<PIECE_DIR>/04-diligence/`. The piece directory remains the forensic archive.
- It does not modify the writer's local clone of the publishing repo. The push is via GitHub's API; the local clone (if any) drifts from origin until the writer next fetches. The writer is free to ignore the local clone entirely.
- It does not trigger your site's rebuild. The push triggers your hosting webhook; nothing in this plugin touches the hosting.
- It does not rewrite source images. The hero PNG goes into the repo as-is.
- It does not modify the source post's quotes. The transform writes to the repo path; the source stays untouched.

## Degradation behaviors

- **`git` not available in the sandbox:** halt with a clear message. Rare.
- **Repo is on iCloud / Google Drive / Dropbox synced filesystem:** publish may work but expect lockfile races. Strongly recommend the writer move the repo to a non-synced local path (`~/Documents/GitHub/`). Don't refuse; flag it once and proceed.
- **Default branch detection fails** (no `origin/HEAD`): ask the writer whether to push to `main` or `master`. Don't assume.
- **smart_quotes.py exits with code 3 (malformed frontmatter):** halt and tell the writer their source post needs the frontmatter fixed before publish — show them the line.
- **Images folder doesn't exist and writer's site uses on-demand hero**: skip the hero copy if the IMAGES_SUBFOLDER detection found nothing AND no hero reference exists in frontmatter. Log it.
- **Status normalization fails** (unexpected YAML shape): surface the issue, ask whether to publish as-is or halt.
