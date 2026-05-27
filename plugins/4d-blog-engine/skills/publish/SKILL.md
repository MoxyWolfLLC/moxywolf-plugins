---
name: publish
description: |
  This skill should be used when the user runs /4d-blog-engine:publish or asks any variant of "publish this post," "ship the blog," "push the post to my site," "deploy the post," "get this on the live site." It takes a Phase-4-signed post (staged as a clean draft at <blog-project-dir>/drafts/<slug>.md by the sign-off step), applies a reliable typographer's-quote transform via scripts/smart_quotes.py (preserves YAML frontmatter and JSON-LD verbatim), normalizes status to published, copies post + hero into the user's GitHub repo at the paths declared in blog-project-instructions.md, and runs git add/commit/push from the bash sandbox after the user closes GitHub Desktop. The local drafts/ folder is the draft state — there is no --draft flag and no content/draft/ folder in the publishing repo. /publish always ships from drafts/ to content/blog/ with status=published. The user never sees a git word; they see a confirmation dialog and a "pushed" message. Do NOT use this skill for: running the pipeline (use /4d-blog-engine:blog), publishing unsigned posts without --force (refuse), or pushing to anywhere other than the configured publishing repo.
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, Glob, mcp__cowork__request_cowork_directory]
---

# Publish — ship a signed post to the writer's blog

> **Read this when:** the user runs `/4d-blog-engine:publish [<slug>]`. Your job is to take a Phase-4-signed piece, copy its publication-ready files into the configured publishing repo with the typographer's-quote transform applied correctly, normalize status to `published`, and push to the default branch — without making the writer type a single git command and without the YAML-breaking quote bug.

## Design principles (read first — this skill regressed before because these weren't explicit)

1. **The writer never types a git word.** Commit message is auto-generated. Push is automatic on confirm. The only word the writer sees is "publish."
2. **The typographer's-quote transform is vendored, not improvised.** Use `scripts/smart_quotes.py` — it explicitly preserves YAML frontmatter and JSON-LD `<script>` blocks. Never write ad-hoc Python that touches the file's quote characters; that's what shipped broken YAML last time.
3. **The publishing repo must be mounted before this skill runs.** `blog-start` mounts both directories. If the writer skipped `blog-start` and the repo isn't mounted, this skill mounts it itself rather than failing.
4. **Source of truth is `<blog-project-dir>/drafts/<slug>.md`.** Phase 4 sign-off stages the signed post there as a clean writer-facing copy. `/publish` reads from `drafts/`, applies the transform, writes to the publishing repo's `content/blog/<slug>.md` with `status: published`. There is no `--draft` flag and no `content/draft/` folder in the publishing repo — the local `drafts/` folder is the draft state. `/publish` is the one and only repo-write operation.

5. **The piece directory at `<blog-project-dir>/Posts/<slug>/` stays untouched.** It's the forensic archive (delegation, description, discernment, diligence artifacts). The signed `<piece>/04-diligence/blog.md` is preserved as the source-of-truth pre-publish version; the `drafts/<slug>.md` copy is what /publish actually reads.
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

## STEP 2 — Mount the publishing repo if needed

The repo path comes from the marker file. Check whether it's accessible from this session:

```bash
ls "$PUBLISHING_REPO_DIR/.git" >/dev/null 2>&1 && echo "mounted" || echo "not_mounted"
```

If `not_mounted`, call `mcp__cowork__request_cowork_directory` with `PUBLISHING_REPO_DIR` as the `path` argument. The writer approves the mount. Continue once mounted.

