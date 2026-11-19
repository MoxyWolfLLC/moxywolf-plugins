#!/usr/bin/env python3
"""GO-017: build and test independent work in parallel; integrate in dependency order through one coordinator.

A goal's PLAN.md stays as goal_brief.py checks it. A parallel plan adds goals/<id>/DEPS.json beside it, approved
and frozen with the goal; without one the plan is serial (each item starts after the one before), exactly the
one-item loop goal_run.py has always run.

DEPS.json: {"version": 1, "max_workers": 1-3,
            "items": {"<plan item n>": {"id": "page", "writes": ["assets/x.html", "tests/test_x.py"],
                                        "start_after": [], "integrate_after": ["cli"],
                                        "contracts": [{"path": "assets/gate.js", "sha256": "..."}],
                                        "estimate_usd": 2.0}},
            "order": [["cli", "page"]]}
A start dependency blocks dispatch until the dependency has merged. An integration dependency blocks only the
merge: the item is drafted and tested against its pinned contracts meanwhile. Two items that write the same
path need an order between them (integrate_after, directly or through others, or an "order" pair).

The coordinator is the only writer of <run>/swarm.json. Workers get a claim (item, attempt, pinned base, branch,
writable paths, contracts, what to return) and return a patch or head SHA, test results and unresolved issues.
They don't dispatch workers, write run state, merge, deploy or see the holdout.

  swarm.py check <goal dir>                                   validate DEPS.json against PLAN.md
  swarm.py init <run> --goal <goal dir> --base <sha> --budget <usd> [--review-cap N]
  swarm.py tick <run> [--halt <path>] [--spend-stop]          claims every eligible item up to max_workers
  swarm.py launched <run> <id> --attempt N                    the Agent call started
  swarm.py launch-failed <run> <id> --attempt N --reason R    it didn't; visible, retried by a later tick
  swarm.py result <run> <id> --attempt N --head SHA --repo R --tests passed|failed [--cost USD] [--unresolved T]
  swarm.py review <run> <id> --head SHA --outcome clean|blocking [--review-id ID]
  swarm.py refresh <run> <id> --head SHA --repo R --target <ref> --tests passed|failed
                                                              rebuilt on a moved target; its review must run again
  swarm.py blocked <run> <id> --reason R                      stops the item and its dependents only
  swarm.py merge-gate <run> <id> --repo R --target <ref>      exit 0 only when this item may merge now
  swarm.py merged <run> <id> --sha SHA
  swarm.py status <run>
"""
import argparse
import fcntl
import fnmatch
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from task_graph import write   # the graph's atomic write, reused

MAX_WORKERS = 3
MAX_LAUNCHES = 2           # a launch that failed twice is blocked, not retried forever
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
RUNNING = ("dispatched", "running")
DEFAULT_ESTIMATE = 1.0


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan_numbers(plan_text):
    return [int(m.group(1)) for m in re.finditer(r"^(\d+)\.\s+\S", plan_text, re.M)]


def _glob_overlap(a, b):
    # ponytail: literal-prefix test, so "src/**" and "src/x.py" overlap; two globs that only meet in the middle
    # ("*.py" vs "a/*") read as overlapping too, which errs toward asking for an order, never toward a race
    if a == b or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
        return True
    pa, pb = re.split(r"[*?\[]", a)[0], re.split(r"[*?\[]", b)[0]
    return ("*" in a or "?" in a) and pb.startswith(pa) or ("*" in b or "?" in b) and pa.startswith(pb)


def load_plan(goal_dir):
    """The validated dependency plan; a serial chain when DEPS.json is absent (every existing goal)."""
    goal_dir = Path(goal_dir)
    numbers = plan_numbers((goal_dir / "PLAN.md").read_text())
    f = goal_dir / "DEPS.json"
    if not f.is_file():
        items = [{"n": n, "id": f"item-{n}", "writes": ["**"], "start_after": [f"item-{p}"] if p else [],
                  "integrate_after": [f"item-{p}"] if p else [], "contracts": [], "estimate_usd": DEFAULT_ESTIMATE}
                 for p, n in zip([None] + numbers, numbers)]
        return validate({"version": 1, "max_workers": 1, "serial": True, "items": items, "order": []})
    d = json.loads(f.read_text())
    if not isinstance(d, dict) or not isinstance(d.get("items"), dict):
        raise ValueError("DEPS.json needs an items object keyed by PLAN.md item number")
    if sorted(int(k) for k in d["items"]) != sorted(numbers):
        raise ValueError(f"DEPS.json items {sorted(d['items'])} don't match PLAN.md items {numbers}")
    items = []
    for k, v in sorted(d["items"].items(), key=lambda kv: int(kv[0])):
        items.append({"n": int(k), "id": v.get("id"), "writes": v.get("writes") or [], "start_after": v.get("start_after", []),
                      "integrate_after": v.get("integrate_after", []), "contracts": v.get("contracts", []),
                      "estimate_usd": float(v.get("estimate_usd", DEFAULT_ESTIMATE))})
    return validate({"version": d.get("version"), "max_workers": d.get("max_workers", MAX_WORKERS), "serial": False,
                     "items": items, "order": d.get("order", [])})


