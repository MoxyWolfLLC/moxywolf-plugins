# swarm-agent-view--s1
1. add `viewer-start` and `viewer-stop` to swarm.py
   - `swarm.py viewer-start <run>` on a host where the platform is `Darwin` and npx is on the path starts `npx --yes agent-flow-app@0.9.6 --no-open --port <port>` in the background and prints `viewer: http://127.0.0.1:<port>` on standard output, with exit code 0; the command picks a free port itself and has no port option
   - the platform is the value of the environment variable `SWARM_VIEWER_PLATFORM` when it is set, and the real platform otherwise
   - the command passes no host or bind option, so the viewer's own default of 127.0.0.1 holds
   - `viewer-start` on any other platform, or with no npx, prints one line on standard error that starts `viewer: unavailable` and says the swarm is unaffected, prints nothing on standard output, and exits 0; this check comes before the running-viewer check, so on such a host `viewer-start` never starts a viewer and never reports one
   - `viewer-start` on a Darwin host with npx and with a viewer already running prints that viewer's address and starts no second process
   - `swarm.py viewer-stop <run>` ends the process that `viewer-start` started, prints `viewer: stopped` on standard output and exits 0
   - a viewer that is not running prints `viewer: not running` on standard output and exits 0 from `viewer-stop` and signals no process; a viewer counts as not running when it has ended, has crashed, is a zombie process, or its process id now belongs to another process
   - on a Darwin host with npx, after a viewer crashed, `viewer-start` starts a new viewer and prints its address; the platform and npx check above still comes first
   - the viewer's process id, port and start time are kept in a file named `viewer.pid` in the run folder and never in swarm.json or swarm-events.jsonl, which neither command opens for writing
   - each command takes exactly one argument, the run folder; no run folder argument, an extra argument, or any option, in any position, prints a usage line on standard error, prints nothing on standard output and exits 2, before any other check
   - swarm.py never opens `~/.claude/settings.json`
   - the plugin version moves up by one patch step, counted from the version on the goal branch when this item starts (the items run in the order 1, 2, 3 and each one starts from the version the item before it merged): `plugins/gstack-execution/.claude-plugin/plugin.json` takes the new version, and the `gstack-execution` entry in `.claude-plugin/marketplace.json` takes the same version; the top-level version in `.claude-plugin/marketplace.json` does not move
2. document the viewer in the gstack-goal command text
   - `commands/gstack-goal.md` has a short paragraph on `viewer-start` and `viewer-stop`: Mac only, address 127.0.0.1, optional, pinned at agent-flow-app 0.9.6
   - the paragraph says that the first start of agent-flow-app adds its hooks to the user's own `~/.claude/settings.json` and sends session events to a relay on 127.0.0.1
   - the paragraph says that a missing viewer never stops the swarm
   - the plugin version moves up by one patch step, counted from the version on the goal branch when this item starts: `plugins/gstack-execution/.claude-plugin/plugin.json` takes the new version, and the `gstack-execution` entry in `.claude-plugin/marketplace.json` takes the same version; the top-level version in `.claude-plugin/marketplace.json` does not move
3. move the plugin version
   - the plugin version moves up by one minor step with the patch number set to 0, counted from the version on the goal branch when this item starts: `plugins/gstack-execution/.claude-plugin/plugin.json` takes the new version, and the `gstack-execution` entry in `.claude-plugin/marketplace.json` takes the same version
   - the top-level version in `.claude-plugin/marketplace.json` does not move
   - this item changes no path other than those two files
