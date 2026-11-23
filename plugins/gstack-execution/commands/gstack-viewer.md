---
description: Open or close the agent-flow viewer for the goal swarm that's running (GO-025): finds the run, starts swarm.py's viewer and gives you the address
allowed-tools: Bash
argument-hint: [stop] [<goal-id>]
---

Shows the swarm's agents live in the agent-flow viewer (`swarm.py viewer-start`, gstack-execution 0.113.0). It works only where the viewer does: a Mac with `npx`, from Claude Code or a desktop session on that Mac. From a cloud session `swarm.py` answers `viewer: unavailable`; say so once and stop.

Arguments: `$ARGUMENTS`. A first word `stop` is the verb; the word after it, or the only word when there's no `stop`, is a goal id.

1. **Find the run.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/goal_run.py" swarm-run [<goal-id>]`. With no id it prints the swarm folder of the one goal running a swarm. It reads only; it writes nothing.
   - It prints `REFUSED: ...` and exits 1: relay the line as written. When it names several running goals, ask which one with AskUserQuestion, listing the ids it named, then run this step again with the chosen id. When no goal is running, add one line: a viewer left from an ended goal is stopped by naming that goal (`/gstack-viewer stop <goal-id>`).
2. **Start or stop.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/swarm.py" viewer-start <path>`, or `viewer-stop <path>` for `stop`, with the path step 1 printed.
3. **Report** what `swarm.py` printed, as written: the address to open (`viewer: http://127.0.0.1:<port>`), `viewer: stopped`, `viewer: not running` or `viewer: unavailable ...`. Give the address as a link. Nothing else to add: the first start of agent-flow-app adds its own hooks to `~/.claude/settings.json`, which Dorian allowed (swarm-agent-view), and a missing viewer never stops the swarm.

Don't install, start or configure anything else, and don't change the run's files. Both scripts exit 0 when the viewer can't run; only step 1's refusal exits 1.
