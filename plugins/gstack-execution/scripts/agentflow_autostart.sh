#!/bin/bash
# GO-026: an always-on agent-flow viewer on this Mac, started at login by a LaunchAgent.
# It shows Claude Code sessions that run on this Mac under $HOME, on 127.0.0.1 only.
# It cannot show cloud sessions (Cowork, Claude Code on the web): they never run here.
# Usage: agentflow_autostart.sh [install|uninstall|status]   (default install; rerun install after a Node upgrade)
# The package pin must equal swarm.py's VIEWER_PACKAGE (test_agentflow_autostart.py checks it).
set -eu
LABEL=com.moxywolf.agent-flow
PKG=agent-flow-app@0.9.6
PORT=${AGENT_FLOW_PORT:-61469}
WAIT=${AGENT_FLOW_WAIT:-30}   # ponytail: seconds to wait for the first answer; tests shorten it
PLIST=$HOME/Library/LaunchAgents/$LABEL.plist
LOG=$HOME/Library/Logs/agent-flow.log

CMD=${1:-install}
case "$CMD" in install|uninstall|status) ;; *) echo "usage: $0 [install|uninstall|status]" >&2; exit 2 ;; esac
[ "$(uname)" = Darwin ] || { echo "agent-flow: macOS only" >&2; exit 1; }
DOMAIN=gui/$(id -u)

if [ "$CMD" = uninstall ]; then
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "agent-flow: removed (the hooks in ~/.claude/settings.json stay; they do nothing without a viewer)"
  exit 0
fi
if [ "$CMD" = status ]; then
  # the installed plist's port wins: a later status needn't repeat AGENT_FLOW_PORT
  INSTALLED=$(sed -n 's|.*<string>--port</string><string>\([0-9]*\)</string>.*|\1|p' "$PLIST" 2>/dev/null || true)
  PORT=${INSTALLED:-$PORT}
  launchctl print "$DOMAIN/$LABEL" 2>/dev/null | grep -E '^[[:space:]]*(state|pid) =' || echo "agent-flow: not loaded"
  curl -s -m 5 -o /dev/null -w "agent-flow: http://127.0.0.1:$PORT answers %{http_code}\n" "http://127.0.0.1:$PORT/" || echo "agent-flow: http://127.0.0.1:$PORT not answering"
  exit 0
fi

# launchd has no shell PATH, so the plist names npx by its full path and puts its folder on PATH.
NPX=$(command -v npx || true)
[ -n "$NPX" ] || NPX=$("${SHELL:-/bin/zsh}" -lic 'command -v npx' 2>/dev/null | tail -n 1)
[ -x "$NPX" ] || { echo "agent-flow: npx not found; install Node first" >&2; exit 1; }
NODE_BIN=$(dirname "$NPX")

mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$NPX</string><string>--yes</string><string>$PKG</string>
    <string>--no-open</string><string>--port</string><string>$PORT</string>
  </array>
  <key>WorkingDirectory</key><string>$HOME</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>$NODE_BIN:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
EOF
if command -v plutil >/dev/null; then plutil -lint "$PLIST" >/dev/null; fi
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
# the port must be free once our own agent is gone, or a later answer could come from someone else's process
n=0
while curl -s -m 1 -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null; do
  n=$((n + 1))
  [ "$n" -lt 5 ] || { echo "agent-flow: port $PORT is in use by another process; stop it or set AGENT_FLOW_PORT" >&2; exit 1; }
  sleep 1
done
launchctl bootstrap "$DOMAIN" "$PLIST"
END=$((SECONDS + WAIT))   # a deadline on elapsed time, so a stalled answer can't stretch the wait
while :; do
  LEFT=$((END - SECONDS))   # one clock read decides both whether to probe and the probe's limit
  [ "$LEFT" -gt 0 ] || break   # never curl -m 0: that means no limit at all
  # the page must be agent-flow's own, so an unrelated service on the port isn't taken for the viewer
  if curl -s -m "$LEFT" "http://127.0.0.1:$PORT/" 2>/dev/null | grep -q '<title>Agent Flow</title>'; then
    echo "agent-flow: running at http://127.0.0.1:$PORT (starts at every login)"; exit 0
  fi
  sleep 1
done
echo "agent-flow: loaded but not answering on port $PORT after ${WAIT}s; see $LOG" >&2
exit 1
