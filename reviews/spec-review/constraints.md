# Spec review: DESIGN.md constraints

_2026-11-12T00:03:27+00:00 · claude-sonnet-5-5 with claude-fable-5-2 advisor (1 calls)_

I found no contradictions in the plan, only ambiguities. Of the advisor's candidate pairs, two are resolved by the plan's own text and I dropped them. The first is *Test the boundaries before adding item IDs* against *One release path*, because the plan exempts `released` and `merged_unreviewed`. The second is the `review` → `done` shortcut against `released` → `done`, which the plan marks as interim. I also dropped the pair on low-risk autonomy against "merges with no human approval". Assessing a merge's effects, including deployment triggers, doesn't require a human approval, and this repository has no deployment target.

The plan has no items, so every id below is a constraint heading or the opening words of a bullet.

**Ambiguities**
- **A1** (*The pre-merge gate is GitHub's*): the brief pull request adds `goals/<id>/`, which is a `CODEOWNERS` path. The same constraint says `goal-envelope` fails a goal's pull request into `main` that touches one. The plan doesn't say whether the brief PR is such a pull request or targets another branch.
- **A2** (*The pre-merge gate is GitHub's*, *The agent merges on a clean review*): "closed" and "wide" for the lane are never defined, and neither is who switches it.
- **A3** (*Test the boundaries before adding item IDs*): the "*Boundary tests* below" section is missing. Whether the three tests "have run and their findings are recorded" can't be decided from the plan.
- **A4** (*The pre-merge gate is GitHub's*, *Coverage is mandatory*): the lane-wide merge needs a "clean whole-goal review", but the plan doesn't say whether that review needs coverage `checked` or can use a recorded exception.
- **A5** (*One release path*, *Coverage is mandatory*): the owner merges a clean review whose coverage isn't `checked`, with no exception recorded. The plan doesn't say whether that item is `merged_unreviewed` or stuck in a state `record-release` refuses.
- **A6** (Keep `/gstack-verify` advisory, *Coverage is mandatory*): the plan doesn't say whether incomplete verification feeds the review coverage status, which blocks release. If it does, "advisory" no longer holds.
- **A7** (Keep low-risk, authorized work autonomous): "consequential boundaries" is undefined, so which actions need human approval can't be decided.

```json
{"contradictions": [],
 "ambiguities": [
  {"id": "A1", "requirements": ["The pre-merge gate is GitHub's"], "question": "Is the goal's brief pull request (which adds goals/<id>/, a CODEOWNERS path) a 'goal's pull request into main' that goal-envelope fails, or does it target a different branch? If it targets main, how can it pass goal-envelope?"},
  {"id": "A2", "requirements": ["The pre-merge gate is GitHub's", "The agent merges on a clean review, not on words"], "question": "What do the lane states 'closed' and 'wide' mean, who sets them, and where is the current state recorded?"},
  {"id": "A3", "requirements": ["Test the boundaries before adding item IDs"], "question": "The 'Boundary tests' section it points to is not in the plan. How is 'the three boundary tests have run and their findings are recorded' decided?"},
  {"id": "A4", "requirements": ["The pre-merge gate is GitHub's", "Coverage is mandatory"], "question": "Must the lane-wide 'clean whole-goal review' have coverage 'checked', or can a recorded owner exception stand in for it?"},
  {"id": "A5", "requirements": ["One release path, checked by code", "Coverage is mandatory"], "question": "When the owner merges a clean review whose coverage isn't 'checked' and no exception was recorded before the merge, is the item merged_unreviewed, or is it in a state that record-release refuses?"},
  {"id": "A6", "requirements": ["Keep /gstack-verify advisory; incomplete verification must remain visible", "Coverage is mandatory"], "question": "Does incomplete /gstack-verify output feed the review coverage status? If so, it blocks release and is no longer advisory."},
  {"id": "A7", "requirements": ["Keep low-risk, authorized work autonomous. Human approval belongs at consequential boundaries"], "question": "What makes an action 'consequential' or 'low-risk', so that human approval requirements can be decided?"}
 ]}
```
