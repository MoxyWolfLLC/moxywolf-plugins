# DC-001 build-branch history (criterion 8: the probe came first)

Repository-derived at commit time on `build/DC-001-decider-council`, base `195f18f` (main after PR #227). The same order is on GitHub at https://github.com/MoxyWolfLLC/moxywolf-plugins/pull/228/commits. Round 1 and 2 of review `20261018-104726-2e78652-u2t4ltw8` (F4) could not see commit order from the review surface, which carries a cumulative diff; this file is the committed record of it.

```
$ git log --reverse --format='%h %ad %s' --date=iso-strict 195f18f..HEAD
6a0f97c 2026-10-18T16:27:20+00:00 DC-001: live probe of the three deciders on /v1/decisions
7c23b25 2026-10-18T16:57:30+00:00 DC-001: the decider council, three voices on one wire, and model_select is its first caller
cdebf5e 2026-10-18T17:21:51+00:00 DC-001: review 20261018-100213 round 1 fixes (F1 to F5, F8, F9)
2e78652 2026-10-18T17:42:51+00:00 design: DC-001 criteria 1, 2, 9 and 10 amended on Dorian's approval
415b166 2026-10-18T18:03:13+00:00 DC-001: review 20261018-104726 round 1 fixes (F1, F2, F3) and the gate's named comparison

$ git show --stat --format='%h %ad %s' --date=iso-strict 6a0f97c   # the first commit on the branch
6a0f97c 2026-10-18T16:27:20+00:00 DC-001: live probe of the three deciders on /v1/decisions

 docs/evidence/decision-quorum-probe-2026-10-18.md | 314 ++++++++++++++++++++++
 1 file changed, 314 insertions(+)
```

The first commit, `6a0f97c`, adds one file, `docs/evidence/decision-quorum-probe-2026-10-18.md`, and nothing else. The implementation follows in `7c23b25`.
