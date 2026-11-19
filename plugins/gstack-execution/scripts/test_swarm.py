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
        self.assertEqual(st["y"]["why"], "a prerequisite is blocked")

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
        self.assertEqual((s["spent"], s["reserved"]), (1.5, 2.0))
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
        self.assertEqual([c["id"] for c in swarm.tick(self.run)["dispatch"]], ["c"])   # a's unspent reservation freed

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


if __name__ == "__main__":
    unittest.main()
