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
               "review-subagent", "build-subagent", "department-subagent"]
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
    "department-subagent": ("Agent", {"subagent_type": "finance:finance", "description": "margin", "prompt": "what is the margin"}),
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
                                              "tool_input": tool_input, "tool_use_id": "t1", "cwd": str(self.root)}, **kw)

    def plugin_copy(self, name):
        plugin = self.root / f"plugin-{name}"; (plugin / "scripts").mkdir(parents=True); (plugin / "references").mkdir()
        (plugin / "scripts" / "route.py").write_text(SCRIPT.read_text())
        return plugin

    def run_plugin(self, plugin, cmd, payload):
        e = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(self.root), JEV_ENDPOINT=self.endpoint, AI_GATEWAY_API_KEY="k-test")
        return subprocess.run([sys.executable, str(plugin / "scripts" / "route.py"), cmd], input=json.dumps(payload), capture_output=True, text=True, env=e)

    def session_lines(self, sid):
        files = sorted((self.root / "model-routing").glob(f"*-{sid}.jsonl"))
        self.assertEqual(len(files), 1, files)
        return [json.loads(l) for l in files[0].read_text().splitlines() if l.strip()]

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
        # F1 (review 20261014-014833): every malformed table is a SessionStart refusal, run as the host runs it
        cases = [("drop-ask", lambda t: t["classes"][0].pop("ask"), "lacks"),
                 ("bad-tier", lambda t: t["classes"][0].update(default_tier="huge"), "default_tier"),
                 ("null-entry", lambda t: t["classes"].append(None), "not an object"),
                 ("bad-regex", lambda t: t["classes"][-1].update(match={"subagent_type": "["}), "not a regex"),
                 ("string-bool", lambda t: t["classes"][0].update(ask="yes"), "boolean"),
                 ("not-json", None, "could not be read")]
        for name, mutate, text in cases:
            plugin = self.plugin_copy(name)
            if mutate is None:
                (plugin / "references" / "call-ontology.json").write_text("{not json")
            else:
                tt = json.loads(ONTOLOGY.read_text()); mutate(tt)
                (plugin / "references" / "call-ontology.json").write_text(json.dumps(tt))
            r = self.run_plugin(plugin, "session-start", {"session_id": name, "source": "startup"})
            self.assertEqual(r.returncode, 0, name)
            self.assertIn("routing is off for this session", r.stderr, name); self.assertIn(text, r.stderr, name)
            rec = self.session_lines(name)
            self.assertEqual((rec[0]["event"], rec[0]["routing"]), ("session_start", "off"), name)
            self.assertIn(text, rec[0]["why"])
            r = self.run_plugin(plugin, "pre-tool-use", {"session_id": name, "tool_name": "Agent", "tool_input": {"subagent_type": "gstack-execution:explore"}})
            self.assertEqual((r.returncode, r.stdout.strip()), (0, ""), name)
            self.assertEqual(self.session_lines(name)[-1]["event"], "refused", name)

    # ---- MR-003.3: SessionStart ----

    def test_session_start_opens_the_ledger_and_refuses_without_a_table(self):
        r = self.run_hook("session-start", {"session_id": self.sid, "hook_event_name": "SessionStart", "source": "startup"})
        self.assertEqual(r.returncode, 0, r.stderr)
        first = self.ledger()[0]
        self.assertEqual((first["event"], first["routing"], first["ledger_source"]), ("session_start", "on", "env GSTACK_PEER_REVIEW_DIR"))
        self.assertTrue(first["ontology_version"])
        # no table at all: a copy of the plugin without its ontology
        plugin = self.plugin_copy("s2")
        r = self.run_plugin(plugin, "session-start", {"session_id": "s2"})
        self.assertEqual(r.returncode, 0)
        self.assertIn("routing is off for this session", r.stderr); self.assertIn("could not be read", r.stderr)
        self.assertEqual(self.session_lines("s2")[0]["routing"], "off")
        r = self.run_plugin(plugin, "pre-tool-use", {"session_id": "s2", "tool_name": "Agent", "tool_input": {"subagent_type": "gstack-execution:explore"}})
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))
        self.assertEqual(self.session_lines("s2")[-1]["event"], "refused")
        # F2 (review 20261014-014833): the table restored mid-session does not turn routing back on
        (plugin / "references" / "call-ontology.json").write_text(ONTOLOGY.read_text())
        r = self.run_plugin(plugin, "pre-tool-use", {"session_id": "s2", "tool_name": "Agent", "tool_input": {"subagent_type": "gstack-execution:explore"}})
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))
        last = self.session_lines("s2")[-1]
        self.assertEqual((last["event"], last["why"]), ("refused", "routing is off for this session"))
        # round 2: a second SessionStart (compact, resume) with the table restored does not turn it back on
        r = self.run_plugin(plugin, "session-start", {"session_id": "s2", "source": "compact"})
        self.assertEqual(r.returncode, 0); self.assertIn("refused earlier in this session", r.stderr)
        self.assertEqual((self.session_lines("s2")[-1]["routing"], self.session_lines("s2")[-1]["source"]), ("off", "compact"))
        r = self.run_plugin(plugin, "pre-tool-use", {"session_id": "s2", "tool_name": "Agent", "tool_input": {"subagent_type": "gstack-execution:explore"}})
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))
        self.assertEqual(self.session_lines("s2")[-1]["event"], "refused")
        # a new session on the restored table routes normally
        r = self.run_plugin(plugin, "session-start", {"session_id": "s2b", "source": "startup"})
        self.assertEqual(self.session_lines("s2b")[0]["routing"], "on")
        r = self.run_plugin(plugin, "pre-tool-use", {"session_id": "s2b", "tool_name": "Agent", "tool_input": {"subagent_type": "gstack-execution:explore", "prompt": "x"}})
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]["model"], "haiku")
        # a call before any SessionStart, with no table, opens the ledger off (cloud session) and stays off
        plugin3 = self.plugin_copy("s3")
        r = self.run_plugin(plugin3, "pre-tool-use", {"session_id": "s3", "tool_name": "Read", "tool_input": {}})
        self.assertEqual(r.returncode, 0)
        self.assertEqual([l["event"] for l in self.session_lines("s3")], ["session_start", "refused"])
        self.assertEqual(self.session_lines("s3")[0]["routing"], "off")

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
        # F4 (review 20261014-014833): a forced internal failure with a writable ledger leaves the hook_error line
        before = len(self.ledger())
        r = self.call("Agent", FIXTURE_CALL["explore-subagent"][1], MODEL_ROUTER_FORCE_ERROR="1")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))     # unchanged input: no updatedInput at all
        err = self.ledger()[-1]
        self.assertEqual(len(self.ledger()), before + 1)
        self.assertEqual((err["event"], err["cmd"], err["tool"]), ("hook_error", "pre-tool-use", "Agent"))
        self.assertIn("RuntimeError: forced by MODEL_ROUTER_FORCE_ERROR", err["error"])
        # and an unwritable ledger root still fails open: exit 0, nothing on stdout
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
        Stub.answers = {"docs_only": 0.9}
        self.call("Agent", {"subagent_type": "something:new", "prompt": "read"})   # unclassified, routed by Jev to light
        r = self.run_hook("session-end", {"session_id": self.sid, "reason": "other"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("model-router: 6 calls, 3 routed, 2 Jev consults, 2 unclassified", r.stdout)
        s = self.ledger()[-1]
        self.assertEqual(s["event"], "session_end")
        self.assertEqual({k: s[k] for k in ("calls", "routed", "jev_consults", "jev_unavailable", "unclassified", "refused")},
                         {"calls": 6, "routed": 3, "jev_consults": 2, "jev_unavailable": 0, "unclassified": 2, "refused": 0})
        self.assertEqual(s["by_class"], {"build-subagent": 1, "explore-subagent": 1, "read-file": 2, "unclassified": 2})
        self.assertEqual(s["tiers"], {"floor": 1, "light": 2})
        self.assertTrue(s["ontology_version"])
        r = subprocess.run([sys.executable, str(SCRIPT), "score", "--dir", str(self.root / "model-routing")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 files, 8 lines, 1 sessions, 6 calls, 2 unclassified", r.stdout)
        self.assertIn("read-file              2 calls, 0 routed, 0 Jev consults (0 unavailable), 0 unclassified", r.stdout)
        self.assertIn("build-subagent         1 calls, 1 routed, 1 Jev consults (0 unavailable), 0 unclassified", r.stdout)
        self.assertIn("unclassified           2 calls, 1 routed, 1 Jev consults (0 unavailable), 2 unclassified", r.stdout)
        # F3 (review 20261014-014833): the unclassified Agent launch Jev routed to light shows in light's row
        self.assertIn("tier floor     1 calls, 1 routed, 1 Jev consults (0 unavailable), 0 unclassified", r.stdout)
        self.assertIn("tier light     2 calls, 2 routed, 1 Jev consults (0 unavailable), 1 unclassified", r.stdout)
        self.assertIn("tier standard  0 calls, 0 routed, 0 Jev consults (0 unavailable), 0 unclassified", r.stdout)
        empty = self.root / "empty"; empty.mkdir()
        r = subprocess.run([sys.executable, str(SCRIPT), "score", "--dir", str(empty)], capture_output=True, text=True)
        self.assertIn("0 files, 0 lines, 0 sessions, 0 calls, 0 unclassified", r.stdout)
        self.assertIn("tier light     0 calls, 0 routed, 0 Jev consults (0 unavailable), 0 unclassified", r.stdout)

    # ---- CS-007: department on the line, security at the floor, the after-action report ----

    def cos_run(self, verb, *rest, sid=None):
        """The /cos step runs `route.py cos-run ...` as a Bash call; the hook sees that call go by."""
        cmd = f'python3 "$PLUGIN/scripts/route.py" cos-run {verb} ' + " ".join(rest)
        sid, self.sid = self.sid, (sid or self.sid)
        r = self.call("Bash", {"command": cmd})
        self.sid = sid
        return r

    def test_a_department_launch_carries_its_department_and_the_run_id_of_its_own_session(self):
        # the unknown of review 20261014-082908: a shell export never reaches the hook process, and F12: a
        # project-wide marker mixes sessions. The hook records the `cos-run start` command it sees, per session.
        r = subprocess.run([sys.executable, str(SCRIPT), "cos-run", "start", "2026-10-14-margin"], capture_output=True, text=True, cwd=str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr); self.assertIn("recorded by the model-router hook", r.stdout)
        self.assertFalse((self.root / ".gstack").exists())      # no shared file anywhere
        self.cos_run("start", "2026-10-14-margin")
        self.assertEqual((self.ledger()[-2]["event"], self.ledger()[-2]["cos_run"], self.ledger()[-1]["class"]), ("cos_run_start", "2026-10-14-margin", "shell"))
        Stub.answers = {"docs_only": 0.2}
        r = self.call("Agent", FIXTURE_CALL["department-subagent"][1])
        self.assertEqual(self.updated(r)["model"], "sonnet")
        last = self.ledger()[-1]
        self.assertEqual((last["class"], last["department"], last["cos_run"], last["decided_by"]), ("department-subagent", "finance", "2026-10-14-margin", "jev"))
        self.assertEqual((last["applied_model"], last["floor_rule"]), ("sonnet", False))
        # F12: a second session in the same project starts its own run; neither sees the other's
        self.cos_run("start", "2026-10-14-hiring", sid="s9")
        r = self.call("Agent", FIXTURE_CALL["department-subagent"][1])
        self.assertEqual(self.ledger()[-1]["cos_run"], "2026-10-14-margin")
        self.cos_run("end", sid="s9")
        r = self.call("Agent", FIXTURE_CALL["department-subagent"][1])
        self.assertEqual(self.ledger()[-1]["cos_run"], "2026-10-14-margin")   # s9's end did not end s1's run
        self.sid = "s9"
        r = self.call("Agent", FIXTURE_CALL["department-subagent"][1])
        self.assertNotIn("cos_run", self.ledger()[-1]); self.sid = "s1"
        # F14 and the three rounds of review 20261014-085739: only the whole command being the invocation counts;
        # anything that merely contains it (a search, an echo, a chain, a quoted fragment, a heredoc) changes nothing
        for cmd in ("rg -n 'route.py cos-run end' plugins", "grep route.py cos-run end file", "echo route.py cos-run start fake",
                    "echo python3 route.py cos-run end", "echo 'a; python3 route.py cos-run end; b'", "echo prefix'; python3 route.py cos-run end; suffix'",
                    "echo ';' python3 route.py cos-run end ';'", "echo \\; python3 route.py cos-run end", 'echo "&&" python3 route.py cos-run start z',
                    "cd /p && python3 plugins/model-router/scripts/route.py cos-run end", "python3 route.py cos-run end; ls",
                    "# python3 route.py cos-run end", "#route.py cos-run end", "'#route.py' cos-run end", "cat <<'EOF'\npython3 route.py cos-run end\nEOF\n", "ls\npython3 route.py cos-run end",
                    "python3 -c \"print(1)\" route.py cos-run end"):
            self.call("Bash", {"command": cmd})
            self.assertNotIn(self.ledger()[-1].get("event"), ("cos_run_start", "cos_run_end"))
            self.assertNotEqual(self.ledger()[-2].get("event"), "cos_run_end", cmd)
        r = self.call("Agent", FIXTURE_CALL["department-subagent"][1])
        self.assertEqual(self.ledger()[-1]["cos_run"], "2026-10-14-margin")
        # the invocation alone, with a quoted path and a trailing newline, starts a new run
        self.call("Bash", {"command": "python3 'plugins/model-router/scripts/route.py' cos-run start 2026-10-14-second\n"})
        r = self.call("Agent", FIXTURE_CALL["department-subagent"][1])
        self.assertEqual(self.ledger()[-1]["cos_run"], "2026-10-14-second")
        # end, then a call without a run; the hook never invents one
        self.cos_run("end")
        r = self.call("Read", {"file_path": "/x"})
        self.assertNotIn("cos_run", self.ledger()[-1])
        # COS_RUN_ID in the environment is an explicit override for runners
        r = self.call("Agent", {**FIXTURE_CALL["department-subagent"][1], "model": "haiku"}, COS_RUN_ID="env-run")
        self.assertEqual(self.updated(r), None)
        last = self.ledger()[-1]
        self.assertEqual((last["applied_model"], last["caller_model"], last["floor_rule"], last["cos_run"]), ("haiku", "haiku", False, "env-run"))

    def test_the_security_department_is_never_moved_below_floor(self):
        Stub.answers = {"docs_only": 0.95}
        r = self.call("Agent", {"subagent_type": "security:security", "prompt": "read the policy"})
        self.assertEqual(self.updated(r)["model"], "opus")
        last = self.ledger()[-1]
        self.assertEqual((last["department"], last["tier"], last["floor_locked_from"]), ("security", "floor", "light"))
        self.assertEqual((last["applied_model"], last["floor_rule"]), ("opus", True))   # F5: the lock is a floor rule, written here

    def aar(self, d, date):
        r = subprocess.run([sys.executable, str(SCRIPT), "aar", "--dir", str(d), "--date", date], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_aar_on_an_empty_day_reads_zero_and_decides_none(self):
        empty = self.root / "empty"; empty.mkdir()
        out = self.aar(empty, "2026-10-13")
        self.assertIn("Read 0 files and 0 lines dated 2026-10-13", out)
        self.assertIn("Zero lines read. That is not a clean day", out)
        self.assertNotIn("clean day.", out.replace("not a clean day", ""))
        self.assertIn("| (none) | 0 | 0 | 0 | 0 |", out)
        self.assertIn("| opus (floor) | 0 | 0 | 0/0 (no observations) | 0/0 (no observations) | 0/0 (no observations) | 0/0 (no observations) |", out)
        self.assertIn("## Decision\n\nDecision: none this day; the counts are below the bar.", out)
        self.assertEqual(out.count("Decision:"), 1)

    def test_aar_on_a_fixture_day_counts_usage_by_the_tags_written_at_launch_and_decides_once(self):
        d = self.root / "model-routing"; d.mkdir()
        day = "2026-10-13"
        def line(ts=f"{day}T10:00:00Z", **kw):
            base = {"ts": ts, "class": "department-subagent", "tool": "Agent", "routed": True, "decided_by": "jev", "rule": "default",
                    "tier": "standard", "model": "sonnet", "applied_model": "sonnet", "floor_rule": False}
            base.update(kw); return json.dumps(base)
        sess = [json.dumps({"ts": f"{day}T09:00:00Z", "event": "session_start", "routing": "on"}),
                line(department="finance", cos_run="r1", subagent_type="finance:finance"),
                line(department="sales-department", cos_run="r1", subagent_type="sales-department:sales-department"),
                # F5: the security lock as the hook writes it: Jev said docs_only, the lock put it on the floor
                line(department="security", cos_run="r2", subagent_type="security:security", tier="floor", model="opus", applied_model="opus",
                     rule="docs_only", floor_locked_from="light", floor_rule=True),
                line(department="finance", cos_run="r2", subagent_type="finance:finance"),
                # F2: the router advised haiku, the caller launched sonnet: counted as sonnet
                line(department="people", cos_run="r2", subagent_type="people:people", routed=False, tier="light", model="haiku",
                     caller_model="sonnet", applied_model="sonnet", decided_by="caller (jev advised haiku)"),
                # a script class carries advice, never an applied model: not a launch
                json.dumps({"ts": f"{day}T10:10:00Z", "class": "model-select-script", "tool": "Bash", "routed": False, "tier": "floor", "model": "opus", "note": "script selects its own model"}),
                json.dumps({"ts": f"{day}T10:30:00Z", "class": "read-file", "tool": "Read", "routed": False}),
                json.dumps({"ts": f"{day}T10:31:00Z", "class": "unclassified", "tool": "Teleport", "routed": False}),
                # F3: the same session crosses midnight; the next day's calls belong to the next day
                line(ts="2026-10-14T00:05:00Z", department="pmo", cos_run="r3", subagent_type="pmo:pmo")]
        (d / "20261013-s1.jsonl").write_text("\n".join(sess) + "\n")
        (d / "20261012-s0.jsonl").write_text(line(ts="2026-10-12T10:00:00Z", department="pmo", cos_run="r0") + "\n")
        checks = [{"ts": f"{day}T10:05:00Z", "cos_run": "r1", "department": "finance", "model": "sonnet", "doc": "f.md", "passed": True, "failing_lines": []},
                  {"ts": f"{day}T10:06:00Z", "cos_run": "r1", "department": "sales-department", "model": "sonnet", "doc": "s.md", "passed": False, "failing_lines": [4]},
                  {"ts": f"{day}T10:07:00Z", "cos_run": "r1", "department": "sales-department", "model": "sonnet", "doc": "s2.md", "passed": False, "failing_lines": [2]},
                  {"ts": f"{day}T10:20:00Z", "cos_run": "r2", "department": "security", "model": "opus", "doc": "sec.md", "passed": True, "failing_lines": []},
                  {"ts": f"{day}T10:21:00Z", "cos_run": "r2", "department": "finance", "model": None, "doc": "f2.md", "passed": True, "failing_lines": []},
                  {"ts": "2026-10-12T10:21:00Z", "cos_run": "r0", "department": "pmo", "model": "sonnet", "doc": "p.md", "passed": False, "failing_lines": [1]}]
        (d / "claim-checks.jsonl").write_text("\n".join(json.dumps(c) for c in checks) + "\n")
        ms = self.root / "model-selection"; ms.mkdir()
        (ms / "o-r.jsonl").write_text("\n".join([
            json.dumps({"recorded_at": f"{day}T11:00:00Z", "declared_tier": "floor", "recommendation": {"tier": "floor", "rule": "cross_file"}, "outcome": {"blocking_findings": 4, "rounds_used": 3}}),
            # F4: no declared tier; the recommendation says floor, and that is not used
            json.dumps({"recorded_at": f"{day}T11:30:00Z", "recommendation": {"tier": "floor", "rule": "cross_file"}, "outcome": {"blocking_findings": 9}}),
            json.dumps({"recorded_at": "2026-10-12T11:00:00Z", "declared_tier": "floor", "outcome": {"blocking_findings": 0}})]) + "\n")
        out = self.aar(d, day)
        self.assertIn("Read 4 files and 16 lines dated 2026-10-13: 8 calls across 2 session ledgers, 5 department dispatches, 5 claim checks, 2 model-selection lines.", out)
        self.assertIn("harder tasks go to stronger models by design", out)
        self.assertIn("| department-subagent | 5 | 4 | 0 | 0 |", out)
        self.assertIn("| model-select-script | 1 | 0 | 0 | 0 |", out)
        self.assertIn("| unclassified | 1 | 0 | 0 | 1 |", out)
        # by model: launches that actually ran on it; dispatches as the denominator for failures; the lock counted as a floor rule
        self.assertIn("| sonnet (standard) | 4 | 4 | 0/4 (0%), too few to read (n=4 < 10), a lead | 2 over 4 dispatches, too few to read (n=4 < 10), a lead | 1/3 (33%), too few to read (n=3 < 10), a lead | 0/0 (no observations) |", out)
        self.assertIn("| opus (floor) | 1 | 1 | 1/1 (100%), too few to read (n=1 < 10), a lead | 0 over 1 dispatches, too few to read (n=1 < 10), a lead | 1/1 (100%), too few to read (n=1 < 10), a lead | 4 over 1 reviews, too few to read (n=1 < 10), a lead |", out)
        self.assertIn("| haiku (light) | 0 | 0 |", out)        # advised haiku, launched sonnet: no haiku usage
        self.assertIn("Untagged, counted apart: 1 claim-check lines without a model or department; 1 model-selection lines without a declared tier.", out)
        # by department: send-backs over dispatches (two failed checks on one dispatch is 2 over 1), escalation on the second failure
        self.assertIn("| sales-department | 1 | sonnet | 0/2 (0%), too few to read (n=2 < 10), a lead | 2 over 1 dispatches, too few to read (n=1 < 10), a lead | 1 over 1 runs, too few to read (n=1 < 10), a lead |", out)
        self.assertIn("| finance | 2 | sonnet | 2/2 (100%), too few to read (n=2 < 10), a lead | 0 over 2 dispatches, too few to read (n=2 < 10), a lead | 0 over 2 runs, too few to read (n=2 < 10), a lead |", out)
        self.assertIn("| people | 1 | sonnet | 0/0 (no observations) | 0 over 1 dispatches", out)
        self.assertNotIn("| pmo |", out)                       # r3 is the next day's; r0 is the day before's
        self.assertIn("- r1: finance, sales-department; models sonnet; escalated (sales-department)", out)
        self.assertIn("- r2: finance, people, security; models opus, sonnet; done", out)
        for word in ("because", "caused", "due to"):
            self.assertNotIn(word, out)
        self.assertIn("## Decision\n\nDecision: none this day; the counts are below the bar.", out)
        self.assertEqual(out.count("Decision:"), 1)
        # the next day's report holds the post-midnight dispatch, and nothing from the 13th
        out14 = self.aar(d, "2026-10-14")
        self.assertIn("1 department dispatches, 0 claim checks", out14)
        self.assertIn("| pmo | 1 | sonnet |", out14); self.assertNotIn("sales-department", out14)
        # ten dispatches with six failed checks: the decision names the department's gate over its dispatches
        extra = [line(ts=f"{day}T12:0{i % 10}:00Z", department="pmo", cos_run=f"q{i}", subagent_type="pmo:pmo", applied_model="haiku", model="haiku", tier="light") for i in range(12)]
        with open(d / "20261013-s1.jsonl", "a") as f:
            f.write("\n".join(extra) + "\n")
        more = [{"ts": f"{day}T12:0{i % 10}:30Z", "cos_run": f"q{i}", "department": "pmo", "model": "haiku", "doc": "p.md", "passed": i % 2 == 0, "failing_lines": [1]} for i in range(12)]
        with open(d / "claim-checks.jsonl", "a") as f:
            f.write("\n".join(json.dumps(c) for c in more) + "\n")
        out = self.aar(d, day)
        self.assertIn("| pmo | 12 | haiku | 6/12 (50%) | 6 over 12 dispatches | 0 over 12 runs |", out)
        self.assertIn("Decision: change the pmo department's return contract or claim-check form: 6 send-backs over 12 dispatches.", out)
        self.assertEqual(out.count("Decision:"), 1)
        # the ontology candidate's bar is over the calls observed: 20 calls with 2 unclassified is a decision on its own day
        d2 = self.root / "mr2"; d2.mkdir()
        rows = [json.dumps({"ts": "2026-10-15T01:00:00Z", "class": "read-file", "tool": "Read", "routed": False})] * 18 + \
               [json.dumps({"ts": "2026-10-15T01:00:00Z", "class": "unclassified", "tool": "Teleport", "routed": False})] * 2
        (d2 / "20261015-s1.jsonl").write_text("\n".join(rows) + "\n")
        out = self.aar(d2, "2026-10-15")
        self.assertIn("Decision: change the ontology: 2 of 20 calls were unclassified; add the missing class.", out)
        (d2 / "20261015-s1.jsonl").write_text("\n".join(rows[:9]) + "\n")   # under ten calls: a lead, no decision
        self.assertIn("Decision: none this day; the counts are below the bar.", self.aar(d2, "2026-10-15"))

    def test_hooks_json_declares_the_three_events_running_route_py(self):
        h = json.loads((HERE.parent / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertEqual(set(h), {"SessionStart", "PreToolUse", "SessionEnd"})
        for ev, arg in (("SessionStart", "session-start"), ("PreToolUse", "pre-tool-use"), ("SessionEnd", "session-end")):
            cmd = h[ev][0]["hooks"][0]["command"]
            self.assertIn("scripts/route.py", cmd); self.assertIn(arg, cmd); self.assertTrue(cmd.endswith("exit 0"))


if __name__ == "__main__":
    unittest.main()
