#!/usr/bin/env python3
"""GO-026: agentflow_autostart.sh against a temporary HOME and fake npx, launchctl, curl and uname."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "agentflow_autostart.sh"
sys.path.insert(0, str(HERE))
import swarm  # noqa: E402


class Autostart(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="agentflow-"))
        self.home = self.tmp / "home"; self.home.mkdir()
        self.bin = self.tmp / "bin"; self.bin.mkdir()
        self.calls = self.tmp / "launchctl.log"
        self.fake("npx", "exit 0")
        # print answers only while loaded: after a bootstrap that no later bootout undid, as launchd does
        self.fake("launchctl", f'''echo "$*" >> "{self.calls}"
if [ "$1" = print ]; then
  case $(grep -E "^boot(strap|out)" "{self.calls}" | tail -n 1) in
    bootstrap*) printf "\\tstate = running\\n\\tpid = 100\\n"; exit 0;;
    *) exit 113;;
  esac
fi
exit 0''')
        # the agent (pid 100) starts the viewer (pid 101) once loaded; 999 is someone else's process
        self.fake("lsof", f'grep -E "^boot(strap|out)" "{self.calls}" 2>/dev/null | tail -n 1 | grep -q bootstrap && echo 101; exit 0')
        self.fake("ps", 'for a; do last=$a; done; case $last in 101) echo 100;; *) echo 1;; esac')
        # the fake viewer answers only once the agent is loaded, as the real one does
        self.fake("curl", f'grep -q bootstrap "{self.calls}" 2>/dev/null || exit 7; echo "<html><title>Agent Flow</title></html>"')
        self.fake("uname", 'echo Darwin')
        self.plist = self.home / "Library/LaunchAgents/com.moxywolf.agent-flow.plist"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake(self, name, body):
        p = self.bin / name
        p.write_text(f"#!/bin/sh\n{body}\n")
        p.chmod(0o755)

    def run_script(self, *args, **env):
        e = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin", "AGENT_FLOW_WAIT": "2", **env}
        return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=e)

    def test_install_writes_a_plist_for_the_pinned_package(self):
        r = self.run_script("install")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("http://127.0.0.1:61469", r.stdout)
        text = self.plist.read_text()
        self.assertIn(f"<string>{self.bin / 'npx'}</string>", text)
        self.assertIn(f"<string>{swarm.VIEWER_PACKAGE}</string>", text)
        self.assertIn("<string>--port</string><string>61469</string>", text)
        self.assertIn(f"<key>WorkingDirectory</key><string>{self.home}</string>", text)
        self.assertIn(f"<string>{self.bin}:/usr/bin", text)
        self.assertIn("bootstrap gui/", self.calls.read_text())
        if shutil.which("plutil"):
            self.assertEqual(subprocess.run(["plutil", "-lint", str(self.plist)]).returncode, 0)

    def test_the_port_can_be_changed(self):
        self.assertEqual(self.run_script("install", AGENT_FLOW_PORT="61999").returncode, 0)
        self.assertIn("<string>--port</string><string>61999</string>", self.plist.read_text())

    def test_install_fails_when_the_viewer_never_answers(self):
        self.fake("curl", "exit 7")
        r = self.run_script("install")
        self.assertEqual(r.returncode, 1)
        self.assertIn("agent-flow.log", r.stderr)

    def test_a_stalled_answer_cannot_stretch_the_wait(self):
        """Review F1: each probe carries -m with the time left, so a listener that never answers ends the wait."""
        self.fake("curl", 'while [ $# -gt 0 ]; do [ "$1" = -m ] && { sleep "$2"; exit 28; }; shift; done; sleep 60')
        start = time.monotonic()
        r = self.run_script("install")
        self.assertEqual(r.returncode, 1)
        self.assertLess(time.monotonic() - start, 10)

    def test_another_service_on_the_port_is_not_the_viewer(self):
        """Second review F1: a 200 from something else on the port is not success."""
        self.fake("curl", f'grep -q bootstrap "{self.calls}" 2>/dev/null || exit 7; echo "<html><title>Something else</title></html>"')
        r = self.run_script("install")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not answering", r.stderr)

    def test_a_port_already_held_is_refused_before_loading(self):
        """Second review round 2 and 3 F1: a viewer already holding the port, quick to answer or not, is not ours."""
        self.fake("lsof", "echo 999")
        r = self.run_script("install")
        self.assertEqual(r.returncode, 1)
        self.assertIn("in use by another process", r.stderr)
        self.assertNotIn("bootstrap", self.calls.read_text() if self.calls.exists() else "")

    def test_an_answer_from_a_process_the_agent_did_not_start_is_not_success(self):
        """Second review round 3 F1: a listener outside the agent's process tree never counts."""
        self.fake("lsof", f'grep -q bootstrap "{self.calls}" 2>/dev/null && echo 999; exit 0')
        self.fake("curl", "echo '<html><title>Agent Flow</title></html>'")
        r = self.run_script("install")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not answering", r.stderr)

    def test_no_probe_once_the_deadline_has_passed(self):
        """Review round 2 F1: with no time left the script never calls curl, so it can't pass -m 0 (no limit)."""
        self.fake("curl", f'echo "$*" >> "{self.tmp}/curl.log"; exit 7')
        r = self.run_script("install", AGENT_FLOW_WAIT="0")
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.tmp / "curl.log").exists())

    def test_status_probes_the_installed_port(self):
        """Review F3: status reads the port from the plist, not from this call's environment."""
        self.run_script("install", AGENT_FLOW_PORT="61999")
        self.fake("curl", f'echo "$*" >> "{self.tmp}/curl.log"; exit 0')
        self.assertEqual(self.run_script("status").returncode, 0)
        self.assertIn("127.0.0.1:61999", (self.tmp / "curl.log").read_text())

    def test_a_lingering_agent_is_waited_for_before_loading(self):
        """Found on Dorian's Mac: bootout returns before the old service is gone, and bootstrap then fails (5)."""
        self.run_script("install")
        # the old agent is still listed for two more prints after its bootout, then goes
        n = self.tmp / "lingers"; n.write_text("2")
        self.fake("launchctl", f'''echo "$*" >> "{self.calls}"
if [ "$1" = print ]; then
  left=$(cat "{n}"); if [ "$left" -gt 0 ]; then echo $((left - 1)) > "{n}"; exit 0; fi
  case $(grep -E "^boot(strap|out)" "{self.calls}" | tail -n 1) in
    bootstrap*) printf "\\tpid = 100\\n"; exit 0;; *) exit 113;;
  esac
fi
exit 0''')
        r = self.run_script("install")
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.calls.read_text().splitlines()
        last_out = max(i for i, l in enumerate(log) if l.startswith("bootout"))
        last_in = max(i for i, l in enumerate(log) if l.startswith("bootstrap"))
        self.assertGreaterEqual(sum(l.startswith("print") for l in log[last_out:last_in]), 3)

    def test_uninstall_removes_the_plist(self):
        self.run_script("install")
        r = self.run_script("uninstall")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.plist.exists())
        self.assertIn("bootout gui/", self.calls.read_text())

    def test_status_reports(self):
        self.run_script("install")
        r = self.run_script("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("state = running", r.stdout)

    def test_an_unknown_argument_exits_2(self):
        self.assertEqual(self.run_script("start").returncode, 2)

    def test_other_platforms_are_refused_and_nothing_is_written(self):
        self.fake("uname", "echo Linux")
        for cmd in ("install", "uninstall", "status"):
            r = self.run_script(cmd)
            self.assertEqual(r.returncode, 1, cmd)
            self.assertIn("macOS only", r.stderr)
        self.assertEqual(list(self.home.rglob("*")), [])
        self.assertFalse(self.calls.exists())

    def test_the_pin_matches_swarm(self):
        pin = re.search(r"^PKG=(\S+)$", SCRIPT.read_text(), re.M).group(1)
        self.assertEqual(pin, swarm.VIEWER_PACKAGE)


if __name__ == "__main__":
    unittest.main()