def validate(plan):
    items = plan["items"]
    ids = [i["id"] for i in items]
    if plan.get("version") != 1:
        raise ValueError("DEPS.json version must be 1")
    if not isinstance(plan["max_workers"], int) or not 1 <= plan["max_workers"] <= MAX_WORKERS:
        raise ValueError(f"max_workers must be 1 to {MAX_WORKERS}")
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and ID.match(i) for i in ids):
        raise ValueError(f"item ids must be unique, lowercase, hyphenated: {ids}")
    for i in items:
        if not i["writes"] or not all(isinstance(w, str) and w and not w.startswith("/") and ".." not in w for w in i["writes"]):
            raise ValueError(f"{i['id']}: writes must be repository-relative paths or globs")
        for dep in i["start_after"] + i["integrate_after"]:
            if dep not in ids:
                raise ValueError(f"{i['id']}: missing prerequisite {dep}")
            if dep == i["id"]:
                raise ValueError(f"{i['id']} depends on itself")
        for c in i["contracts"]:
            if not (isinstance(c, dict) and c.get("path") and re.fullmatch(r"[0-9a-f]{64}", str(c.get("sha256", "")))):
                raise ValueError(f"{i['id']}: a contract is pinned as {{path, sha256}}")
    for pair in plan["order"]:
        if not (isinstance(pair, list) and len(pair) == 2 and set(pair) <= set(ids)):
            raise ValueError(f"order entry {pair} must name two items")
    edges = {i["id"]: set(i["start_after"]) | set(i["integrate_after"]) for i in items}
    for a, b in plan["order"]:
        edges[b].add(a)
    done = set()
    while len(done) < len(ids):                       # the graph's own cycle test (task_graph.validate_graph)
        ready = {i for i in ids if edges[i] <= done} - done
        if not ready:
            raise ValueError(f"cycle among {sorted(set(ids) - done)}")
        done |= ready
    before = {i: _ancestors(edges, i) for i in ids}
    for x in items:
        for y in items:
            if x["id"] < y["id"] and any(_glob_overlap(a, b) for a in x["writes"] for b in y["writes"]):
                if x["id"] not in before[y["id"]] and y["id"] not in before[x["id"]]:
                    raise ValueError(f"{x['id']} and {y['id']} write overlapping paths with no order between them")
    return plan


def _ancestors(edges, i):
    out, todo = set(), list(edges[i])
    while todo:
        j = todo.pop()
        if j not in out:
            out.add(j); todo.extend(edges[j])
    return out


# ---- run state: one writer, under the graph's lock ----

def _paths(run):
    run = Path(run)
    return run / "swarm.json", run / "swarm-events.jsonl", run / "swarm.lock"


def load(run):
    return json.loads(_paths(run)[0].read_text())


def _event(run, kind, **f):
    with open(_paths(run)[1], "a") as fh:
        fh.write(json.dumps({"ts": now(), "event": kind, **f}) + "\n")


