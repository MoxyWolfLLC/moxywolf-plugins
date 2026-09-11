---
description: Bounded cross-tool review loop at an implementation checkpoint — the other tool (Codex or Claude Code) reviews pinned commits against a fixed contract; one review plus two fix-verification passes, explicit outcomes, never a same-tool substitute
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, AskUserQuestion
argument-hint: --builder claude|codex [--base <ref>] [--head <ref>] [--repo <path> ...] [--max-rounds 3] [--packet <file>] [outcome text ...]
---

Run the peer review loop defined in `references/peer-review-contract.md` at a **completed implementation checkpoint**, not per file edit. The dispatcher `scripts/peer_review.py` enforces commit identity, tool routing, output validation, and round limits; you supply the packet, substantiate and fix findings, and record dispositions.

Operating rule: review the implementation against the agreed outcome; inspect direct dependencies where necessary; fix demonstrated blockers automatically within scope; preserve unrelated findings separately; do not turn review into a new project or return routine implementation decisions to the user. Approach challenges belong in `/gstack-plan-review`, not here.

Raw slash-command arguments: `$ARGUMENTS`

## Step 0: Refuse to recurse

If `GSTACK_PEER_REVIEW_SESSION` is set in the environment, this is a reviewer session. Stop and say so. The dispatcher refuses too.

## Step 1: Build the packet

`--builder` is required and names the tool that wrote the code (`claude` for a Claude Code or Cowork session, `codex` when Codex built it). Never infer it from git authorship. The reviewer is always the other tool.

Assemble `packet.json` (path from `--packet`, else write it to the review dir the dispatcher reports). Every field is required; the dispatcher rejects a packet with a missing field or an unresolvable commit:

```json
{
  "outcome": "the user outcome, one or two sentences",
  "acceptance_criteria": ["checkable statements of done"],
  "repos": [{"path": "/abs/repo", "base": "<sha or ref>", "head": "<sha or ref>"}],
  "changed_behavior": "what behaves differently and the entry points that reach it",
  "exclusions": ["settled decisions and out-of-scope areas the review must not reopen"],
  "tests": {"commands": ["..."], "results": "what they showed", "environment": "where they ran"},
  "prior_findings": []
}
```

- `base`/`head` default to `HEAD~1`/`HEAD` (or `--base`/`--head`); one exact pair per repository, one entry per `--repo`. The dispatcher resolves them to full SHAs and stores those.
- `tests` is evidence, not a claim: paste the actual command and its actual result. The final check exercises the user's workflow, not only internal helpers; say which.
- `exclusions` is where settled architecture goes so the reviewer cannot reopen it.

## Step 2: Open and run round 1

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peer_review.py" open --builder <claude|codex> --packet packet.json --max-rounds 3
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peer_review.py" round <review-id>
```

The reviewer runs non-interactively in a fresh session against a detached read-only snapshot of the head commit. Report the outcome exactly as the dispatcher names it. `review_unavailable`, `missing_commits`, `timeout`, and `malformed_output` are results, not passes; say what they mean (for `review_unavailable`: which tool is missing and that no same-tool substitute was made).

## Step 3: Substantiate, fix, disposition

For each `blocking` finding, reproduce it or show why it does not hold, then apply the Fix Contract from `/gstack-ship`: fix in scope, run the focused check, commit. Record one disposition per blocking finding before the next round:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peer_review.py" disposition <review-id> F1=fixed F2=disproved:"repro at file:line shows X" F3=deferred
```

A `blocking` finding is deferred only with the user's say-so; ask with AskUserQuestion. `follow_up` and `separate` findings are listed in the report and tracked (Jira or the project backlog), never fixed inside this checkpoint and never silently dropped.

## Step 4: Fix-verification rounds

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peer_review.py" round <review-id> --head <repo-path>=<new-sha>
```

Base becomes the previous head; the reviewer verifies the dispositions and checks for regressions from the fixes; it does not restart a full review. Two fix-verification rounds by default. When the limit is hit with blockers open, the outcome is `rounds_exhausted` and `round-N.json` carries an `escalation` list: present it to the user as the exact disagreement, one line per finding, and stop. Exhaustion is never approval.

## Step 5: Report

```
PEER REVIEW
═══════════
Review ID: {id}         Builder: {tool} → Reviewer: {tool}
Repos:     {path} {base-short}..{head-short}  (one line per repo, final round)
Rounds:    {used}/{max}
Outcome:   {no_blocking_findings | fixes_verified | blocking_findings | rounds_exhausted | review_unavailable | missing_commits | timeout | malformed_output}
Acceptance: {N met}/{N}
Findings:  {N blocking → fixed/disproved/deferred/unresolved}, {N follow_up}, {N separate}
Escalation: {exact disagreement per unresolved finding, or "none"}
Verified:   {what the reviewer opened and what tests the builder ran, through which path}
Unverified: {what was not, and why}
```

Artifacts live under `$GSTACK_PEER_REVIEW_DIR/<review-id>/` (default `~/.gstack/peer-review/`): `packet.json`, `round-N.json`, `round-N-prompt.txt`, `dispositions.json`, `state.json`.
