---
description: Adversarial review of just-committed code — real Codex when available, Claude fallback
allowed-tools: Read, Grep, Glob, Bash, AskUserQuestion
argument-hint: [--wait|--background] [--base <ref>] [commit-ref] [focus ...]
---

Run an **adversarial** review of code you just committed. This is a post-commit gate: where `/gstack-review` checks the whole branch before landing, this command challenges the *most recent commit* before you push.

It takes the best of OpenAI's Codex review plugin — the adversarial framing (challenge the approach, design, tradeoffs, and assumptions, not just hunt defects), the review-only discipline, and the smart scope/sizing logic — and runs it through a **hybrid engine**: real Codex when the `codex` CLI is present (genuine cross-model review, different blind spots), and a Claude-run adversarial pass using the same methodology when it isn't (e.g. the Cowork sandbox).

Read the gstack-execution skill for context. Then read `references/codex-review-methodology.md` for the full adversarial protocol — both engines use it as the single source of truth.

Raw slash-command arguments: `$ARGUMENTS`

## Core constraint — review-only

- This command **does not fix code**. No patches, no edits, no "I'll go fix that now."
- Its only job is to surface findings about the just-committed change.
- Keep the framing on whether this commit's approach is the right one, what it assumes, and where it breaks under real conditions. Defect-spotting is the floor, not the ceiling.

## Step 0: Resolve scope

Default scope is **the last commit** (the one you just made). Parse `$ARGUMENTS` to override:

- No scope flags → review `HEAD~1..HEAD` (the single most recent commit). If `HEAD` has no parent (first commit in the repo), review the full tree of `HEAD`.
- A bare commit ref or short SHA in the arguments (e.g. `a1b2c3d`) → review that commit (`<ref>~1..<ref>`).
- `--base <ref>` → review `<ref>..HEAD` (every commit since `<ref>` — use when you've stacked several commits and want them reviewed together before push).
- Any non-flag text after the flags is **focus text** — pass it through verbatim to sharpen the review (e.g. `challenge the retry design`, `look for race conditions in the queue worker`). Do not rewrite or soften it.

Run via Bash to establish scope and confirm there's something to review:

```bash
git rev-parse --abbrev-ref HEAD                      # current branch
git log -1 --format='%h %s'                          # the commit under review
git diff --shortstat HEAD~1..HEAD                    # size (adjust range per scope)
```

Only conclude "nothing to review" when the resolved range is genuinely empty. If the range is non-empty, proceed.

## Step 1: Execution mode (foreground vs background)

- If `$ARGUMENTS` contains `--wait` → run in the foreground, do not ask.
- If `$ARGUMENTS` contains `--background` → run as a background task, do not ask.
- Otherwise size the diff from Step 0 and decide:
  - Clearly tiny (roughly 1-2 files, no directory-sized change) → recommend **Wait**.
  - Anything larger, or unclear → recommend **Background**.
- Then call `AskUserQuestion` exactly once with two options, recommended option first and suffixed `(Recommended)`:
  - `Wait for results`
  - `Run in background`

When run in the background, tell the user to check back, and (if the real-Codex path is used) that `/codex:status` and `/codex:result` from the OpenAI plugin also track the job.

## Step 2: Detect the engine

Run via Bash:

```bash
command -v codex >/dev/null 2>&1 && echo "codex-present" || echo "codex-absent"
```

If `codex-present`, also check it's authenticated (a logged-out binary can't review):

```bash
codex login status 2>/dev/null && echo "codex-ready" || echo "codex-not-logged-in"
```

Decide the path:

- **`codex-ready`** → Step 3A (real Codex).
- **`codex-absent` or `codex-not-logged-in`** → Step 3B (Claude fallback). When not-logged-in, mention `codex login` once as the way to unlock real cross-model review next time, then proceed with the fallback — don't block.

The Cowork bash sandbox normally has no `codex` binary, so Step 3B is the expected path there. Real Codex is the expected path from Claude Code CLI on a Mac where `codex` is installed and logged in.

## Step 3A: Real Codex review

Construct an adversarial review prompt from `references/codex-review-methodology.md`, embedding the resolved commit range and any focus text, and hand it to Codex non-interactively:

```bash
codex exec "Review ONLY the git commit range <RANGE> in this repository. \
This is an adversarial, review-only pass — do not modify files or propose to apply patches. \
Challenge the implementation approach, design choices, tradeoffs, and hidden assumptions of this change, \
not just surface defects. <FOCUS_TEXT_IF_ANY>. \
For each finding give: severity (CRITICAL/INFO), file:line, what, why-it-matters, and a concrete fix. \
End with a one-line ship-readiness verdict."
```

- For the background mode, launch that same `codex exec ...` with the Bash tool's `run_in_background` so it detaches; report the job started and stop for this turn.
- Return Codex's output **verbatim** — do not paraphrase, summarize, or add findings of your own. Prefix it with one line: `Engine: real Codex (codex exec)`.
- If `codex exec` errors (network, rate limit, wedged binary), say so plainly and offer to re-run via the Step 3B fallback rather than failing silently.

## Step 3B: Claude fallback (Codex methodology)

Run the adversarial review yourself, following `references/codex-review-methodology.md`. Be explicit that this is the same-family engine so the user can weigh it accordingly.

1. Pull the full diff for the resolved range: `git diff <RANGE>`. For large diffs (>2000 lines), go file-by-file.
2. Apply the methodology's four adversarial lenses — **Approach**, **Design & tradeoffs**, **Assumptions**, **Failure modes under real conditions** — on top of the defect floor (the `references/review-checklist.md` critical list: SQL safety, race conditions, LLM trust boundaries, auth bypass, data loss, enum completeness).
3. Fold in any focus text as a priority lens.

## Step 4: Findings format

Each finding:

```
## [CRITICAL|INFO] {title}

**File:** {path}:{line}
**Lens:** {Approach | Design | Assumption | Failure-mode | Defect}
**What:** {the issue, specific to this commit}
**Why it matters:** {impact on the user or system}
**Fix:** {concrete remediation — describe it; do not apply it}
```

## Step 5: Summary

```
CODEX REVIEW (just-committed)
═════════════════════════════
Engine:  {real Codex (codex exec) | Claude fallback (Codex methodology)}
Commit:  {short-sha} {subject}
Range:   {RANGE}
Files:   {N}   Lines: +{added} -{removed}
Focus:   {focus text, or "none"}

CRITICAL: {N — challenge the approach / must address before push}
INFO:     {N — worth considering}

Verdict: {SHIP | RECONSIDER APPROACH | NEEDS FIXES}
```

Review-only: present findings and stop. If the user wants fixes, that's a separate `/gstack-investigate` or manual pass followed by a fresh review of the new commit.
