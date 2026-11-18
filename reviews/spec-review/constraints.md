# Spec review: DESIGN.md constraints

_2026-11-18T04:32:03+00:00 · claude-sonnet-5-5 with claude-fable-5-2 advisor (1 calls)_

I found no contradictions among the constraints. The plan has no items under review, so any contradiction would have been scope `constraints`. I kept three ambiguities. I tested the advisor's four candidate additions against the plan text and dropped all of them:

- **XE-015 reviewed afterwards at the same head:** *One release path* already settles this. It says "an item marked 'Merged unreviewed' can't become `released` by a review after the fact", and that "a review after the fact isn't permission given before it".
- **Interim `review` → `done` against `released` → `done`:** the plan states the interim rule and ties its end to "the first fix B-a produces". That is decidable.
- **Deployment-trigger assessment against "merges with no human approval":** the constraint says to assess effects, not to gate them on a human. `.github/` is owned, so workflow changes that trigger deployment still need Dorian's review.
- **Successor folders against "No autonomous topology expansion":** successor folders are held byte for byte to the root brief by `goal_successor.py`, which is a static check. I don't read them as topology growth.

The ambiguities:

- **A1:** `goals/` must stay owned under GA-008, but successor folders under it must be unowned. The plan doesn't say how the test reconciles the two.
- **A2:** *One release path* says each move has "one condition a script can check". The `review` → `released` move has several conditions. This sits inside that one constraint.
- **A3:** the `/gstack-verify` constraint says it is advisory. *Coverage is mandatory* says non-`checked` coverage is a block. The plan doesn't say whether the block applies to `/gstack-verify`.

I dropped my earlier A4, because the gate paragraph already says `goal_successor.py` is owned, so the answer is in the plan.

```json
{"contradictions": [],
 "ambiguities": [
  {"id": "A1", "requirements": ["The pre-merge gate is GitHub's, sized to the stakes", "A goal delegates item selection, not authority"], "question": "`goals/` is a CODEOWNERS path that GA-008's test requires to stay owned, but successor folders `goals/<id>--s1/` and `--s2/` under it must be unowned. Does `test_codeowners.py` accept an override for successor folders, and what is the exact pattern?"},
  {"id": "A2", "requirements": ["One release path, checked by code"], "question": "The plan says each state move has 'one condition a script can check', but `review` → `released` needs a clean cross-vendor review at the head, `record-release` success, Dorian's approving review for a CODEOWNERS path, and a recorded exception when coverage isn't `checked`. Is that one composite condition or several, and which script checks which?"},
  {"id": "A3", "requirements": ["Keep `/gstack-verify` advisory; incomplete verification must remain visible", "Coverage is mandatory"], "question": "Does the 'visible block, not a pass' rule for non-`checked` coverage apply to `/gstack-verify` results, or only to peer-review coverage? If it applies, `/gstack-verify` is no longer advisory."}
 ]}
```
