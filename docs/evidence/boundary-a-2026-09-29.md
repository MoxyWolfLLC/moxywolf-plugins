# Boundary test B-a: the pre-merge gate on gate-lab and on main

**Date:** 2026-09-29 · **Repository:** MoxyWolfLLC/gate-lab (public, sacrificial) · **Ruleset:** `main-gate` (id 24200051), imported by Dorian from `gate-lab-ruleset-import.json` · **Actor:** `moxywolf-agent[bot]`, the app's installation token · **Approver:** `dorianatmoxywolf`

## Result

**Pass on gate-lab.** GitHub refused all eight attempts, and the one control merge went through. `main` stayed at the seed commit `91b51b8` through every refused attempt, and moved only on the control merge, to `2e003da`.

| # | Attempt, as the bot | Outcome | GitHub's words |
|---|---|---|---|
| 1 | Merge PR #2 with no approval | refused, 405 | "Waiting on code owner review from dorianatmoxywolf." |
| 2 | Push to PR #2 after Dorian approved `1f9d555`, then merge `0d21162` with `tests` green | refused, 405 | GitHub set the approval to `DISMISSED` on its own, then: "Waiting on code owner review from dorianatmoxywolf." |
| 3 | Merge PR #3, approved at its head, with `tests` failing | refused, 405 | "Required status check \"tests\" is failing." |
| 4 | Merge PR #4, approved at its head, where the job was renamed so `tests` never reports | refused, 405 | "Required status check \"tests\" is expected." |
| 5 | Push a commit straight to `main` | refused, GH013 | "Changes must be made through a pull request." |
| 6 | Force-push an unrelated history over `main` | refused, GH013 | "Cannot force-push to this branch" |
| 7 | Disable the ruleset; delete the ruleset | refused, 403 both | "Resource not accessible by integration" |
| 8 | Approve its own pull request | refused, 422 | "Review Can not approve your own pull request" |
| control | Merge PR #2 after Dorian's second approval, at head `0d21162`, `tests` green | **merged** by `moxywolf-agent[bot]` | merge commit `2e003da` |

GitHub reports `current_user_can_bypass: never` for the bot on this ruleset.

## On moxywolf-plugins `main`

