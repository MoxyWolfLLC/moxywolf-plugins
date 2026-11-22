#!/usr/bin/env python3
"""GO-017: the swarm coordinator against temporary repositories and controlled worker responses."""
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import swarm  # noqa: E402


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout.strip()


class Swarm(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="swarm-"))
        self.repo = self.tmp / "repo"; self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@t"); git(self.repo, "config", "user.name", "t")
        (self.repo / "contract.json").write_text('{"v": 1}\n')
        git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.goal = self.tmp / "goal"; self.goal.mkdir()
        self.run = self.tmp / "run"

    def plan(self, items, order=(), max_workers=3, n=None):
        n = n or len(items)
        (self.goal / "PLAN.md").write_text("".join(f"{k}. item {k}\n   - works\n" for k in range(1, n + 1)))
        if items is not None:
            (self.goal / "DEPS.json").write_text(json.dumps({"version": 1, "max_workers": max_workers, "order": list(order),
                                                             "items": {str(k + 1): v for k, v in enumerate(items)}}))

    def item(self, id, writes, start=(), integ=(), est=1.0):
        return {"id": id, "writes": list(writes), "start_after": list(start), "integrate_after": list(integ), "estimate_usd": est}

    def work(self, claim, files, sleep=0.0):
        """A controlled worker: its own worktree and branch from the pinned base, writes, commits, returns the head."""
        wt = self.tmp / f"wt-{claim['id']}-{claim['attempt']}"
        git(self.repo, "worktree", "add", "-q", "-b", claim["branch"], str(wt), claim["base"])
        time.sleep(sleep)
        for f in files:
            (wt / f).parent.mkdir(parents=True, exist_ok=True); (wt / f).write_text(f"{claim['id']}\n")
        git(wt, "add", "."); git(wt, "commit", "-qm", claim["id"])
        return git(wt, "rev-parse", "HEAD")

    def merge(self, iid):
        st = swarm.load(self.run)["items"][iid]
        git(self.repo, "merge", "-q", "--ff-only", st["evidence"]["head"]) if False else \
            git(self.repo, "merge", "-q", "--no-ff", "-m", f"merge {iid}", st["evidence"]["head"])
        sha = git(self.repo, "rev-parse", "HEAD"); swarm.merged(self.run, iid, sha); return sha

    def finish(self, claim, files, cost=None):
        swarm.launched(self.run, claim["id"], claim["attempt"])
        head = self.work(claim, files)
        r = swarm.result(self.run, claim["id"], claim["attempt"], head, self.repo, "passed", cost)
        return head, r

    def test_v1_explicit_width_and_legacy_defaults(self):
        self.plan([self.item(f"i{i}", [f"{i}.py"]) for i in range(41)], max_workers=40)
        swarm.init(self.run, self.goal, self.base, 41)
        self.assertEqual(len(swarm.tick(self.run)["dispatch"]), 40)
        deps = self.goal / "DEPS.json"
        d = json.loads(deps.read_text())
        d.pop("max_workers")
        deps.write_text(json.dumps(d))
        default = self.tmp / "default"
        swarm.init(default, self.goal, self.base, 41)
        self.assertEqual(len(swarm.tick(default)["dispatch"]), 3)
        for invalid in (0, True, "4"):
            with self.subTest(invalid=invalid):
                d["max_workers"] = invalid
                deps.write_text(json.dumps(d))
                with self.assertRaisesRegex(ValueError, "max_workers"):
                    swarm.load_plan(self.goal)

    def test_v1_refusal_counts_running_and_sent_and_clears_unsent(self):
        self.plan([self.item(f"i{i}", [f"{i}.py"]) for i in range(6)], max_workers=6)
        swarm.init(self.run, self.goal, self.base, 6)
        claims = swarm.tick(self.run)["dispatch"]
        for c in claims[:4]:
            self.assertEqual(swarm.launch_sent(self.run, c["id"], c["attempt"]), "launch")
        for c in claims[:2]:
            swarm.launched(self.run, c["id"], c["attempt"])
        swarm.launch_failed(self.run, "i2", 1, "capacity", host_refused=True)
        state = swarm.load(self.run)
        self.assertEqual([v["status"] for v in state["items"].values()],
                         ["running", "running", "pending", "sent", "pending", "pending"])
        self.assertEqual(swarm.status(self.run)["reserved"], 3)
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])
        other = self.tmp / "other"
        swarm.init(other, self.goal, self.base, 6)
        self.assertEqual(len(swarm.tick(other)["dispatch"]), 3)

    def test_v1_halt_keeps_sent_reservation_and_blocks_unsent(self):
        self.plan([self.item(f"i{i}", [f"{i}.py"]) for i in range(4)], max_workers=4)
        swarm.init(self.run, self.goal, self.base, 4)
        swarm.tick(self.run)
        with self.assertRaisesRegex(ValueError, "sent"):
            swarm.launched(self.run, "i0", 1)
        self.assertEqual(swarm.launch_sent(self.run, "i0", 1), "launch")
        self.assertIn("HALT", swarm.launch_sent(self.run, "i1", 1, halted=True))
        self.assertEqual(swarm.status(self.run)["reserved"], 1)
        self.assertEqual(swarm.load(self.run)["items"]["i0"]["status"], "sent")
        swarm.launched(self.run, "i0", 1)
        self.assertEqual(swarm.load(self.run)["items"]["i0"]["status"], "running")

    def test_v1_does_not_open_hard_caps_or_retest(self):
        self.plan([self.item("a", ["a.py"])], max_workers=4)
        brief = self.goal / "GOAL.md"
        brief.write_text("## Hard cap\n$40\n")
        with self.assertRaisesRegex(ValueError, "hard dollar cap"):
            swarm.init(self.run, self.goal, self.base, 4)
        self.assertFalse(self.run.exists())
        with self.assertRaises(SystemExit) as exc:
            swarm.main(["init", str(self.run), "--goal", str(self.goal), "--retest"])
        self.assertEqual(exc.exception.code, 2)

    def test_v1_width_30_holds_at_a_recorded_host_limit_of_20(self):
        """GO-024: an approved width of 30 never starts a 21st worker while 20 are active on a host that recorded 20."""
        self.plan([self.item(f"i{i}", [f"{i}.py"]) for i in range(30)], max_workers=30)
        record = swarm.host_file(self.run)
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({"limit": 20}))
        swarm.init(self.run, self.goal, self.base, 30)
        claims = swarm.tick(self.run)["dispatch"]
        self.assertEqual(len(claims), 20)
        for c in claims:
            self.assertEqual(swarm.launch_sent(self.run, c["id"], c["attempt"]), "launch")
            swarm.launched(self.run, c["id"], c["attempt"])
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])
        states = [v["status"] for v in swarm.load(self.run)["items"].values()]
        self.assertEqual((states.count("running"), states.count("pending")), (20, 10))
        self.assertEqual(swarm.host_limit(record), 20)

    def test_v1_four_results_still_need_review_and_ordered_integration(self):
        self.plan([self.item(f"i{i}", [f"{i}.py"], integ=["i0"] if i == 1 else [])
                   for i in range(4)], max_workers=4)
        swarm.init(self.run, self.goal, self.base, 4)
        claims = swarm.tick(self.run)["dispatch"]
        self.assertEqual(len(claims), 4)
        for c in claims:
            self.assertEqual(swarm.launch_sent(self.run, c["id"], c["attempt"]), "launch")
        for i, c in enumerate(claims):
            head, result = self.finish(c, [f"{i}.py"])
            self.assertTrue(result["accepted"])
            self.assertNotEqual(swarm.merge_gate(self.run, c["id"], self.repo, "main"), [])
            swarm.review(self.run, c["id"], head, "clean")
        self.assertIn("integration waits for i0", swarm.merge_gate(self.run, "i1", self.repo, "main"))
        self.assertEqual(swarm.merge_gate(self.run, "i0", self.repo, "main"), [])
        self.assertEqual(swarm.status(self.run)["spent"], 4)
        self.assertEqual(swarm.status(self.run)["reserved"], 0)

    # 1
    def test_two_independent_items_are_dispatched_together_and_really_overlap(self):
        self.plan([self.item("a", ["a/**"]), self.item("b", ["b/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        t = swarm.tick(self.run)
        self.assertEqual([c["id"] for c in t["dispatch"]], ["a", "b"])
        spans = {}
        def worker(c):
            swarm.launched(self.run, c["id"], c["attempt"])
            start = time.monotonic(); head = self.work(c, [f"{c['id']}/x.txt"], sleep=0.6); spans[c["id"]] = (start, time.monotonic())
            return swarm.result(self.run, c["id"], c["attempt"], head, self.repo, "passed")
        with ThreadPoolExecutor(3) as ex:
            out = list(ex.map(worker, t["dispatch"]))
        self.assertTrue(all(r["accepted"] for r in out))
        (a0, a1), (b0, b1) = spans["a"], spans["b"]
        self.assertLess(max(a0, b0), min(a1, b1), "the two workers' spans must overlap")

    # 2
    def test_a_start_dependency_blocks_dispatch_and_an_integration_dependency_blocks_only_the_merge(self):
        self.plan([self.item("api", ["api/**"]), self.item("page", ["page/**"], integ=["api"]), self.item("wire", ["wire/**"], start=["api"])])
        swarm.init(self.run, self.goal, self.base, 10)
        t = swarm.tick(self.run)
        self.assertEqual([c["id"] for c in t["dispatch"]], ["api", "page"])
        self.assertIn({"id": "wire", "status": "pending", "why": "start waits for api"}, t["waiting"])
        claims = {c["id"]: c for c in t["dispatch"]}
        self.finish(claims["page"], ["page/p.html"])
        h = swarm.load(self.run)["items"]["page"]["evidence"]["head"]
        swarm.review(self.run, "page", h, "clean")
        self.assertIn("integration waits for api", swarm.merge_gate(self.run, "page", self.repo, "main"))
        self.finish(claims["api"], ["api/a.py"])
        swarm.review(self.run, "api", swarm.load(self.run)["items"]["api"]["evidence"]["head"], "clean")
        self.assertEqual(swarm.merge_gate(self.run, "api", self.repo, "main"), [])
        sha = self.merge("api")
        t2 = swarm.tick(self.run)
        self.assertEqual([(c["id"], c["base"]) for c in t2["dispatch"]], [("wire", sha)])   # starts from the integrated head
        # page was built on the old base: stale against the moved target until it is refreshed
        self.assertTrue(any("isn't built on the target" in r for r in swarm.merge_gate(self.run, "page", self.repo, "main")))

    # 3
    def test_a_blocked_item_stops_its_dependents_and_not_unrelated_work(self):
        self.plan([self.item("x", ["x/**"]), self.item("y", ["y/**"], start=["x"]), self.item("z", ["z/**"])], max_workers=3)
        swarm.init(self.run, self.goal, self.base, 10)
        t = swarm.tick(self.run)
        swarm.blocked(self.run, "x", "#575 is stopped")
        claims = {c["id"]: c for c in t["dispatch"]}
        _, r = self.finish(claims["z"], ["z/z.txt"])
        self.assertTrue(r["accepted"])
        t2 = swarm.tick(self.run)
        st = swarm.status(self.run)["items"]
        self.assertEqual((st["x"]["status"], st["y"]["status"], st["z"]["status"]), ("blocked", "blocked", "drafted"))
        self.assertEqual(st["y"]["why"], "a prerequisite is blocked (x)")

    # 4
    def test_overlapping_writes_without_an_order_are_refused_and_a_diff_outside_the_claim_is_rejected(self):
        self.plan([self.item("a", ["src/**"]), self.item("b", ["src/b.py"])])
        with self.assertRaisesRegex(ValueError, "overlapping paths with no order"):
            swarm.load_plan(self.goal)
        self.plan([self.item("a", ["src/**"]), self.item("b", ["src/b.py"])], order=[["a", "b"]])
        swarm.load_plan(self.goal)                                       # an explicit order makes it legal
        for bad, msg in (([self.item("a", ["a/**"], start=["b"]), self.item("b", ["b/**"], start=["a"])], "cycle"),
                         ([self.item("a", ["a/**"], start=["ghost"])], "missing prerequisite")):
            self.plan(bad)
            with self.assertRaisesRegex(ValueError, msg):
                swarm.load_plan(self.goal)
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        head = self.work(c, ["a/ok.txt", "elsewhere.txt"])
        r = swarm.result(self.run, "a", 1, head, self.repo, "passed")
        self.assertFalse(r["accepted"]); self.assertIn("elsewhere.txt", r["why"])
        self.assertEqual(swarm.status(self.run)["items"]["a"]["status"], "blocked")

    # 5
    def test_a_restarted_coordinator_dispatches_nothing_twice_and_charges_once(self):
        self.plan([self.item("a", ["a/**"], est=2), self.item("b", ["b/**"], est=2)])
        swarm.init(self.run, self.goal, self.base, 10)
        first = swarm.tick(self.run)
        again = swarm.tick(self.run)                                     # a crash and a resume, same state on disk
        self.assertEqual(len(first["dispatch"]), 2); self.assertEqual(again["dispatch"], [])
        self.assertEqual(sorted(r["id"] for r in again["running"]), ["a", "b"])
        self.assertEqual(swarm.status(self.run)["reserved"], 4.0)
        _, r = self.finish(first["dispatch"][0], ["a/x"], cost=1.5)
        s = swarm.status(self.run)
        self.assertEqual((s["spent"], s["reserved"]), (2.0, 2.0))   # an unverified $1.50 releases nothing of its $2
        with self.assertRaises(ValueError):                              # the same result can't be charged twice
            swarm.result(self.run, "a", 1, "HEAD", self.repo, "passed", 1.5)

    # 6
    def test_halt_and_the_shared_budget_hold_with_jobs_in_flight(self):
        self.plan([self.item("a", ["a/**"], est=4), self.item("b", ["b/**"], est=4), self.item("c", ["c/**"], est=4)])
        swarm.init(self.run, self.goal, self.base, 9)
        t = swarm.tick(self.run)
        self.assertEqual([c["id"] for c in t["dispatch"]], ["a", "b"])
        self.assertTrue(any(w["id"] == "c" and w["why"].startswith("budget") for w in t["waiting"]))
        h = swarm.tick(self.run, halted=True)
        self.assertEqual((h["stopped"], h["dispatch"], len(h["running"])), ("HALT", [], 2))
        claims = {c["id"]: c for c in t["dispatch"]}
        self.finish(claims["a"], ["a/x"], cost=1)                        # in-flight work still reports under HALT
        swarm.review(self.run, "a", swarm.load(self.run)["items"]["a"]["evidence"]["head"], "clean")
        self.assertIn("HALT", swarm.merge_gate(self.run, "a", self.repo, "main", halted=True))
        self.assertEqual(swarm.tick(self.run, spend_stop=True)["dispatch"], [])
        t = swarm.tick(self.run)                                         # a reported $1, but its $4 stays charged
        self.assertEqual(t["dispatch"], [])
        self.assertTrue(any(w["id"] == "c" and w["why"].startswith("budget") for w in t["waiting"]))

    # 7
    def test_stale_evidence_cannot_authorize_a_merge(self):
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        head, _ = self.finish(c, ["a/x"])
        with self.assertRaises(ValueError):
            swarm.review(self.run, "a", "0" * 40, "clean")               # a review of another head
        swarm.review(self.run, "a", head, "clean")
        (self.repo / "other.txt").write_text("moved\n"); git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "main moved")
        reasons = swarm.merge_gate(self.run, "a", self.repo, "main")
        self.assertTrue(any("target moved" in r for r in reasons) and any("isn't built on the target" in r for r in reasons), reasons)

    # 8
    def test_a_launch_failure_is_visible_and_never_reported_running(self):
        self.plan([self.item("a", ["a/**"], est=3)])
        swarm.init(self.run, self.goal, self.base, 10)
        swarm.tick(self.run)
        swarm.launch_failed(self.run, "a", 1, "hook changed this tool call's input")
        s = swarm.status(self.run)
        self.assertEqual((s["items"]["a"]["status"], s["reserved"], s["spent"]), ("pending", 0, 0))
        self.assertIn("launch failed: hook changed", s["items"]["a"]["why"])
        c = swarm.tick(self.run)["dispatch"][0]
        self.assertEqual(c["attempt"], 2)
        swarm.launch_failed(self.run, "a", 2, "again")
        self.assertEqual(swarm.status(self.run)["items"]["a"]["status"], "blocked")
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])
        events = [json.loads(l)["event"] for l in (self.run / "swarm-events.jsonl").read_text().splitlines()]
        self.assertEqual(events.count("launch_failed"), 2); self.assertNotIn("launched", events)

    # 9
    def test_an_existing_plan_without_deps_stays_serial(self):
        self.plan(None, n=3)
        plan = swarm.load_plan(self.goal)
        self.assertTrue(plan["serial"]); self.assertEqual(plan["max_workers"], 1)
        swarm.init(self.run, self.goal, self.base, 10)
        t = swarm.tick(self.run)
        self.assertEqual([c["id"] for c in t["dispatch"]], ["item-1"])
        self.assertIn({"id": "item-2", "status": "pending", "why": "start waits for item-1"}, t["waiting"])

    # 10
    def test_redispatching_a_worker_never_resets_the_review_cap(self):
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10, review_cap=2)
        c = swarm.tick(self.run)["dispatch"][0]
        head, _ = self.finish(c, ["a/x"])
        self.assertEqual(swarm.review(self.run, "a", head, "blocking"), "pending")
        c2 = swarm.tick(self.run)["dispatch"][0]
        self.assertEqual(c2["attempt"], 2)
        head2, _ = self.finish(c2, ["a/y"])
        self.assertEqual(swarm.review(self.run, "a", head2, "blocking"), "blocked")
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])
        self.assertEqual(swarm.status(self.run)["items"]["a"]["review_rounds"], 2)

    # 11
    def test_a_changed_pinned_contract_is_rejected(self):
        self.plan([dict(self.item("a", ["a/**", "contract.json"]), contracts=[{"path": "contract.json", "sha256": "0" * 64}])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        r = swarm.result(self.run, "a", 1, self.work(c, ["a/x", "contract.json"]), self.repo, "passed")
        self.assertFalse(r["accepted"]); self.assertIn("pinned contract", r["why"])

    # 12
    def test_an_item_left_behind_by_a_merge_is_refreshed_on_the_target_and_reviewed_again(self):
        self.plan([self.item("a", ["a/**"]), self.item("b", ["b/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        ca, cb = swarm.tick(self.run)["dispatch"]
        ha, _ = self.finish(ca, ["a/x"]); hb, _ = self.finish(cb, ["b/x"])
        swarm.review(self.run, "a", ha, "clean"); swarm.review(self.run, "b", hb, "clean")
        self.merge("a")
        self.assertTrue(swarm.merge_gate(self.run, "b", self.repo, "main"))         # stale: b isn't on the new target
        wt = self.tmp / "wt-b-1"
        git(wt, "rebase", "-q", "main"); nb = git(wt, "rev-parse", "HEAD")
        self.assertEqual(swarm.refresh(self.run, "b", nb, self.repo, "main", "passed")["accepted"], True)
        self.assertIn("status is drafted, not reviewed", swarm.merge_gate(self.run, "b", self.repo, "main"))
        self.assertEqual(swarm.status(self.run)["items"]["b"]["review_rounds"], 1)  # the earlier round still counts
        swarm.review(self.run, "b", nb, "clean")
        self.assertEqual(swarm.merge_gate(self.run, "b", self.repo, "main"), [])
        with self.assertRaisesRegex(ValueError, "isn't built on"):
            swarm.refresh(self.run, "b", hb, self.repo, "main", "passed")

    # review 20261119-153637 round 1
    def test_r1_f1_character_class_globs_overlap(self):
        self.assertTrue(swarm._glob_overlap("src/[ab].py", "src/[bc].py"))
        self.assertTrue(swarm._glob_overlap("src/[ab].py", "src/b.py"))
        self.assertFalse(swarm._glob_overlap("src/[ab].py", "src/c.py"))
        self.assertFalse(swarm._glob_overlap("a/x.py", "a/y.py"))
        self.plan([self.item("a", ["src/[ab].py"]), self.item("b", ["src/[bc].py"])])
        with self.assertRaisesRegex(ValueError, "overlapping paths with no order"):
            swarm.load_plan(self.goal)

    def test_r2_f2_a_returned_patch_is_committed_at_the_pinned_base_and_checked_like_a_head(self):
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        self.assertIn("or a patch against the pinned base", c["return"][0])
        swarm.launched(self.run, "a", 1)
        scratch = self.tmp / "scratch"; git(self.repo, "worktree", "add", "-q", "--detach", str(scratch), c["base"])
        (scratch / "a").mkdir(); (scratch / "a" / "p.txt").write_text("from a patch\n"); git(scratch, "add", "-A")
        patch = self.tmp / "w.patch"; patch.write_text(git(scratch, "diff", "--cached") + "\n")
        head = swarm.apply_patch(self.run, "a", 1, self.repo, patch)
        self.assertEqual(git(self.repo, "rev-parse", f"{head}~1"), c["base"])
        self.assertEqual(git(self.repo, "rev-parse", c["branch"]), head)
        self.assertEqual(swarm.result(self.run, "a", 1, head, self.repo, "passed"), {"accepted": True, "files": ["a/p.txt"]})

    def test_r2_f1_every_refusal_load_plan_makes(self):
        cases = [
            ({"1": {"id": "a", "writes": ["a/x"]}, "2": {"id": "b", "writes": ["b/x"]}}, 3, None, 1, "don't match PLAN.md"),
            ({"1": {"id": "a", "writes": ["a/x"]}, "2": {"id": "a", "writes": ["b/x"]}}, 3, None, 2, "unique, lowercase"),
            ({"1": {"id": "Bad_ID", "writes": ["a/x"]}}, 3, None, 1, "unique, lowercase"),
            ({"1": {"id": "a", "writes": ["a/x"], "start_after": ["a"]}}, 3, None, 1, "depends on itself"),
            ({"1": {"id": "a", "writes": ["a/x"], "contracts": [{"path": "c.json"}]}}, 3, None, 1, "pinned as"),
            ({"1": {"id": "a", "writes": ["a/x"]}}, True, None, 1, "max_workers"),
            ({"1": {"id": "a", "writes": ["a/x"]}}, 0, None, 1, "max_workers"),
            ({"1": {"id": "a", "writes": ["a/x"], "start_after": ["c"]}, "2": {"id": "b", "writes": ["b/x"], "integrate_after": ["a"]},
              "3": {"id": "c", "writes": ["c/x"]}}, 3, [["b", "c"]], 3, "cycle"),   # start, integration and order edges together
            ({"1": {"id": "a", "writes": ["/etc/x"]}}, 3, None, 1, "repository-relative"),
        ]
        for items, mw, order, n, msg in cases:
            (self.goal / "PLAN.md").write_text("".join(f"{k}. item {k}\n   - works\n" for k in range(1, n + 1)))
            (self.goal / "DEPS.json").write_text(json.dumps({"version": 1, "max_workers": mw, "order": order or [], "items": items}))
            with self.assertRaisesRegex(ValueError, msg, msg=msg):
                swarm.load_plan(self.goal)

    def test_r2_f7_a_moved_target_is_reported_for_an_item_with_no_evidence(self):
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        (self.repo / "o.txt").write_text("m\n"); git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "moved")
        self.assertTrue(any("target moved" in r for r in swarm.merge_gate(self.run, "a", self.repo, "main")))   # pending
        swarm.tick(self.run)
        self.assertTrue(any("target moved" in r for r in swarm.merge_gate(self.run, "a", self.repo, "main")))   # dispatched

    def test_r2_f9_a_worker_blocked_while_running_keeps_its_slot(self):
        self.plan([self.item("a", ["a/**"]), self.item("b", ["b/**"])], max_workers=1)
        swarm.init(self.run, self.goal, self.base, 10)
        ca = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        swarm.blocked(self.run, "a", "stop")
        t = swarm.tick(self.run)
        self.assertEqual(t["dispatch"], [])
        self.assertIn({"id": "b", "status": "pending", "why": "all workers busy"}, t["waiting"])
        swarm.result(self.run, "a", 1, self.work(ca, ["a/x"]), self.repo, "passed", cost=1)   # it reports: the slot frees
        self.assertEqual([c["id"] for c in swarm.tick(self.run)["dispatch"]], ["b"])

    def test_r1_f3_only_failed_launches_count_toward_the_launch_limit(self):
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        head, _ = self.finish(c, ["a/x"])
        swarm.review(self.run, "a", head, "blocking")
        c2 = swarm.tick(self.run)["dispatch"][0]
        swarm.launch_failed(self.run, "a", c2["attempt"], "once")
        st = swarm.status(self.run)["items"]["a"]
        self.assertEqual((st["status"], st["attempts"]), ("pending", 2))
        self.assertEqual(swarm.tick(self.run)["dispatch"][0]["attempt"], 3)

    def test_r1_f4_f5_a_block_reaches_in_flight_dependents_and_frees_unlaunched_reservations(self):
        self.plan([self.item("x", ["x/**"]), self.item("y", ["y/**"], integ=["x"]), self.item("z", ["z/**"])], max_workers=2)
        swarm.init(self.run, self.goal, self.base, 2)
        t = swarm.tick(self.run)
        self.assertEqual([c["id"] for c in t["dispatch"]], ["x", "y"])
        cy = t["dispatch"][1]
        swarm.launched(self.run, "y", 1)
        swarm.blocked(self.run, "x", "stopped")                      # x never launched: its $1 comes back
        st = swarm.status(self.run)
        self.assertEqual((st["items"]["x"]["status"], st["items"]["y"]["status"], st["reserved"]), ("blocked", "blocked", 1.0))
        self.assertEqual([c["id"] for c in swarm.tick(self.run)["dispatch"]], ["z"])   # an unrelated item gets the freed money
        r = swarm.result(self.run, "y", 1, self.work(cy, ["y/a"]), self.repo, "passed", cost=0.5)
        self.assertFalse(r["accepted"])                              # y's worker reports, its spend settles, it stays blocked
        st = swarm.status(self.run)
        self.assertEqual((st["items"]["y"]["status"], st["spent"]), ("blocked", 1.0))   # its full reservation
        with self.assertRaises(ValueError):
            swarm.launched(self.run, "x", 1)

    def test_r1_f6_a_pinned_contract_renamed_away_is_a_change_to_it(self):
        self.plan([dict(self.item("a", ["a/**"]), contracts=[{"path": "contract.json", "sha256": "0" * 64}])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        wt = self.tmp / "wt-a-1"
        git(self.repo, "worktree", "add", "-q", "-b", c["branch"], str(wt), c["base"])
        (wt / "a").mkdir(); git(wt, "mv", "contract.json", "a/contract.json"); git(wt, "commit", "-qm", "move")
        r = swarm.result(self.run, "a", 1, git(wt, "rev-parse", "HEAD"), self.repo, "passed")
        self.assertFalse(r["accepted"]); self.assertIn("contract.json", r["why"])

    def test_r1_f7_a_drafted_item_reports_a_stale_target_too(self):
        self.plan([self.item("a", ["a/**"])])
        swarm.init(self.run, self.goal, self.base, 10)
        self.finish(swarm.tick(self.run)["dispatch"][0], ["a/x"])
        (self.repo / "o.txt").write_text("m\n"); git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "moved")
        reasons = swarm.merge_gate(self.run, "a", self.repo, "main")
        self.assertTrue(any("target moved" in r for r in reasons) and any("isn't built on the target" in r for r in reasons), reasons)

    def test_r1_f8_the_review_cap_is_the_briefs(self):
        self.plan([self.item("a", ["a/**"])])
        (self.goal / "GOAL.md").write_text("# g\n\n## Max review rounds per item\n1\n")
        with self.assertRaisesRegex(ValueError, "differs from the brief"):
            swarm.init(self.run, self.goal, self.base, 10, review_cap=3)
        swarm.init(self.run, self.goal, self.base, 10)
        self.assertEqual(swarm.load(self.run)["review_cap"], 1)

    # Dorian 2026-11-19: the dollar cap and HALT with workers already running
    def test_the_dispatch_budget_holds_while_workers_run_and_records_an_overrun(self):
        self.plan([self.item("a", ["a/**"], est=2), self.item("b", ["b/**"], est=2), self.item("c", ["c/**"], est=2)])
        swarm.init(self.run, self.goal, self.base, 5)
        t = swarm.tick(self.run)
        self.assertEqual([c["id"] for c in t["dispatch"]], ["a", "b"])      # $4 reserved of $5: c can't fit
        ca, cb = t["dispatch"]
        swarm.launched(self.run, "a", 1); swarm.launched(self.run, "b", 1)
        self.assertTrue(any(w["id"] == "c" and w["why"].startswith("budget") for w in swarm.tick(self.run)["waiting"]))
        swarm.result(self.run, "a", 1, self.work(ca, ["a/x"]), self.repo, "passed", cost=4)   # a overran its $2
        st = swarm.status(self.run)
        self.assertEqual((st["spent"], st["reserved"], st["over_budget"]), (4.0, 2.0, False))
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])               # spent + in flight past the cap: nothing new
        swarm.result(self.run, "b", 1, self.work(cb, ["b/x"]), self.repo, "passed")          # no dollar figure reported
        st = swarm.status(self.run)
        self.assertEqual((st["spent"], st["reserved"], st["estimated_settlements"], st["over_budget"]), (6.0, 0, 2, True))   # charged at its estimate
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])
        ev = [json.loads(l) for l in (self.run / "swarm-events.jsonl").read_text().splitlines()]
        self.assertEqual([(e["id"], e["charged"]) for e in ev if e["event"] == "overrun"], [("a", 4.0)])
        self.assertTrue(any(e["event"] == "over_budget" for e in ev))
        self.assertEqual([(e["reported"], e["charged"], e["verified"]) for e in ev if e["event"] == "settled"], [(4.0, 4.0, False), (None, 2.0, False)])

    def test_halt_raised_after_launch_stops_dispatch_and_integration_through_the_cli(self):
        self.plan([self.item("a", ["a/**"]), self.item("b", ["b/**"], start=["a"])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        halt = self.tmp / "HALT"; halt.write_text("stop\n")                 # raised while a runs
        cli = lambda *a: subprocess.run([sys.executable, str(HERE / "swarm.py"), *a], capture_output=True, text=True)
        r = cli("tick", str(self.run), "--halt", str(halt))
        self.assertEqual((json.loads(r.stdout)["stopped"], json.loads(r.stdout)["dispatch"]), ("HALT", []))
        head = self.work(c, ["a/x"])
        self.assertEqual(cli("result", str(self.run), "a", "--attempt", "1", "--head", head, "--repo", str(self.repo), "--tests", "passed").returncode, 0)
        swarm.review(self.run, "a", head, "clean")
        r = cli("merge-gate", str(self.run), "a", "--repo", str(self.repo), "--target", "main", "--halt", str(halt))
        self.assertEqual(r.returncode, 1); self.assertIn("HALT", json.loads(r.stdout))
        halt.unlink()
        self.assertEqual(cli("merge-gate", str(self.run), "a", "--repo", str(self.repo), "--target", "main", "--halt", str(halt)).returncode, 0)

    # review 20261119-203612 F11 and Dorian 2026-11-19: dispatch budget, not a spend cap
    def test_f11_money_values_must_be_finite_and_not_negative(self):
        for est in (-2, 0, "nan", "inf", True, "two"):
            self.plan([self.item("a", ["a/**"], est=est)])
            with self.assertRaises(ValueError, msg=est):
                swarm.load_plan(self.goal)
        self.plan([self.item("a", ["a/**"], est=1), self.item("b", ["b/**"], est=1)], max_workers=3)
        for budget in (0, -5, float("nan"), float("inf")):
            with self.assertRaises(ValueError, msg=budget):
                swarm.init(self.tmp / f"run-{budget}", self.goal, self.base, budget)
        swarm.init(self.run, self.goal, self.base, 2)
        ca, cb = swarm.tick(self.run)["dispatch"]
        swarm.launched(self.run, "a", 1); swarm.launched(self.run, "b", 1)
        for bad in ("nan", "-1", "inf"):
            with self.assertRaises(ValueError, msg=bad):
                swarm.result(self.run, "a", 1, self.work(ca, [f"a/{bad}"]) if bad == "nan" else "HEAD", self.repo, "passed", cost=bad)
        st = swarm.status(self.run)
        self.assertEqual((st["spent"], st["reserved"]), (0.0, 2.0))     # a refused result settles nothing

    def test_two_workers_in_flight_keep_their_full_reservations_whatever_they_report(self):
        self.plan([self.item("a", ["a/**"], est=3), self.item("b", ["b/**"], est=3), self.item("c", ["c/**"], est=3)])
        swarm.init(self.run, self.goal, self.base, 7)
        ca, cb = swarm.tick(self.run)["dispatch"]
        swarm.launched(self.run, "a", 1); swarm.launched(self.run, "b", 1)
        swarm.result(self.run, "a", 1, self.work(ca, ["a/x"]), self.repo, "passed", cost=0.10)
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])          # $3 + $3 of $7 still held: c can't fit
        swarm.result(self.run, "b", 1, self.work(cb, ["b/x"]), self.repo, "passed")
        st = swarm.status(self.run)
        self.assertEqual((st["spent"], st["reserved"], st["over_budget"]), (6.0, 0, False))
        self.assertEqual(swarm.tick(self.run)["dispatch"], [])

    def test_a_goal_that_needs_a_hard_dollar_cap_is_refused(self):
        self.plan([self.item("a", ["a/**"])])
        d = json.loads((self.goal / "DEPS.json").read_text()); d["hard_dollar_cap"] = True
        (self.goal / "DEPS.json").write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, "hard dollar cap"):
            swarm.load_plan(self.goal)
        d.pop("hard_dollar_cap"); d["spend_cap_usd"] = 5
        (self.goal / "DEPS.json").write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, "keys the coordinator doesn't read"):
            swarm.load_plan(self.goal)
        d.pop("spend_cap_usd"); (self.goal / "DEPS.json").write_text(json.dumps(d))
        (self.goal / "GOAL.md").write_text("# g\n\n## Spend cap\n$40, a hard cap\n\n## Max review rounds per item\n2\n")
        with self.assertRaisesRegex(ValueError, "asks for a hard cap"):
            swarm.load_plan(self.goal)
        (self.goal / "GOAL.md").write_text("# g\n\n## Spend cap\n$40\n\n## Max review rounds per item\n2\n")
        swarm.load_plan(self.goal)

    def test_an_item_that_can_never_fit_is_blocked_once_nothing_is_in_flight(self):   # spec review GO-017 C1
        self.plan([self.item("a", ["a/**"], est=3), self.item("b", ["b/**"], est=3), self.item("c", ["c/**"], est=1, start=["b"])],
                  max_workers=1)
        swarm.init(self.run, self.goal, self.base, 5)
        ca = swarm.tick(self.run)["dispatch"][0]
        t = swarm.tick(self.run)
        self.assertEqual(swarm.status(self.run)["items"]["b"]["status"], "pending")   # a is in flight: b waits
        swarm.launched(self.run, "a", 1)
        swarm.result(self.run, "a", 1, self.work(ca, ["a/x"]), self.repo, "passed")
        t = swarm.tick(self.run)                                          # $2 left, b needs $3, nothing in flight
        st = swarm.status(self.run)["items"]
        self.assertEqual((st["b"]["status"], st["c"]["status"]), ("blocked", "blocked"))
        self.assertIn("dispatch budget exhausted", st["b"]["why"])
        self.assertEqual(t["dispatch"], [])

    # review 20261119-212242 F1: literal Unicode names for both checks
    def test_f1_a_change_to_a_pinned_unicode_filename_is_refused(self):
        (self.repo / "caf\u00e9.json").write_text('{"v": 1}\n'); git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "contract")
        base = git(self.repo, "rev-parse", "HEAD")
        self.plan([dict(self.item("a", ["**"]), contracts=[{"path": "caf\u00e9.json", "sha256": "0" * 64}])])
        swarm.init(self.run, self.goal, base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        r = swarm.result(self.run, "a", 1, self.work(c, ["caf\u00e9.json"]), self.repo, "passed")
        self.assertFalse(r["accepted"]); self.assertIn("changed a pinned contract: caf\u00e9.json", r["why"])

    def test_f1_a_change_to_an_allowed_unicode_filename_is_accepted(self):
        self.plan([self.item("a", ["docs/r\u00e9sum\u00e9-*.md"])])
        swarm.init(self.run, self.goal, self.base, 10)
        c = swarm.tick(self.run)["dispatch"][0]
        swarm.launched(self.run, "a", 1)
        r = swarm.result(self.run, "a", 1, self.work(c, ["docs/r\u00e9sum\u00e9-1.md"]), self.repo, "passed")
        self.assertEqual(r, {"accepted": True, "files": ["docs/r\u00e9sum\u00e9-1.md"]})


class Viewer(unittest.TestCase):
    """swarm-agent-view: a record that cannot be written must not leak a detached viewer."""
    def test_unwritable_pid_record_ends_the_viewer_and_reports_unavailable(self):
        import os, io, contextlib
        tmp = Path(tempfile.mkdtemp(prefix="viewer-"))
        (tmp / "viewer.pid").mkdir()   # write_text on a directory raises OSError
        fake = tmp / "bin"; fake.mkdir()
        (fake / "npx").write_text("#!/bin/sh\nexec /bin/sleep 30\n"); (fake / "npx").chmod(0o755)
        env = {"PATH": str(fake), "SWARM_VIEWER_PLATFORM": "Darwin"}
        old = dict(os.environ); os.environ.clear(); os.environ.update(env)
        err = io.StringIO()
        started, real_popen = [], swarm.subprocess.Popen
        def spy(*a, **k):
            started.append(real_popen(*a, **k)); return started[-1]
        swarm.subprocess.Popen = spy
        try:
            with contextlib.redirect_stderr(err):
                rc = swarm.viewer_start(str(tmp))
        finally:
            swarm.subprocess.Popen = real_popen
            os.environ.clear(); os.environ.update(old)
        self.assertEqual(rc, 0)
        self.assertIn("viewer: unavailable", err.getvalue())
        self.assertIn("swarm is unaffected", err.getvalue())
        import time
        pid = started[0].pid   # the fake viewer did start; it must now be gone
        for _ in range(50):
            if not swarm._viewer_stamp(pid):
                break
            time.sleep(0.1)
        self.assertEqual(swarm._viewer_stamp(pid), "")

    def test_unavailable_host_returns_before_any_running_viewer_check(self):
        import os, io, contextlib
        tmp = Path(tempfile.mkdtemp(prefix="viewer-"))
        old_env, old_rec = dict(os.environ), swarm._viewer_record
        os.environ["SWARM_VIEWER_PLATFORM"] = "Linux"
        def boom(run): raise AssertionError("running-viewer check ran on an unavailable host")
        swarm._viewer_record = boom
        err, out = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = swarm.viewer_start(str(tmp))
        finally:
            swarm._viewer_record = old_rec; os.environ.clear(); os.environ.update(old_env)
        self.assertEqual((rc, out.getvalue()), (0, ""))
        self.assertTrue(err.getvalue().startswith("viewer: unavailable"))

    def test_viewer_names_as_ordinary_arguments_reach_their_own_commands(self):
        import io, contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                swarm.main(["check", "viewer-start"])
            except BaseException:
                pass
        self.assertNotIn("usage: swarm.py viewer-start", err.getvalue())


    def test_viewer_command_rejects_options_in_any_position(self):
        import io, contextlib
        for argv in (["--halt", "x", "viewer-start", "r"], ["viewer-stop", "r", "--halt", "x"],
                     ["--spend-stop", "viewer-start", "r"], ["viewer-start"], ["viewer-stop", "a", "b"],
                     ["--help", "viewer-start", "r"], ["--spend-st", "viewer-stop", "r"], ["viewer-start", "r", "--he"]):
            err, out = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = swarm.main(argv)
            self.assertEqual((rc, out.getvalue()), (2, ""), argv)
            self.assertIn("usage: swarm.py viewer-start|viewer-stop", err.getvalue())

    def test_other_commands_with_options_before_a_viewer_named_item_still_dispatch(self):
        import io, contextlib
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                swarm.main(["--reason", "failure", "blocked", "run", "viewer-start"])
            except BaseException:
                pass
        self.assertNotIn("usage: swarm.py viewer-start", err.getvalue())


    def test_help_on_a_complete_mutating_command_changes_no_state(self):
        import io, contextlib
        tmp = Path(tempfile.mkdtemp(prefix="help-"))
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc = swarm.main(["blocked", str(tmp), "x", "--reason", "r", "--help"])
        self.assertEqual((rc, list(tmp.iterdir())), (0, []))


if __name__ == "__main__":
    unittest.main()