def mutate(run, fn):
    state_f, _, lock_f = _paths(run)
    # the graph's lock refuses a second executor; here results from parallel workers queue for the one writer
    with open(lock_f, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            s = json.loads(state_f.read_text())
            out = fn(s)
            write(state_f, s)
            return out
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def init(run, goal_dir, base, budget, review_cap=3):
    plan = load_plan(goal_dir)
    run = Path(run); run.mkdir(parents=True, exist_ok=True)
    if _paths(run)[0].exists():
        raise ValueError(f"{run} already has a swarm; resume it with tick")
    s = {"plan": plan, "base": base, "integration_head": base, "budget": float(budget), "spent": 0.0,
         "reserved": {}, "review_cap": review_cap,
         "items": {i["id"]: {"status": "pending", "attempts": 0, "review_rounds": 0, "evidence": None, "why": None}
                   for i in plan["items"]}}
    write(_paths(run)[0], s)
    _event(run, "init", base=base, budget=budget, serial=plan["serial"], items=[i["id"] for i in plan["items"]])
    return s


def _item(s, iid):
    if iid not in s["items"]:
        raise ValueError(f"no item {iid}")
    return next(i for i in s["plan"]["items"] if i["id"] == iid), s["items"][iid]


def _remaining(s):
    return s["budget"] - s["spent"] - sum(s["reserved"].values())


def tick(run, halted=False, spend_stop=False):
    """Claim every eligible item up to max_workers. Never claims an item that is already claimed, so a restarted
    coordinator that ticks again dispatches nothing twice. Returns what to launch, what's running, and why the
    rest waits."""
    def go(s):
        out = {"dispatch": [], "running": [], "waiting": [], "stopped": None}
        if halted or spend_stop:
            out["stopped"] = "HALT" if halted else "spend stop"
        running = [k for k, v in s["items"].items() if v["status"] in RUNNING]
        for i in s["plan"]["items"]:
            st = s["items"][i["id"]]
            if st["status"] in RUNNING:
                out["running"].append({"id": i["id"], "status": st["status"], "attempt": st["attempts"]})
                continue
            if st["status"] in ("merged", "blocked", "drafted", "reviewed"):
                if st["status"] != "merged":
                    why = st["why"] or ("integration waits for " + ", ".join(
                        d for d in i["integrate_after"] if s["items"][d]["status"] != "merged") if st["status"] != "blocked" else "")
                    out["waiting"].append({"id": i["id"], "status": st["status"], "why": why or "awaiting review or merge"})
                continue
            blockers = [d for d in i["start_after"] if s["items"][d]["status"] != "merged"]
            if any(s["items"][d]["status"] == "blocked" for d in _ancestors(_edges(s), i["id"])):
                st.update(status="blocked", why="a prerequisite is blocked")
                _event(run, "blocked", id=i["id"], why=st["why"])
                out["waiting"].append({"id": i["id"], "status": "blocked", "why": st["why"]}); continue
            if blockers:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "start waits for " + ", ".join(blockers)}); continue
            if out["stopped"]:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": out["stopped"]}); continue
            if len(running) >= s["plan"]["max_workers"]:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "all workers busy"}); continue
            if i["estimate_usd"] > _remaining(s) + 1e-9:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": f"budget: ${_remaining(s):.2f} left, needs ${i['estimate_usd']:.2f}"}); continue
            st["attempts"] += 1
            key = f"{i['id']}#{st['attempts']}"
            s["reserved"][key] = i["estimate_usd"]       # reserved before the launch, released or settled after
            base = s["base"] if not i["start_after"] else s["integration_head"]
            claim = {"id": i["id"], "n": i["n"], "attempt": st["attempts"], "base": base,
                     "branch": f"swarm/{i['id']}-a{st['attempts']}", "writes": i["writes"], "contracts": i["contracts"],
                     "return": ["head SHA or patch", "tests run and their result", "unresolved issues"],
                     "may_not": ["dispatch workers", "write run state", "merge", "deploy", "read the holdout"]}
            st.update(status="dispatched", why=None, claim=claim)
            running.append(i["id"])
            _event(run, "dispatch", **{k: claim[k] for k in ("id", "attempt", "base", "branch")}, reserved=i["estimate_usd"])
            out["dispatch"].append(claim)
        return out
    return mutate(run, go)


def _edges(s):
    e = {i["id"]: set(i["start_after"]) | set(i["integrate_after"]) for i in s["plan"]["items"]}
    for a, b in s["plan"]["order"]:
        e[b].add(a)
    return e


def _attempt(st, attempt, iid):
    if st["status"] not in RUNNING or st["attempts"] != attempt:
        raise ValueError(f"{iid} attempt {attempt} isn't in flight (status {st['status']}, attempt {st['attempts']})")


def launched(run, iid, attempt):
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        st["status"] = "running"; st["started_at"] = now()
        _event(run, "launched", id=iid, attempt=attempt)
    mutate(run, go)


def launch_failed(run, iid, attempt, reason):
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        s["reserved"].pop(f"{iid}#{attempt}", None)      # nothing ran, nothing is charged
        st.update(status="blocked" if st["attempts"] >= MAX_LAUNCHES else "pending",
                  why=f"launch failed: {reason}")
        _event(run, "launch_failed", id=iid, attempt=attempt, reason=reason)
    mutate(run, go)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout.strip()