**Pass.** Dorian merged `.github/CODEOWNERS` (PR #74, `2c50154`), imported `main-gate` from `moxywolf-plugins-main-ruleset-import.json` (ruleset id 24201147), and deleted the 2026-09-20 `protect-main` ruleset, which had the app on its bypass list and **Restrict updates** on. Read through the API as the bot, `main-gate` is the only ruleset, its rules match gate-lab's, and `current_user_can_bypass` is `never`.

Attempts 1 to 3 then ran against PR #75, a probe that changed only `docs/evidence/boundary-a-main-probe.md` until attempt 3. `main` stayed at `2c50154` throughout. PR #75 was closed unmerged and its branch deleted.

| # | Attempt, as the bot | Outcome | GitHub's words |
|---|---|---|---|
| 1 | Merge PR #75 at `31195ec`, `tests` green, no approval | refused, 405 | "Waiting on code owner review from dorianatmoxywolf." |
| 2 | Dorian approved `31195ec`; the bot pushed `929c51d` (`tests` green), then merged | refused, 405 | GitHub set the approval to `DISMISSED` on its own, then: "Waiting on code owner review from dorianatmoxywolf." |
| 3 | The bot pushed `375e011`, a plugin README change with no version bump, so `tests` failed; Dorian approved `375e011`; the bot merged | refused, 405 | "Required status check \"tests\" is failing." |

## What this proves, and what it doesn't

- It proves that on gate-lab the gate is GitHub's. The bot can't merge without Dorian's approval at the exact head, can't reuse an approval after a new push, can't merge past a red or missing `tests`, can't push around the pull request, and can't change the ruleset.
- On gate-lab alone, it proved nothing about `moxywolf-plugins` `main`. The section below repeats attempts 1 to 3 there, after Dorian applied `main-gate` to it.
- **The bypass list isn't verified here.** The bot's token can't read `bypass_actors`. The claim that only Repository admin can bypass rests on the imported file Dorian used, and on GitHub reporting `current_user_can_bypass: never` for the bot. No export of the saved ruleset was taken.
- Dorian, as Repository admin, can still bypass the gate. GitHub showed him "Merge without waiting for requirements to be met (bypass rules)" on PR #3. That's by design: the human keeps the override, and the agent doesn't have one.

## The agent-side checks, as a second line

`release`, `merge-instruction` and `record-release` weren't the gate in this test, and none of them could have let a merge through: every refusal above came from GitHub before any agent-side check ran. Their role is to record what happened, not to stop it.

## The ruleset as the bot reads it

Read through `GET /repos/MoxyWolfLLC/gate-lab/rulesets/24200051` with the app's token; `bypass_actors` isn't returned to it.

```json
{
  "id": 24200051,
  "name": "main-gate",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "~DEFAULT_BRANCH"
      ]
    }
  },
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "required_reviewers": [],
        "require_code_owner_review": true,
        "dismissal_restriction": {
          "enabled": false,
          "allowed_actors": []
        },
        "require_last_push_approval": true,
        "required_review_thread_resolution": false,
        "require_extra_approval_for_unattributed_changes": true,
        "allowed_merge_methods": [
          "merge",
          "squash",
          "rebase"
        ]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {
            "context": "tests",
            "integration_id": 15368
          }
        ]
      }
    }
  ],
  "current_user_can_bypass": "never",
  "updated_at": "2026-09-29T18:32:05.912Z"
}
```

## Verbatim log

```text
PR #2 head 1f9d555a7b60699fd0827ca870b824d1db812215 checks: [('tests', 'completed', 'success')]
PR #3 head 155ef76c815ad6e3d683180985bec353ac777050 checks: [('tests', 'completed', 'failure')]
PR #4 head 52e5d52dcded83951fe2ef0c36b59dcd4427f9df checks: [('tests-renamed', 'completed', 'success')]
=== A1 merge PR #2 with no approval (2026-09-29T18:34:33Z)
PUT repos/MoxyWolfLLC/gate-lab/pulls/2/merge returned 405
{
  "message": "Repository rule violations found\n\nWaiting on code owner review from dorianatmoxywolf.\n\n",
  "documentation_url": "https://docs.github.com/rest/pulls/pulls#merge-a-pull-request",
  "status": "405"
}

=== A8 bot approves its own PR #2 (2026-09-29T18:34:39Z)
POST repos/MoxyWolfLLC/gate-lab/pulls/2/reviews returned 422
{
  "message": "Unprocessable Entity",
  "errors": [
    "Review Can not approve your own pull request"
  ],
  "documentation_url": "https://docs.github.com/rest/pulls/reviews#create-a-review-for-a-pull-request",
  "status": "422"
}

=== A7 bot edits the ruleset (2026-09-29T18:34:41Z)
PUT repos/MoxyWolfLLC/gate-lab/rulesets/24200051 returned 403
{
  "message": "Resource not accessible by integration",
  "documentation_url": "https://docs.github.com/rest/repos/rules#update-a-repository-ruleset",
  "status": "403"
}

=== A7b bot deletes the ruleset
DELETE repos/MoxyWolfLLC/gate-lab/rulesets/24200051 returned 403
{
  "message": "Resource not accessible by integration",
  "documentation_url": "https://docs.github.com/rest/repos/rules#delete-a-repository-ruleset",
  "status": "403"
}

=== A5 direct push to main (2026-09-29T18:34:52Z)
remote: error: GH013: Repository rule violations found for refs/heads/main.        
remote: Review all repository rules at https://github.com/MoxyWolfLLC/gate-lab/rules?ref=refs%2Fheads%2Fmain        
remote: 
remote: - Changes must be made through a pull request.        
remote: 
remote: - Required status check "tests" is expected.        
remote: 
To https://github.com/MoxyWolfLLC/gate-lab.git
 ! [remote rejected] main -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/MoxyWolfLLC/gate-lab.git'
rc=1
=== A6 force push to main (2026-09-29T18:34:56Z)
remote: error: GH013: Repository rule violations found for refs/heads/main.        
remote: Review all repository rules at https://github.com/MoxyWolfLLC/gate-lab/rules?ref=refs%2Fheads%2Fmain        
remote: 
remote: - Cannot force-push to this branch        
remote: 
remote: - Changes must be made through a pull request.        
remote: 
remote: - Required status check "tests" is expected.        
remote: 
To https://github.com/MoxyWolfLLC/gate-lab.git
 ! [remote rejected] forced -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/MoxyWolfLLC/gate-lab.git'
rc=1
main on server: 91b51b8165c2 (expected 91b51b8165c2)
PR #2 reviews: [('dorianatmoxywolf', 'APPROVED', '1f9d555a7b60')]
PR #3 reviews: [('dorianatmoxywolf', 'APPROVED', '155ef76c815a')]
PR #4 reviews: [('dorianatmoxywolf', 'APPROVED', '52e5d52dcded')]
=== A3 merge PR #3, approved at head 155ef76c815ad6e3d683180985bec353ac777050 (2026-09-29T18:38:26Z)
PUT repos/MoxyWolfLLC/gate-lab/pulls/3/merge returned 405
{
  "message": "Repository rule violations found\n\nRequired status check \"tests\" is failing.\n\n",
  "documentation_url": "https://docs.github.com/rest/pulls/pulls#merge-a-pull-request",
  "status": "405"
}

=== A4 merge PR #4, approved at head 52e5d52dcded83951fe2ef0c36b59dcd4427f9df (2026-09-29T18:38:32Z)
PUT repos/MoxyWolfLLC/gate-lab/pulls/4/merge returned 405
{
  "message": "Repository rule violations found\n\nRequired status check \"tests\" is expected.\n\n",
  "documentation_url": "https://docs.github.com/rest/pulls/pulls#merge-a-pull-request",
  "status": "405"
}

=== A2 PR #2: approval at 1f9d555a7b60, new head 0d21162f1449 (2026-09-29T18:38:51Z)
reviews now: [('dorianatmoxywolf', 'DISMISSED', '1f9d555a7b60')]
checks at new head: [('tests', 'completed', 'success')]
PUT repos/MoxyWolfLLC/gate-lab/pulls/2/merge returned 405
{
  "message": "Repository rule violations found\n\nWaiting on code owner review from dorianatmoxywolf.\n\n",
  "documentation_url": "https://docs.github.com/rest/pulls/pulls#merge-a-pull-request",
  "status": "405"
}

main on server: 91b51b8165c2
PR #2 reviews: [('dorianatmoxywolf', 'DISMISSED', '1f9d555a7b60'), ('dorianatmoxywolf', 'APPROVED', '0d21162f1449')]
=== CONTROL merge PR #2, approved at head 0d21162f1449, tests green (2026-09-29T18:41:12Z)
{
  "sha": "2e003daef4882cfb654adc2a95835e62a64ba25d",
  "merged": true,
  "message": "Pull Request successfully merged"
}

merged: True by moxywolf-agent[bot] commit 2e003daef488
main on server: 
main head (API): 2e003daef488 protected: True
PR 3 closed not merged
PR 4 closed not merged
```
