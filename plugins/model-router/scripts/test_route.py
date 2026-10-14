#!/usr/bin/env python3
"""MR-003.10: the hooks run as subprocesses with the hook JSON on stdin, the way the host calls them.
Nothing is imported from route.py."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "route.py"
ONTOLOGY = HERE.parent / "references" / "call-ontology.json"
ALL_CLASSES = ["read-file", "glob", "grep", "web-fetch", "web-search", "edit", "write", "coverage-script",
               "model-select-script", "reviewer-script", "git", "shell", "explore-subagent", "docs-subagent",
               "review-subagent", "build-subagent"]
FIXTURE_CALL = {
    "read-file": ("Read", {"file_path": "/a"}), "glob": ("Glob", {"pattern": "*"}), "grep": ("Grep", {"pattern": "x"}),
    "web-fetch": ("WebFetch", {"url": "https://x"}), "web-search": ("WebSearch", {"query": "q"}),
    "edit": ("Edit", {"file_path": "/a"}), "write": ("Write", {"file_path": "/a"}),
    "coverage-script": ("Bash", {"command": "node scripts/packet_coverage.mjs p.json DESIGN.md"}),
    "model-select-script": ("Bash", {"command": "node scripts/model_select.mjs recommend p.json DESIGN.md"}),
    "reviewer-script": ("Bash", {"command": "python3 peer_review.py round 2026-x"}),
    "git": ("Bash", {"command": "git status"}), "shell": ("Bash", {"command": "ls -la"}),
    "explore-subagent": ("Agent", {"subagent_type": "gstack-execution:explore", "prompt": "map the tree"}),
    "docs-subagent": ("Agent", {"subagent_type": "gstack-execution:docs", "prompt": "find the doc"}),
    "review-subagent": ("Agent", {"subagent_type": "gstack-execution:peer-review", "prompt": "review it"}),
    "build-subagent": ("Agent", {"subagent_type": "general-purpose", "description": "build it", "prompt": "change scripts/a.py and b.py"}),
}


class Stub(http.server.BaseHTTPRequestHandler):
    answers = {}
    seen = []
    fail = False

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.seen.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        if Stub.fail:
            self.send_response(500); self.end_headers(); return
        out = {"answers": {k: {"type": "boolean", "probability": float(Stub.answers.get(k, 0.1))} for k in body["questions"]},
               "usage": {"inputTokens": 7}}
        raw = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def log_message(self, *a):
        pass


class Hooks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mr003-")).resolve()
        self.sid = "s1"
        Stub.answers = {}; Stub.seen = []; Stub.fail = False

    def run_hook(self, cmd, payload, endpoint=None, **env):
        e = {k: v for k, v in os.environ.items() if k not in {"GSTACK_PEER_REVIEW_DIR", "JEV_ENDPOINT", "AI_GATEWAY_API_KEY", "GSTACK_AIGATEWAY_ENV"}}
        e.update(GSTACK_PEER_REVIEW_DIR=str(self.root), JEV_ENDPOINT=endpoint or self.endpoint, AI_GATEWAY_API_KEY="k-test"); e.update(env)
        t = time.monotonic()
        r = subprocess.run([sys.executable, str(SCRIPT), cmd], input=json.dumps(payload), capture_output=True, text=True, env=e, cwd=str(self.root))
        r.seconds = time.monotonic() - t
        return r

    def call(self, tool, tool_input, **kw):
        return self.run_hook("pre-tool-use", {"session_id": self.sid, "hook_event_name": "PreToolUse", "tool_name": tool,
                                              "tool_input": tool_input, "tool_use_id": "t1"}, **kw)

    def ledger(self):
        files = sorted((self.root / "model-routing").glob(f"*-{self.sid}.jsonl"))
        self.assertEqual(len(files), 1, files)
        return [json.loads(l) for l in files[0].read_text().splitlines() if l.strip()]

    def updated(self, r):
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return None
        return json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]

    # ---- MR-003.1: the table ----

    def test_the_table_ships_every_class_and_a_bad_table_is_refused(self):
        t = json.loads(ONTOLOGY.read_text())
        names = [c["class"] for c in t["classes"]]
        for c in ALL_CLASSES:
            self.assertIn(c, names)
        for c in t["classes"]:
            self.assertEqual(set(c), {"class", "tool", "match", "carries_model", "default_tier", "ask"}, c["class"])
            self.assertEqual(c["carries_model"], c["tool"] == "Agent" or c["class"].endswith("-script"), c["class"])
        bad = self.root / "bad.json"
        for mutate in ({"drop": "ask"}, {"tier": "huge"}):
            tt = json.loads(ONTOLOGY.read_text())
            if "drop" in mutate: del tt["classes"][0][mutate["drop"]]
            else: tt["classes"][0]["default_tier"] = mutate["tier"]
            bad.write_text(json.dumps(tt))
            r = subprocess.run([sys.executable, "-c",
                                f"import sys; sys.path.insert(0, {str(HERE)!r}); import route; t, why = route.load_table({str(bad)!r}); print(why)"],
                               capture_output=True, text=True)
            self.assertIn("ontology", r.stdout, r.stderr)
            self.assertTrue("lacks" in r.stdout or "default_tier" in r.stdout, r.stdout)

    # ---- MR-003.3: SessionStart ----

    def test_session_start_opens_the_ledger_and_refuses_without_a_table(self):
        r = self.run_hook("session-start", {"session_id": self.sid, "hook_event_name": "SessionStart", "source": "startup"})
        self.assertEqual(r.returncode, 0, r.stderr)
        first = self.ledger()[0]
        self.assertEqual((first["event"], first["routing"], first["ledger_source"]), ("session_start", "on", "env GSTACK_PEER_REVIEW_DIR"))
        self.assertTrue(first["ontology_version"])
        # no table: a copy of the plugin without its references directory
        plugin = self.root / "plugin"; (plugin / "scripts").mkdir(parents=True); (plugin / "references").mkdir()
        (plugin / "scripts" / "route.py").write_text(SCRIPT.read_text())
        e = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(self.root))
        r = subprocess.run([sys.executable, str(plugin / "scripts" / "route.py"), "session-start"], input=json.dumps({"session_id": "s2"}),
                           capture_output=True, text=True, env=e)
        self.assertEqual(r.returncode, 0)
        self.assertIn("routing is off for this session", r.stderr)
        self.assertIn("could not be read", r.stderr)
        rec = [json.loads(l) for l in sorted((self.root / "model-routing").glob("*-s2.jsonl"))[0].read_text().splitlines()]
        self.assertEqual(rec[0]["routing"], "off")
        # and a call in that session is recorded as refused, not routed
        r = subprocess.run([sys.executable, str(plugin / "scripts" / "route.py"), "pre-tool-use"],
                           input=json.dumps({"session_id": "s2", "tool_name": "Agent", "tool_input": {"subagent_type": "gstack-execution:explore"}}),
                           capture_output=True, text=True, env=e)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))
        rec = [json.loads(l) for l in sorted((self.root / "model-routing").glob("*-s2.jsonl"))[0].read_text().splitlines()]
        self.assertEqual(rec[-1]["event"], "refused")

    # ---- MR-003.4 and .5: classification by code, no Jev for the table path ----

    def test_every_shipped_class_classifies_its_fixture_and_unclassified_is_recorded_not_routed(self):
        for cls, (tool, tin) in FIXTURE_CALL.items():
            r = self.call(tool, tin)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self.ledger()[-1]["class"], cls, (cls, self.ledger()[-1]))
        r = self.call("Teleport", {"to": "mars"})
        self.assertEqual(self.updated(r), None)
        last = self.ledger()[-1]
        self.assertEqual((last["class"], last["routed"]), ("unclassified", False))
        self.assertNotIn("model", last)
        # the first line was written lazily, as a cloud session needs
        self.assertEqual((self.ledger()[0]["event"], self.ledger()[0]["source"]), ("session_start", "lazy"))

    def test_an_explore_launch_is_rewritten_to_haiku_by_the_table_without_jev(self):
        r = self.call("Agent", {"subagent_type": "gstack-execution:explore", "prompt": "map the tree", "description": "map"})
        self.assertEqual(self.updated(r)["model"], "haiku")
        self.assertEqual(self.updated(r)["prompt"], "map the tree")
        last = self.ledger()[-1]
        self.assertEqual((last["tier"], last["model"], last["decided_by"], last["routed"]), ("light", "haiku", "table", True))
        self.assertEqual(Stub.seen, [])
        self.assertLess(r.seconds, 2.0, r.seconds)
        # a call with no model choice is recorded unchanged
        r = self.call("Read", {"file_path": "/x"})
        self.assertEqual(self.updated(r), None)
        self.assertEqual({k: self.ledger()[-1][k] for k in ("class", "tool", "routed")}, {"class": "read-file", "tool": "Read", "routed": False})
        self.assertIn("ts", self.ledger()[-1])
        # a script class records the tier and applies nothing
        r = self.call("Bash", {"command": "node scripts/model_select.mjs recommend p.json DESIGN.md"})
        self.assertEqual(self.updated(r), None)
        self.assertEqual((self.ledger()[-1]["tier"], self.ledger()[-1]["routed"], self.ledger()[-1]["note"]), ("floor", False, "script selects its own model"))

    # ---- MR-003.6: the Jev path at the MR-002 bars ----

    def test_a_build_launch_asks_jev_and_is_rewritten_at_the_mr002_bars(self):
        cases = [({"risky": 0.70, "docs_only": 0.95}, "opus", "risky"),
                 ({"trust_boundary": 0.30}, "opus", "trust_boundary"),
                 ({"docs_only": 0.60, "has_tests": 0.10}, "haiku", "docs_only"),
                 ({"docs_only": 0.59}, "sonnet", "default")]
        for answers, model, rule in cases:
            Stub.answers = answers
            r = self.call("Agent", FIXTURE_CALL["build-subagent"][1])
            self.assertEqual(self.updated(r)["model"], model, (answers, r.stdout, r.stderr))
            last = self.ledger()[-1]
            self.assertEqual((last["decided_by"], last["rule"], last["routed"]), ("jev", rule, True))
            self.assertEqual(last["thresholds"], {"risky": 0.7, "upgrade": 0.3, "downgrade": 0.6, "has_tests": 0.5})
            self.assertEqual(set(last["answers"]), {"trust_boundary", "cross_file", "docs_only", "has_tests", "risky"})
        sent = Stub.seen[-1]
        self.assertEqual(sent["path"], "/evaluation-model")
        self.assertEqual(sent["headers"]["authorization"], "Bearer k-test")
        self.assertEqual(sent["headers"]["ai-model-id"], "typesafe-ai/jev")
        self.assertEqual(set(sent["body"]["questions"]), {"trust_boundary", "cross_file", "docs_only", "has_tests", "risky"})
        self.assertEqual(sent["body"]["state"]["prompt"], "change scripts/a.py and b.py")
        # an unclassified Agent call also asks
        Stub.answers = {"docs_only": 0.9}
        r = self.call("Agent", {"subagent_type": "something:new", "prompt": "read the docs"})
        self.assertEqual(self.updated(r)["model"], "haiku")
        self.assertEqual(self.ledger()[-1]["class"], "unclassified")
        # MR-001.7: a caller's explicit model stands and the advice is recorded
        r = self.call("Agent", {**FIXTURE_CALL["build-subagent"][1], "model": "sonnet"})
        self.assertEqual(self.updated(r), None)
        self.assertEqual((self.ledger()[-1]["caller_model"], self.ledger()[-1]["routed"]), ("sonnet", False))
        self.assertTrue(self.ledger()[-1]["decided_by"].startswith("caller (jev advised"))

    # ---- MR-003.7 ----

    def test_a_review_subagent_is_never_moved_below_floor(self):
        Stub.answers = {"docs_only": 0.95}
        r = self.call("Agent", FIXTURE_CALL["review-subagent"][1])
        self.assertEqual(self.updated(r)["model"], "opus")
        self.assertEqual((self.ledger()[-1]["tier"], self.ledger()[-1]["decided_by"]), ("floor", "table"))

    # ---- MR-003.8: Jev unreachable, forced failure ----

    def test_jev_unreachable_leaves_the_call_unchanged_and_a_failure_never_blocks(self):
        Stub.fail = True
        r = self.call("Agent", FIXTURE_CALL["build-subagent"][1])
        self.assertEqual(self.updated(r)["model"], "opus")        # the table default for build-subagent
        last = self.ledger()[-1]
        self.assertEqual((last["jev"], last["decided_by"]), ("unavailable", "table"))
        Stub.fail = False
        r = self.call("Agent", {"subagent_type": "something:new", "prompt": "x"}, endpoint="http://127.0.0.1:9")
        self.assertEqual((r.returncode, self.updated(r)), (0, None))   # unclassified: unchanged
        self.assertEqual(self.ledger()[-1]["jev"], "unavailable")
        # a forced internal failure: an unwritable ledger root
        ro = self.root / "ro"; ro.mkdir(); os.chmod(ro, 0o500)
        r = self.call("Read", {"file_path": "/x"}, GSTACK_PEER_REVIEW_DIR=str(ro))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))
        os.chmod(ro, 0o700)
        # malformed stdin
        r = subprocess.run([sys.executable, str(SCRIPT), "pre-tool-use"], input="not json", capture_output=True, text=True,
                           env=dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(self.root)))
        self.assertEqual(r.returncode, 0)

    # ---- MR-003.9: SessionEnd and score ----

    def test_session_end_writes_the_summary_and_score_counts(self):
        self.run_hook("session-start", {"session_id": self.sid, "source": "startup"})
        self.call("Read", {"file_path": "/a"}); self.call("Read", {"file_path": "/b"})
        self.call("Agent", FIXTURE_CALL["explore-subagent"][1])
        Stub.answers = {"cross_file": 0.9}
        self.call("Agent", FIXTURE_CALL["build-subagent"][1])
        self.call("Teleport", {})
        r = self.run_hook("session-end", {"session_id": self.sid, "reason": "other"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("model-router: 5 calls, 2 routed, 1 Jev consults, 1 unclassified", r.stdout)
        s = self.ledger()[-1]
        self.assertEqual(s["event"], "session_end")
        self.assertEqual({k: s[k] for k in ("calls", "routed", "jev_consults", "jev_unavailable", "unclassified", "refused")},
                         {"calls": 5, "routed": 2, "jev_consults": 1, "jev_unavailable": 0, "unclassified": 1, "refused": 0})
        self.assertEqual(s["by_class"], {"build-subagent": 1, "explore-subagent": 1, "read-file": 2, "unclassified": 1})
        self.assertEqual(s["tiers"], {"floor": 1, "light": 1})
        self.assertTrue(s["ontology_version"])
        r = subprocess.run([sys.executable, str(SCRIPT), "score", "--dir", str(self.root / "model-routing")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 files, 7 lines, 1 sessions, 5 calls, 1 unclassified", r.stdout)
        self.assertIn("read-file              2 calls, 0 routed, 0 Jev consults (0 unavailable)", r.stdout)
        self.assertIn("build-subagent         1 calls, 1 routed, 1 Jev consults (0 unavailable)", r.stdout)
        self.assertIn("tier floor     1 calls, 1 routed", r.stdout)
        self.assertIn("tier standard  0 calls, 0 routed", r.stdout)
        empty = self.root / "empty"; empty.mkdir()
        r = subprocess.run([sys.executable, str(SCRIPT), "score", "--dir", str(empty)], capture_output=True, text=True)
        self.assertIn("0 files, 0 lines, 0 sessions, 0 calls, 0 unclassified", r.stdout)
        self.assertIn("tier light     0 calls, 0 routed", r.stdout)

    def test_hooks_json_declares_the_three_events_running_route_py(self):
        h = json.loads((HERE.parent / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertEqual(set(h), {"SessionStart", "PreToolUse", "SessionEnd"})
        for ev, arg in (("SessionStart", "session-start"), ("PreToolUse", "pre-tool-use"), ("SessionEnd", "session-end")):
            cmd = h[ev][0]["hooks"][0]["command"]
            self.assertIn("scripts/route.py", cmd); self.assertIn(arg, cmd); self.assertTrue(cmd.endswith("exit 0"))


if __name__ == "__main__":
    unittest.main()
