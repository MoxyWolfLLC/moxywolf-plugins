# Reconstruction, not a record

**Review ID:** `20260912-122421-80159e3-_lrr97ak`
**Reviewer:** codex / gpt-6-astra · **Builder:** claude / claude-opus-5
**Outcome:** `rounds_exhausted`, 3 of 3 rounds used
**Subject:** `build/EV-evidence-integrity`, opened at `80159e3`, final head `b746e22`
**Merged:** `c747ab9` (PR #9), 13 September 2026

## Read this first

This file is a reconstruction. The review's own record is gone.

`peer_review.py` defaulted `REVIEW_DIR` to `$HOME/.gstack/peer-review`. In a sandboxed
session `$HOME` is per-session and outside every connected folder, so `packet.json`,
`round-1.json` through `round-3.json`, the round prompts, `dispositions.json` and
`state.json` were destroyed when the session ended. Nothing recovers them.

What survives is the pull request comment written at release time, quoted below, plus
the commits and the tests. So a reader can check what the review concluded and what was
changed because of it, and cannot check what the reviewer actually examined, which is
the difference between a record and an account of one. EV-009 stops the next review
losing its record the same way. It does not recover this one.

**Source:** PR #9 comment `5648256649`, 2026-09-12T19:45:18Z, by the Release Owner.
https://github.com/MoxyWolfLLC/moxywolf-plugins/pull/9#issuecomment-5648256649

## Round 1: six blockers, all accepted

| | Finding | Status |
|---|---|---|
| F1 | `lstrip("./")` ate the leading dot, so findings in `.claude-plugin` and `.github` bound as unresolvable | verified fixed |
| F2 | a verifier that examined nothing reported success | raised three times, see below |
| F3 | verification re-hashed the subject's own stored path, which says nothing about the finding citing it | verified fixed |
| F4 | disposition coverage checked only the final round, excusing exactly the blockers that were acted on | verified fixed |
| F5 | the write sweep exempted every hidden path and every `.lock`, not only executor-owned files | verified fixed |
| F6 | observation argv built by formatting and re-splitting a string, tearing apart every path containing a space; a failed command still recorded its claim | verified fixed |

## F2, four times

A wholly missing round record. Then a record carrying only an outcome. Then fields
checked for presence but not for shape. Each repair passed the builder's own testing and
the reviewer found the next one. Writing the third regression surfaced a fourth instance
of the same rule having a second home: two later sweeps re-read the round records without
the shape check, so a malformed record crashed a sweep that the validated walk had already
rejected. All three walks now read collectors filled in during the one validated pass.

## What was never established

The third F2 repair (`b746e22`) and the one-walk change that followed it carry regression
tests and no reviewer sign-off, because the round limit was reached first. The reviewer's
final evidence named `repos=null`, `findings={}` and `acceptance=null`, each of which
either verified falsely or crashed. Those cases are covered by
`test_f2_a_round_field_of_the_wrong_shape_does_not_verify` and
`test_f2_a_finding_that_is_not_an_object_does_not_verify`, written and verified by the
builder and not by the other tool.

The Release Owner merged on that evidence rather than opening a fresh review of the final
head. Exhausting the round limit was not treated as approval, and is not recorded as one.

## Verification at the merged head

95 tests: 27 evidential links, 33 task graph, 20 governed review, 20 release gate, plus
the `peer_review` and `endform_workflow` selftests.
