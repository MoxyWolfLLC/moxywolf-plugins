# swarm-agent-view
1. add `viewer-start` and `viewer-stop` to swarm.py
   - `swarm.py viewer-start <run>` on a host where `SWARM_VIEWER_PLATFORM` (or the real platform) is `Darwin` and npx is on the path starts `npx --yes agent-flow-app@0.9.6 --no-open --port <port>` in the background and prints `viewer: http://127.0.0.1:<port>` on standard output, with exit code 0
   - the command passes no host or bind option, so the viewer's own default of 127.0.0.1 holds
   - `viewer-start` on any other platform, or with no npx, prints one line on standard error that starts `viewer: unavailable` and says the swarm is unaffected, prints nothing on standard output, and exits 0
   - `swarm.py viewer-stop <run>` ends the process that `viewer-start` started, prints `viewer: stopped` on standard output and exits 0; with no viewer running it prints `viewer: not running` on standard output and exits 0
   - the viewer's process id is kept in a file named `viewer.pid` in the run folder and never in swarm.json or swarm-events.jsonl, which neither command opens for writing
   - an unknown option after the run path prints a usage line on standard error and exits 2
   - swarm.py never opens `~/.claude/settings.json`
2. document the viewer in the gstack-goal command text
   - `commands/gstack-goal.md` has a short paragraph on `viewer-start` and `viewer-stop`: Mac only, address 127.0.0.1, optional, pinned at agent-flow-app 0.9.6
   - the paragraph says that the first start of agent-flow-app adds its hooks to the user's own `~/.claude/settings.json` and sends session events to a relay on 127.0.0.1
   - the paragraph says that a missing viewer never stops the swarm
3. move the plugin version
   - `plugins/gstack-execution/.claude-plugin/plugin.json` moves its version by one minor step
   - `.claude-plugin/marketplace.json` is not changed
   - no other path changes
