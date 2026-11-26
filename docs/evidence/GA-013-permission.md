# GA-013.6: statuses: write on the moxywolf-agent app

GA-013.7 posts the commit status `gstack/release-lane` only on a repository whose own moxywolf-agent installation grants `statuses: write`. Until it does, `peer_review.py` prints `status_unavailable` and skips the post; open and release run unchanged.

## Dorian's step

1. Add **Commit statuses: Read and write** to the moxywolf-agent GitHub App (app id 5007349).
2. Accept the permission request on each installation: MoxyWolfLLC, OpenControls-AI and GRCSchema.
3. Confirm with `agent_token.py permissions --repo <owner>/<name>`: the list shows `statuses  write`.

## Record

- 2026-11-25, checked by the agent with `agent_token.py permissions`: MoxyWolfLLC/moxywolf-plugins and OpenControls-AI/cki showed `checks: read` and no statuses permission. GRCSchema not checked. Dorian's step not yet taken.
- 2026-11-25 16:10 PT, done by the agent in Dorian's Chrome on his instruction ("do it for me"): Commit statuses set to Read and write on the app, and the request accepted on MoxyWolfLLC, OpenControls-AI and GRCSchema; each asked only for that permission. `agent_token.py permissions` then showed `statuses  write` for MoxyWolfLLC/moxywolf-plugins and OpenControls-AI/cki.
