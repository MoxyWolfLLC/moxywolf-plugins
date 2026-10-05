---
description: Check whether a repository is ready for goal mode (GO-008) and say who closes each gap — read-only, changes nothing
allowed-tools: Read, Bash
argument-hint: <owner>/<repo>
---

Goal mode (`/gstack-goal-new`, `/gstack-goal`) runs only in a repository whose own `main` holds everything that enforces it, under Dorian's code-owner review. This command checks one repository and reports what it lacks. It writes nothing, in either repository.

1. **Run the check** from a checkout of `MoxyWolfLLC/moxywolf-plugins`. It compares against that checkout's `HEAD` and prints which commit. If that isn't `origin/main`'s tip, say so in the report. Updating the checkout is a separate step, not part of this command:
   `python3 plugins/gstack-execution/scripts/agent_token.py exec --repo <owner>/<repo> -- python3 plugins/gstack-execution/scripts/goal_ready.py <owner>/<repo>`
   If the token isn't minted, the moxywolf-agent app isn't installed on that repository. That's the first gap, and Dorian closes it.
2. **Report every line as printed** (`ready`, `missing` or `unknown`) and the count. Exit 0 means ready: say so, and that `/gstack-goal-new` can draft its first goal. Unknown is not ready.
3. **Say who closes each gap:**
   - **App, ruleset, `goal-holdout` environment (main only), and any `CODEOWNERS` change:** Dorian, as the repository's admin.
   - **`DESIGN.md` with objectives:** the agent, through `/gstack-design-doc`.
   - **The repository's check pins:** `.github/goal-checks.json` pins its own checks (GO-005.7). It's a `CODEOWNERS` path, so the agent proposes it in a pull request and Dorian approves it.
   - **The goal workflows and scripts:** the agent proposes them in that repository's onboarding pull request, copied from this checkout's `HEAD`, and Dorian approves it (GO-008.4). A Node repository works too (GO-002.7). If its build fetches from the network, say so: that build fails in the sandbox until the repository vendors what it fetches. Never copy the workflows or scripts across by hand.
4. **Preview deploys.** If the repository deploys previews from a hosting integration (Vercel, say), previews can stay on only while the Preview environment variables hold no production credential (GO-005.8). Establish that from the host's API (which variables Preview has and what each one is for, never a value) or ask Dorian to confirm it. If neither has happened, report the preview requirement as **unverified**: no goal runs there until it's resolved.

Don't retry a refused call or work around a missing permission. Report it as the check printed it.