def result(run, iid, attempt, head, repo, tests, cost=None, unresolved=""):
    """Check the worker's actual diff against its assignment before anything else believes it."""
    def go(s):
        i, st = _item(s, iid); _attempt(st, attempt, iid)
        base = st["claim"]["base"]
        files = [f for f in git(repo, "diff", "--name-only", f"{base}..{head}").splitlines() if f]
        outside = [f for f in files if not any(fnmatch.fnmatch(f, w) or f == w for w in i["writes"])]
        changed = [c["path"] for c in i["contracts"] if c["path"] in files]
        res = s["reserved"].pop(f"{iid}#{attempt}", 0.0)
        s["spent"] += float(cost) if cost is not None else res   # settle: the actual cost, else the reservation
        st["finished_at"] = now()
        if outside or changed or tests != "passed" or not files:
            why = ("wrote outside its paths: " + ", ".join(outside)) if outside else \
                  ("changed a pinned contract: " + ", ".join(changed)) if changed else \
                  ("tests " + tests) if tests != "passed" else "returned no change"
            st.update(status="pending" if st["attempts"] < MAX_LAUNCHES and not outside and not changed else "blocked", why=why)
            _event(run, "result_rejected", id=iid, attempt=attempt, head=head, why=why)
            return {"accepted": False, "why": why}
        st.update(status="drafted", why=None, evidence={"head": head, "base": base, "files": files, "tests": tests,
                                                        "unresolved": unresolved, "attempt": attempt})
        _event(run, "result", id=iid, attempt=attempt, head=head, files=len(files), tests=tests)
        return {"accepted": True, "files": files}
    return mutate(run, go)


def review(run, iid, head, outcome, review_id=None):
    """Rounds are counted per item, across attempts: redispatching a worker never resets the cap."""
    def go(s):
        _, st = _item(s, iid)
        if st["status"] not in ("drafted", "reviewed") or not st["evidence"] or st["evidence"]["head"] != head:
            raise ValueError(f"{iid}: review must be of the drafted head {st['evidence'] and st['evidence']['head']}, not {head}")
        st["review_rounds"] += 1
        if outcome == "clean":
            st.update(status="reviewed", review={"head": head, "id": review_id})
        elif st["review_rounds"] >= s["review_cap"]:
            st.update(status="blocked", why=f"review cap {s['review_cap']} reached")
        else:
            st.update(status="pending", why=f"review round {st['review_rounds']} found blocking findings")
        _event(run, "review", id=iid, head=head, outcome=outcome, rounds=st["review_rounds"], review_id=review_id)
        return st["status"]
    return mutate(run, go)


def refresh(run, iid, head, repo, target, tests):
    """The target moved under a drafted or reviewed item: the coordinator rebuilt the item on it (rebase or merge of the
    target) and reran its tests. The new head is checked against the claim as a result is, from the target, and any
    review of the old head no longer counts. Review rounds are kept."""
    def go(s):
        i, st = _item(s, iid)
        if st["status"] not in ("drafted", "reviewed"):
            raise ValueError(f"{iid} is {st['status']}; only a drafted or reviewed item is refreshed")
        tip = git(repo, "rev-parse", target)
        try:
            git(repo, "merge-base", "--is-ancestor", tip, head)
        except subprocess.CalledProcessError:
            raise ValueError(f"{head[:12]} isn't built on {target} at {tip[:12]}")
        files = [f for f in git(repo, "diff", "--name-only", f"{tip}..{head}").splitlines() if f]
        outside = [f for f in files if not any(fnmatch.fnmatch(f, w) or f == w for w in i["writes"])]
        changed = [c["path"] for c in i["contracts"] if c["path"] in files]
        if outside or changed or tests != "passed" or not files:
            why = ("refresh wrote outside its paths: " + ", ".join(outside)) if outside else \
                  ("refresh changed a pinned contract: " + ", ".join(changed)) if changed else \
                  ("refresh tests " + tests) if tests != "passed" else "refresh carries no change"
            st.update(status="blocked", why=why)
            _event(run, "refresh_rejected", id=iid, head=head, why=why)
            return {"accepted": False, "why": why}
        st.update(status="drafted", review=None, why=None,
                  evidence=dict(st["evidence"], head=head, base=tip, files=files, tests=tests, refreshed_from=st["evidence"]["head"]))
        _event(run, "refreshed", id=iid, head=head, base=tip)
        return {"accepted": True, "files": files}
    return mutate(run, go)


