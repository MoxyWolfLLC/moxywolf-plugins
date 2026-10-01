# Boundary test B-d, 2026-09-30

GA-008's live check (DESIGN.md, GA-008). Dorian turned **Require review from Code Owners** on in `main-gate` with required approvals at 0. The bot then read `GET /repos/MoxyWolfLLC/moxywolf-plugins/rules/branches/main`:

```
required_approving_review_count: 0
require_code_owner_review: true
require_last_push_approval: false
dismiss_stale_reviews_on_push: false
```

**Attempt 1, a gate file.** PR #96 changed one comment line in `.github/CODEOWNERS` (head `bafbdd4`). `tests` passed. GitHub reported `mergeable_state: blocked`, and the bot's merge at that head was refused:

> 405 Repository rule violations found. Waiting on code owner review from dorianatmoxywolf.

The PR was closed unmerged and its branch deleted. `main` stayed at `1c4a046`.

**Attempt 2, docs only.** This file is the only change in its pull request. It's under `docs/evidence/`, which `CODEOWNERS` doesn't list, so it should merge on green `tests` with no approval. The merge commit is the result.

So code-owner review is enforced with zero required approvals: gate paths wait for Dorian, and everything else doesn't.
