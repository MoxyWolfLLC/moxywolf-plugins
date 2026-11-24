#!/usr/bin/env python3
"""GO-026: agentflow_autostart.sh against a temporary HOME and fake npx, launchctl, curl and uname."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
        self.fake("launchctl", f'echo "$*" >> "{self.calls}"; [ "$1" = print ] && echo "	state = running"; exit 0')
        self.fake("curl", 'exit 0')
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

    def test_uninstall_removes_the_plist(self):
        self.run_script("install")
        r = self.run_script("uninstall")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.plist.exists())
        self.assertIn("bootout gui/", self.calls.read_text())

    def test_status_reports(self):
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
