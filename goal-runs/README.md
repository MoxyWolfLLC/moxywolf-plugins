# Goal runs

`goal-runs/<id>/RESULT.md` is a goal's run record, added in the finalize pull request into `goal/<id>`. The goal pull request into `main` merges as the bot once its checks are green and a whole-goal cross-vendor review is clean (DESIGN.md, GO-011.2). It sits outside `goals/<id>/` so writing it never changes the approved tree. This README is a `CODEOWNERS` path; a goal's own `goal-runs/<id>/` isn't.
