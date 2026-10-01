# main-gate relaxed, 2026-09-30

Dorian changed ruleset `main-gate` (24201147) as admin on 2026-09-30. His reason: "We could significantly speed up development if I didn't have to sit in front of the computer and press approve."

What changed under *Require a pull request before merging*: required approvals 1 to 0, code-owner review off, last-push approval off, stale-review dismissal off. Still on: pull request required, the `tests` check, block force pushes, restrict deletions. Repository admin is still the only bypass.

What the bot reads at `GET /repos/MoxyWolfLLC/moxywolf-plugins/rules/branches/main` after the change:

```json
[
    {
        "type": "deletion",
        "ruleset_source_type": "Repository",
        "ruleset_source": "MoxyWolfLLC/moxywolf-plugins",
        "ruleset_id": 24201147
    },
    {
        "type": "non_fast_forward",
        "ruleset_source_type": "Repository",
        "ruleset_source": "MoxyWolfLLC/moxywolf-plugins",
        "ruleset_id": 24201147
    },
    {
        "type": "pull_request",
        "parameters": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews_on_push": false,
            "required_reviewers": [],
            "require_code_owner_review": false,
            "dismissal_restriction": {
                "enabled": false,
                "allowed_actors": []
            },
            "require_last_push_approval": false,
            "required_review_thread_resolution": false,
            "require_extra_approval_for_unattributed_changes": true,
            "allowed_merge_methods": [
                "merge",
                "squash",
                "rebase"
            ]
        },
        "ruleset_source_type": "Repository",
        "ruleset_source": "MoxyWolfLLC/moxywolf-plugins",
        "ruleset_id": 24201147
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
        },
        "ruleset_source_type": "Repository",
        "ruleset_source": "MoxyWolfLLC/moxywolf-plugins",
        "ruleset_id": 24201147
    }
]
```

This file is the change in the pull request that checks the relaxed gate from the bot's side: the bot opens it, `tests` runs, and the bot merges it with no human approval. The tiered version that puts the gate's own code back under Dorian's review is GA-008, proposed in Taskade `06 – Engineering/risk-tiered-merge-proposal-2026-09-30.md`.
