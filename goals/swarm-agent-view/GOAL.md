## Serves
Eleventh objective: goal mode

## Outcome
Add agent visualization to gstack: pick one tool from the table and wire it into the swarm. The tool is agent-flow (the npm package agent-flow-app, Apache 2.0), pinned at version 0.9.6. The swarm coordinator starts it with a new `swarm.py viewer-start <run>` command and stops it with `swarm.py viewer-stop <run>`. It runs on Dorian's Mac only and binds to 127.0.0.1, so no run data leaves the machine. The viewer is optional: if it is missing, the swarm runs exactly as before and says the viewer is unavailable. Dorian knows that the first start of agent-flow-app adds its own hooks to his personal `~/.claude/settings.json`, and he allowed it. The plugin's own hooks stay untouched. This goal builds the command and its documentation. Showing it on a real run is Dorian's usability check, because the goal tests run in a container with no network.

## Non-goals
- changing any hooks folder, hooks.json or other CODEOWNERS path
- editing `~/.claude/settings.json` from swarm.py (agent-flow-app does that itself on its first start)
- showing the viewer to Dorian from the cloud session
- a viewer of our own, or a different tool
- changing how a worker is launched, merged or reviewed

## Scenarios
- Given a Mac host with npx on the path, when `swarm.py viewer-start <run>` runs, then it starts `npx --yes agent-flow-app@0.9.6 --no-open --port <port>` in the background and prints the viewer address on standard output
- Given a host that is not a Mac, or has no npx, when `swarm.py viewer-start <run>` runs, then it prints one line starting `viewer: unavailable` on standard error, says the swarm is unaffected, and exits 0
- Given a viewer started by `viewer-start`, when `swarm.py viewer-stop <run>` runs, then the viewer process ends and the command exits 0, and with no viewer running it exits 0 and says so
- Given any swarm run, when the viewer starts, stops or crashes, then swarm.json and swarm-events.jsonl are byte for byte unchanged by it
- The viewer being started from any version of agent-flow-app other than 0.9.6 must never happen
- Changing plugins/gstack-execution/hooks/hooks.json (sha256 542f7e30d883d326d10441ed8f3a7c409e4d4720a9fac0c72f776f9d152b0092) must never happen
- Run data being sent off the machine, or the viewer binding to an address other than 127.0.0.1, must never happen
- A missing or crashed viewer delaying, blocking or changing a worker launch, merge or review must never happen

## Goal tests
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_start_runs_pinned_agent_flow_locally` (outcome)
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_start_without_a_mac_or_npx_says_unavailable_and_exits_zero` (outcome)
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_stop_ends_the_viewer_and_is_safe_when_none_runs` (outcome)
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_viewer_commands_never_change_run_state_files` (invariant)
- `tests/test_swarm_agent_view.py::SwarmAgentView.test_hooks_json_is_unchanged_and_no_unpinned_agent_flow_is_started` (invariant)

## Allowed paths
- plugins/gstack-execution/scripts/swarm.py
- plugins/gstack-execution/scripts/test_swarm.py
- plugins/gstack-execution/commands/gstack-goal.md
- plugins/gstack-execution/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json

## Spend cap
$5

## Provider budgets
- openrouter: $3

## Max calls
25

## Max items
3

## Max review rounds per item
2

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- swarm.py gains any write to `~/.claude/settings.json`
- a deploy to Preview or Production is Dorian's call

## Pre-mortem
- the tests pass because they only grep swarm.py text, while the command never starts a process; the outcome tests therefore run swarm.py as a separate program with a fake npx on the path and check what the fake received
- the viewer command is added but exits non-zero when npx is missing, so a missing viewer would stop a coordinator that calls it
- the pinned version is written in the docs but swarm.py uses `agent-flow-app` with no version, so a later upstream release would run
- a goal test that calls git or reads history fails in the test container, where the candidate checkout has no usable git; every test judges the checkout's files and program output only
- the tests assume a Mac, but the container is Linux; the command reads its platform from the environment variable `SWARM_VIEWER_PLATFORM` when set, so tests can say `Darwin` or `Linux`
- the fake npx is left running after the test ends
