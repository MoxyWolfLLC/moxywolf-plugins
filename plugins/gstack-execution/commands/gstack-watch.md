---
description: The watcher (GA-013 part C) - fixes moxywolf-agent's own pull requests after the session ends, from a scheduled GitHub Actions workflow
argument-hint: [run | status]
---

The watcher runs as `.github/workflows/gstack-watch.yml` in moxywolf-plugins, every 20 minutes, over the repositories in `.github/gstack-watch.json` (adding one needs Dorian's approving review). On each of `moxywolf-agent`'s own open `build/*` and `goal/*` pull requests it looks for a failing check, a merge conflict, or a review comment newer than the head that the agent didn't write, and works it with `/gstack-ship`'s Fix Contract: a mechanical fix is pushed as `moxywolf-agent`, a judgment call becomes a comment. It never merges, approves, closes, rebases or force-pushes, and never changes an owned or closed-lane path. After a push it comments that the gstack review covers an old head.

- `run`: start it now with `gh workflow run gstack-watch.yml -R MoxyWolfLLC/moxywolf-plugins` (needs a login that can dispatch workflows), then read the run's summary.
- `status`: `gh run list -R MoxyWolfLLC/moxywolf-plugins -w gstack-watch -L 5`; each run's summary names every repository and pull request it examined and what it did, and its `watch-log` artifact keeps that for 90 days.

It needs two repository secrets Dorian sets, `MOXYWOLF_AGENT_APP_KEY` and `GSTACK_WATCH_ANTHROPIC_KEY` (its own Anthropic Console workspace, with a monthly limit), recorded in `docs/evidence/GA-013-watch-setup.md`. Without them every run fails, naming the missing one. Local work is still `/gstack-build`; this command doesn't replace it.
