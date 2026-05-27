---
description: Show the current state of an in-progress piece — phase, gates passed, next step.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Glob, Grep, Bash]
---

# /4d-blog-engine:blog-status — print current piece state

Print a concise status report for an in-progress piece.

**Argument:** `<piece-slug>` — the per-piece directory under `<active-project>/12 – MARCOM/Posts/`. If omitted, picks the most-recently-modified piece in the active project.

Report shape:

```
4D Blog Engine — piece status

Slug:           <slug>
Title:          <title>
Path:           <piece-dir>
Active project: <project name>

Phase progress:
  [x] 01 — Delegation     — passed at <timestamp>
  [x] 02 — Description    — passed at <timestamp>
  [ ] 03 — Discernment    — IN PROGRESS (last action: <last log entry>)
  [ ] 04 — Diligence      — pending
  [ ] LinkedIn pair       — pending

Phase 3 details (if Phase 3 has run):
  Discourse sweep:   <N> findings, <M> clusters, <K> Tier-1-3 citable
  Council synthesis: <ran|degraded|skipped>
  Slop grade:        <A|B|C|D|F>
  Findings: <count> Major, <count> Medium, <count> Minor

Phase 4 details (if Phase 4 has run):
  Round:             <N> of 3
  Reviewer verdict:  <BLOCKING:true|BLOCKING:false|pending>
  Score:             <total>/100
  Release Owner:     <signed by initials on date | UNSIGNED>

Suggested next command:
  /4d-blog-engine:blog-discern  <slug>   (because Phase 3 is in progress)
```

The status command is read-only. It does not modify state, does not advance phases, and does not invoke any sub-skill.

To find the piece: walk up from CWD looking for `00 – Project Hub/cowork-project-instructions.md` to identify the active project, then scan `<active-project>/12 – MARCOM/Posts/*/state.md` for the most recently modified piece (or filter by `<piece-slug>` if provided).

Read `skills/4d-blog-engine/SKILL.md` §"Status command" for the full logic.
