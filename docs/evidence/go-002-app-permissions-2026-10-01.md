# GO-002.3: the moxywolf-agent app holds no secrets permission

Run 2026-10-01 from the Cowork device VM, as the app (`agent_token.py permissions --repo MoxyWolfLLC/moxywolf-plugins`), which prints what the installation's token actually grants, not what the app requested (GA-007):

```
installation 163156626 (resolved from MoxyWolfLLC/moxywolf-plugins)
  contents                 write
  metadata                 read
  pull_requests            write
  workflows                write
  repository_selection: all
```

No `secrets` entry, so no token minted for a builder or the runner can read an Actions or environment secret through the API, which is where `GOAL_<ID>_HOLDOUT` lives. `workflows: write` is present; goal-run tokens drop it (GO-003.5), because a pushed workflow could otherwise read secrets from inside a run. The runner re-checks this at every start (GO-003.3) rather than trusting this record.