If the mount fails (writer dismisses or path doesn't exist), halt with: *"Cannot reach the publishing repo at `<path>`. Re-run `/4d-blog-engine:blog-init` to update the path, or pick a different repo."*

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

## STEP 5 — Validate the publishing repo

Cheap Bash checks:

```bash
# Default branch
DEFAULT_BRANCH=$(git -C "$PUBLISHING_REPO_DIR" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH="main"  # safe fallback

# Working tree state
WORKING_STATUS=$(git -C "$PUBLISHING_REPO_DIR" status --porcelain)

# Remote URL for the success message
REMOTE_URL=$(git -C "$PUBLISHING_REPO_DIR" config --get remote.origin.url 2>/dev/null)
```

If the working tree has unrelated changes (`WORKING_STATUS` non-empty AFTER filtering for our destination paths), ask the writer:

> *Your blog repo has uncommitted changes unrelated to this post. Continue? The publish commit will only include the new post and hero — your other changes stay uncommitted in your working tree.*

If they decline, halt cleanly.

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

Display the plan to the writer:

```
About to publish "<title>" to your live site.

  Source:        <BLOG_PROJECT_DIR>/drafts/<SLUG>.md
  Hero:          <PIECE_DIR>/04-diligence/og-hero.png

  Will write:    <DEST_POST>
                 <DEST_HERO>

  Repo:          <REMOTE_URL>
  Branch:        <DEFAULT_BRANCH>
  Commit:        <commit-subject>
  Predicted URL: <computed URL or "(no pattern set)">

Heads up: please Cmd+Q GitHub Desktop NOW if it's open.
Type "go" to publish, or "cancel" to stop.
```

Wait for the writer's reply. Accept "go" / "yes" / "publish" as confirmation. Anything else cancels.

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

Then copy files:

```bash
mkdir -p "$(dirname "$DEST_POST")"
mkdir -p "$(dirname "$DEST_HERO")"
cp "$TMP" "$DEST_POST"
cp "$PIECE_DIR/04-diligence/og-hero.png" "$DEST_HERO"
rm "$TMP"
```

## STEP 10 — Commit and push

```bash
git -C "$PUBLISHING_REPO_DIR" add "$POSTS_SUBFOLDER/$SLUG.md" "$IMAGES_SUBFOLDER/$SLUG.png"
git -C "$PUBLISHING_REPO_DIR" commit -m "$COMMIT_MESSAGE" --no-verify
git -C "$PUBLISHING_REPO_DIR" push origin "$DEFAULT_BRANCH"
```

Capture exit codes and stderr from each command.

**If `git commit` fails** with "nothing to commit": surface "Nothing to publish — the files are byte-identical to what's already on GitHub. If you meant to republish, edit the post first." Halt cleanly.

**If `git push` fails because local is behind remote:** halt with *"Push rejected — your local repo is behind the remote. Open GitHub Desktop, click Fetch / Pull to sync, then re-run `/4d-blog-engine:publish <SLUG>`."*

**Any other push failure:** surface full stderr, halt.

**Stale lockfile recovery:** if any `git` call returns *"fatal: Unable to create '.../.git/index.lock': File exists"*, call `mcp__cowork__allow_cowork_file_delete` for the lockfile path, `rm -f` it, retry the failing command. If retry still fails, halt and tell the writer to delete the lockfile manually from Finder.

**Capture the commit SHA** for the success message:

```bash
COMMIT_SHA=$(git -C "$PUBLISHING_REPO_DIR" rev-parse --short HEAD)
COMMIT_URL=$(echo "$REMOTE_URL" | sed -E 's@^git@@github\.com:@https://github.com/@; s@\.git$@@')/commit/$COMMIT_SHA
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
Status:  <published | draft>
Files:
  - <POSTS_SUBFOLDER>/<SLUG>.md
  - <IMAGES_SUBFOLDER>/<SLUG>.png

Predicted live URL: <computed URL or "(check your hosting dashboard for the actual URL)">

Your site rebuild should fire automatically from the push. Most static-site
hosting (GitHub Pages, Vercel, Netlify) takes 1-5 minutes.

It's safe to reopen GitHub Desktop now.
```

## What this skill does NOT do

- It does not publish to LinkedIn. The LinkedIn artifacts live at `<PIECE_DIR>/04-diligence/linkedin-{article,teaser}.md` for you to paste by hand.
- It does not open a pull request. Direct push to default branch only.
- It does not delete the source draft at `<BLOG_PROJECT_DIR>/drafts/<SLUG>.md`. The draft stays as the canonical local copy. Re-running `/publish <slug>` re-publishes it.
- It does not delete files in `<PIECE_DIR>/04-diligence/`. The piece directory remains the forensic archive.
- It does not run `git pull` for you. If push is rejected, the writer resolves it in GitHub Desktop.
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