def blocked(run, iid, reason):
    def go(s):
        _, st = _item(s, iid)
        st.update(status="blocked", why=reason)
        _event(run, "blocked", id=iid, why=reason)
    mutate(run, go)


def merge_gate(run, iid, repo, target, halted=False):
    """[] when the item may merge now; else every reason it may not. The candidate must be the reviewed head,
    rebased on the actual target, with every integration prerequisite merged."""
    s = load(run)
    i, st = _item(s, iid)
    reasons = []
    if halted:
        reasons.append("HALT")
    if st["status"] != "reviewed":
        reasons.append(f"status is {st['status']}, not reviewed")
    else:
        if st["review"]["head"] != st["evidence"]["head"]:
            reasons.append("review head differs from the tested head")
        tip = git(repo, "rev-parse", target)
        if tip != s["integration_head"]:
            reasons.append(f"target moved to {tip[:12]} since the coordinator's last merge {s['integration_head'][:12]}")
        try:
            git(repo, "merge-base", "--is-ancestor", tip, st["evidence"]["head"])
        except subprocess.CalledProcessError:
            reasons.append(f"evidence at {st['evidence']['head'][:12]} isn't built on the target {tip[:12]}; refresh review and checks")
    reasons += [f"integration waits for {d}" for d in sorted(_edges(s)[iid]) if s["items"][d]["status"] != "merged"]
    return reasons


def merged(run, iid, sha):
    def go(s):
        _, st = _item(s, iid)
        if st["status"] != "reviewed":
            raise ValueError(f"{iid} isn't reviewed")
        st.update(status="merged", merged=sha); s["integration_head"] = sha
        _event(run, "merged", id=iid, sha=sha)
    mutate(run, go)


def status(run):
    s = load(run)
    return {"budget": s["budget"], "spent": round(s["spent"], 4), "reserved": round(sum(s["reserved"].values()), 4),
            "integration_head": s["integration_head"],
            "items": {k: {x: v.get(x) for x in ("status", "attempts", "review_rounds", "why", "started_at", "finished_at")}
                      for k, v in s["items"].items()}}


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd"); p.add_argument("path"); p.add_argument("id", nargs="?")
    for f in ("--goal", "--base", "--budget", "--halt", "--reason", "--head", "--repo", "--tests", "--cost",
              "--unresolved", "--outcome", "--review-id", "--target", "--sha"):
        p.add_argument(f)
    p.add_argument("--attempt", type=int); p.add_argument("--review-cap", type=int, default=3)
    p.add_argument("--spend-stop", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "check":
            plan = load_plan(a.path); print(json.dumps({"serial": plan["serial"], "max_workers": plan["max_workers"],
                                                        "items": [i["id"] for i in plan["items"]]})); return 0
        if a.cmd == "init":
            init(a.path, a.goal, a.base, a.budget, a.review_cap); print("ok"); return 0
        halted = bool(a.halt) and Path(a.halt).exists()
        if a.cmd == "tick":
            print(json.dumps(tick(a.path, halted, a.spend_stop), indent=1)); return 0
        if a.cmd == "launched":
            launched(a.path, a.id, a.attempt); return 0
        if a.cmd == "launch-failed":
            launch_failed(a.path, a.id, a.attempt, a.reason); return 0
        if a.cmd == "result":
            r = result(a.path, a.id, a.attempt, a.head, a.repo, a.tests, a.cost, a.unresolved or "")
            print(json.dumps(r)); return 0 if r["accepted"] else 1
        if a.cmd == "review":
            print(review(a.path, a.id, a.head, a.outcome, a.review_id)); return 0
        if a.cmd == "refresh":
            r = refresh(a.path, a.id, a.head, a.repo, a.target, a.tests); print(json.dumps(r)); return 0 if r["accepted"] else 1
        if a.cmd == "blocked":
            blocked(a.path, a.id, a.reason); return 0
        if a.cmd == "merge-gate":
            r = merge_gate(a.path, a.id, a.repo, a.target, halted); print(json.dumps(r)); return 0 if not r else 1
        if a.cmd == "merged":
            merged(a.path, a.id, a.sha); return 0
        if a.cmd == "status":
            print(json.dumps(status(a.path), indent=1)); return 0
    except ValueError as e:
        print(f"swarm: {e}", file=sys.stderr); return 2
    print(f"swarm: unknown command {a.cmd}", file=sys.stderr); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
