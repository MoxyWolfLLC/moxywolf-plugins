#!/usr/bin/env python3
"""GO-017: build and test independent work in parallel; integrate in dependency order through one coordinator.

A goal's PLAN.md stays as goal_brief.py checks it. A parallel plan adds goals/<id>/DEPS.json beside it, approved
and frozen with the goal; without one the plan is serial (each item starts after the one before), exactly the
one-item loop goal_run.py has always run.

DEPS.json: {"version": 1, "max_workers": positive integer (default: how many items can start together, at most 10, XE-049.10),
            "items": {"<plan item n>": {"id": "page", "writes": ["assets/x.html", "tests/test_x.py"],
                                        "start_after": [], "integrate_after": ["cli"],
                                        "contracts": [{"path": "assets/gate.js", "sha256": "..."}],
                                        "estimate_usd": 2.0}},
            "order": [["cli", "page"]]}
A start dependency blocks dispatch until the dependency has merged. An integration dependency blocks only the
merge: the item is drafted and tested against its pinned contracts meanwhile. Two items that write the same
path need an order between them (integrate_after, directly or through others, or an "order" pair).

The coordinator is the only writer of <run>/swarm.json. Workers get a claim (item, attempt, pinned base, branch,
writable paths, contracts, what to return) and return the head SHA they committed on the claim's branch, test results
and unresolved issues.
They don't dispatch workers, write run state, merge, deploy or see the holdout.

  swarm.py check <goal dir>                                   validate DEPS.json against PLAN.md
  swarm.py init <run> --goal <goal dir> --base <sha> --budget <usd> [--review-cap N]
                                                              --budget is a dispatch budget, not a spend cap
                                                              the cap is the brief's Max review rounds per item when
                                                              the goal has a GOAL.md; --review-cap must then agree
  swarm.py tick <run> [--halt <path>] [--spend-stop]          claims eligible items up to the goal and applicable host ceiling
  swarm.py launched <run> <id> --attempt N                    the Agent call started
  swarm.py launch-sent <run> <id> --attempt N [--halt <path>] [--spend-stop]  opt-in pre-send check
  swarm.py launch-failed <run> <id> --attempt N --reason R [--host-refused]    it didn't; visible, retried by a later tick
  swarm.py apply-patch <run> <id> --attempt N --repo R --patch FILE
                                                              a returned patch, committed on the claim's branch at its
                                                              pinned base; prints the head to pass to result
  swarm.py result <run> <id> --attempt N --head SHA --repo R --tests passed|failed [--cost USD] [--unresolved T]
  swarm.py review <run> <id> --head SHA --outcome clean|blocking [--review-id ID]
  swarm.py refresh <run> <id> --head SHA --repo R --target <ref> --tests passed|failed
                                                              rebuilt on a moved target; its review must run again
  swarm.py blocked <run> <id> --reason R                      stops the item and its dependents only
  swarm.py merge-gate <run> <id> --repo R --target <ref>      exit 0 only when this item may merge now
  swarm.py merged <run> <id> --sha SHA
  swarm.py status <run>
  swarm.py viewer-start <run>                                 optional: start the agent-flow viewer (Mac only, 127.0.0.1)
  swarm.py viewer-stop <run>                                  stop it; neither command writes swarm.json or the event log
  swarm.py goal-run [<goal id>]                               the swarm run to view (GO-025): the named goal's, or the one goal
                                                              under GSTACK_GOAL_RUN_DIR running a swarm; writes nothing
"""
import argparse
import fcntl
import os
import platform
import shutil
import signal
import socket
import fnmatch
import math
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from task_graph import write   # the graph's atomic write, reused

DEFAULT_WORKERS = 3        # GO-023: a width above this takes the launch-sent path
WIDTH_CAP = 10             # XE-049.10: the derived default never exceeds this; an explicit max_workers may
MAX_LAUNCHES = 2           # a launch that failed twice is blocked, not retried forever
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
RUNNING = ("dispatched", "sent", "running")
DEFAULT_ESTIMATE = 1.0


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


TOP_KEYS = {"version", "max_workers", "items", "order"}
ITEM_KEYS = {"id", "writes", "start_after", "integrate_after", "contracts", "estimate_usd"}


def money(value, what, positive=False):
    """A dollar amount the coordinator can do arithmetic on: a finite number, not negative, above zero where
    `positive` (review 20261119-203612 F11: a negative estimate or a NaN cost turned every budget comparison off)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{what} must be a number of dollars")
    try:
        v = float(value)
    except ValueError:
        raise ValueError(f"{what} must be a number of dollars, not {value!r}")
    if not math.isfinite(v) or v < 0 or (positive and v == 0):
        raise ValueError(f"{what} must be a finite dollar amount {'above' if positive else 'at or above'} zero, not {value!r}")
    return v


def refuse_hard_cap(goal_dir, deps):
    """Dorian, 2026-11-19: swarm workers are Agent-tool workers, and nothing can stop one from spending past its
    reservation once launched, so the swarm's budget limits dispatch only. A goal that needs a hard dollar cap is
    refused here rather than run on a promise the coordinator can't keep."""
    if deps.get("hard_dollar_cap"):
        raise ValueError("this goal requires a hard dollar cap; swarm workers can't be held to one, so it can't run as a swarm")
    unknown = set(deps) - TOP_KEYS - {"hard_dollar_cap"}
    unknown |= {f"items.{k}.{x}" for k, v in (deps.get("items") or {}).items() if isinstance(v, dict) for x in set(v) - ITEM_KEYS}
    if unknown:
        raise ValueError(f"DEPS.json has keys the coordinator doesn't read: {sorted(unknown)}")
    brief = Path(goal_dir) / "GOAL.md"
    if brief.is_file():
        m = re.search(r"^## Spend cap\s*\n(.*?)(?=^## |\Z)", brief.read_text(), re.M | re.S)
        if m and re.search(r"\bhard\b", m.group(1), re.I):
            raise ValueError("the brief's Spend cap asks for a hard cap; swarm workers can't be held to one, so it can't run as a swarm")


def plan_numbers(plan_text):
    return [int(m.group(1)) for m in re.finditer(r"^(\d+)\.\s+\S", plan_text, re.M)]


GLOB = re.compile(r"[*?\[]")


def _glob_overlap(a, b):
    """Could two writable patterns name the same path? A literal against a pattern is exact; two patterns compare
    their literal prefixes, so any glob syntax ([ab] included, review F1) errs toward asking for an order."""
    # ponytail: two globs that only meet in the middle ("*.py" vs "a/*") read as overlapping, never as a race
    ga, gb = bool(GLOB.search(a)), bool(GLOB.search(b))
    if not ga and not gb:
        return a == b
    if ga != gb:
        lit, pat = (b, a) if ga else (a, b)
        return fnmatch.fnmatchcase(lit, pat)
    pa, pb = GLOB.split(a)[0], GLOB.split(b)[0]
    return pa.startswith(pb) or pb.startswith(pa)


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
    refuse_hard_cap(goal_dir, d)
    if not isinstance(d, dict) or not isinstance(d.get("items"), dict):
        raise ValueError("DEPS.json needs an items object keyed by PLAN.md item number")
    if sorted(int(k) for k in d["items"]) != sorted(numbers):
        raise ValueError(f"DEPS.json items {sorted(d['items'])} don't match PLAN.md items {numbers}")
    brief = goal_dir / "GOAL.md"
    width = d.get("max_workers")
    if type(width) is int and width > DEFAULT_WORKERS and brief.is_file() and re.search(r"^## Hard cap\s*$", brief.read_text(), re.M):
        raise ValueError("this goal requires a hard dollar cap; it cannot opt into a wider swarm")
    items = []
    for k, v in sorted(d["items"].items(), key=lambda kv: int(kv[0])):
        items.append({"n": int(k), "id": v.get("id"), "writes": v.get("writes") or [], "start_after": v.get("start_after", []),
                      "integrate_after": v.get("integrate_after", []), "contracts": v.get("contracts", []),
                      "estimate_usd": money(v.get("estimate_usd", DEFAULT_ESTIMATE), f"item {k} estimate_usd", positive=True)})
    if width is None:                                  # XE-049.10: as wide as the items that can start together
        width = start_width(items)
        if brief.is_file() and re.search(r"^## Hard cap\s*$", brief.read_text(), re.M):
            width = min(width, DEFAULT_WORKERS)
    return validate({"version": d.get("version"), "max_workers": width, "serial": False,
                     "items": items, "order": d.get("order", [])})


def start_width(items):
    """Items that can be dispatched together at the start: no start_after, and no write overlapping one already
    counted. At least 1, at most WIDTH_CAP. ponytail: greedy in plan order, not the largest such set."""
    chosen = []
    for i in items:
        if not i["start_after"] and not any(_glob_overlap(a, b) for c in chosen for a in c["writes"] for b in i["writes"]):
            chosen.append(i)
    return max(1, min(len(chosen), WIDTH_CAP))


def validate(plan):
    items = plan["items"]
    ids = [i["id"] for i in items]
    if plan.get("version") != 1:
        raise ValueError("DEPS.json version must be 1")
    if type(plan["max_workers"]) is not int or plan["max_workers"] < 1:
        raise ValueError("max_workers must be a positive integer")
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


def goal_review_cap(goal_dir):
    """The brief's Max review rounds per item, when the goal has a brief (review F8)."""
    f = Path(goal_dir) / "GOAL.md"
    if not f.is_file():
        return None
    m = re.search(r"^## Max review rounds per item\s*\n+\s*(\d+)", f.read_text(), re.M)
    if not m:
        raise ValueError(f"{f} has no Max review rounds per item")
    return int(m.group(1))


def host_file(run):
    host = socket.gethostname()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,255}", host):
        raise ValueError("host name cannot name a host record")
    root = os.environ.get("GSTACK_GOAL_RUN_DIR")
    return (Path(root).resolve() if root else Path(run).resolve().parent) / "hosts" / f"{host}.json"


def host_limit(path, running=None):
    """Read or lower the opt-in ceiling under the host lock; never reset or raise it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = json.loads(path.read_text()) if path.is_file() else {"limit": None}
        cap = record["limit"]
        if cap is not None and (type(cap) is not int or cap < 1):
            raise ValueError("invalid saved host limit")
        if running is None:
            return cap
        value = max(1, running)
        if cap is not None:
            value = min(value, cap)
        record["limit"] = value
        write(path, record)
        return cap, value


def _ceiling(s):
    cap = s["plan"]["max_workers"]
    host = host_limit(s["host_file"]) if s.get("host_file") else None
    return cap if host is None else min(cap, host)


def _held(s):
    return sum(1 for v in s["items"].values() if v["status"] in ("running", "sent") or
               (v["status"] == "blocked" and v.get("inflight") and v.get("sent")))


def _release_unsent(run, s, ceiling, why):
    claims = sorted((v["claim"]["seq"], item) for item, v in s["items"].items() if v["status"] == "dispatched")
    held = _held(s)
    for rank, (_, item) in enumerate(claims, 1):
        if held + rank > ceiling:
            v = s["items"][item]
            s["reserved"].pop(f"{item}#{v['inflight']}", None)
            v.update(status="pending", inflight=None, why=why)
            _event(run, "claim_returned", id=item, attempt=v["attempts"], why=why)


def init(run, goal_dir, base, budget, review_cap=None):
    plan = load_plan(goal_dir)
    brief_cap = goal_review_cap(goal_dir)
    if brief_cap is not None and review_cap is not None and review_cap != brief_cap:
        raise ValueError(f"--review-cap {review_cap} differs from the brief's Max review rounds per item {brief_cap}")
    review_cap = brief_cap if brief_cap is not None else (review_cap or 3)
    run = Path(run); run.mkdir(parents=True, exist_ok=True)
    if _paths(run)[0].exists():
        raise ValueError(f"{run} already has a swarm; resume it with tick")
    s = {"plan": plan, "base": base, "integration_head": base, "budget": money(budget, "--budget", positive=True), "spent": 0.0,
         "reserved": {}, "review_cap": review_cap,
         "items": {i["id"]: {"status": "pending", "attempts": 0, "review_rounds": 0, "evidence": None, "why": None}
                   for i in plan["items"]}}
    if plan["max_workers"] > DEFAULT_WORKERS:
        s.update(host_file=str(host_file(run)), seq=0)
    write(_paths(run)[0], s)
    _event(run, "init", base=base, budget=budget, serial=plan["serial"], items=[i["id"] for i in plan["items"]])
    return s


def _item(s, iid):
    if iid not in s["items"]:
        raise ValueError(f"no item {iid}")
    return next(i for i in s["plan"]["items"] if i["id"] == iid), s["items"][iid]


def _settle(run, s, iid, attempt, reserved, cost):
    """Settle one attempt's spend once. A reported dollar cost is charged as reported, overrun included; with none
    (a host that reports tokens, not dollars) the reservation is charged and the attempt is marked estimated, so the
    ledger never shows a dollar figure nobody measured."""
    # Dorian, 2026-11-19: an Agent-tool worker's cost can't be verified (the host reports tokens), so the full
    # reservation stays charged; a reported figure can only add to it, never release part of it.
    reported = money(cost, "--cost") if cost is not None else None
    charged = max(reserved, reported) if reported is not None else reserved
    s["spent"] += charged
    s["estimated"] = s.get("estimated", 0) + 1   # every settlement so far: no verified cost source exists
    if charged > reserved + 1e-9:
        _event(run, "overrun", id=iid, attempt=attempt, reserved=reserved, charged=charged)
    if s["spent"] > s["budget"] + 1e-9:
        _event(run, "over_budget", id=iid, attempt=attempt, spent=round(s["spent"], 4), budget=s["budget"])
    _event(run, "settled", id=iid, attempt=attempt, reserved=reserved, reported=reported, charged=charged, verified=False)


def _remaining(s):
    return s["budget"] - s["spent"] - sum(s["reserved"].values())


def _brief_checks(run):
    """XE-049.16: the goal run's brief checks, from the state goal_run.py keeps beside the swarm folder; None for a
    swarm with no goal run around it, or one started before XE-049.16."""
    try:
        return json.loads((Path(run).parent / "state.json").read_text()).get("brief_checks")
    except (OSError, ValueError):
        return None


def tick(run, halted=False, spend_stop=False):
    """Claim every eligible item up to max_workers. Never claims an item that is already claimed, so a restarted
    coordinator that ticks again dispatches nothing twice. Returns what to launch, what's running, and why the
    rest waits."""
    def go(s):
        out = {"dispatch": [], "running": [], "waiting": [], "stopped": None}
        for k, v in list(s["items"].items()):             # an item blocked by any path blocks its dependents now
            if v["status"] == "blocked":
                _block(run, s, k, v["why"] or "blocked")
        if halted or spend_stop:
            out["stopped"] = "HALT" if halted else "spend stop"
        ceiling = _ceiling(s)
        writes = {i["id"]: i["writes"] for i in s["plan"]["items"]}
        checks = _brief_checks(run)
        if s.get("host_file") and out["stopped"]:
            _release_unsent(run, s, 0, out["stopped"])
        # review F9: a worker blocked while it runs holds its slot until it reports
        running = [k for k, v in s["items"].items() if v["status"] in RUNNING or (v["status"] == "blocked" and v.get("inflight"))]
        for i in s["plan"]["items"]:
            st = s["items"][i["id"]]
            if st["status"] in RUNNING:
                out["running"].append({"id": i["id"], "status": st["status"], "attempt": st["attempts"]})
                continue
            if st["status"] == "blocked" and st.get("inflight"):
                out["running"].append({"id": i["id"], "status": "blocked, worker still reporting", "attempt": st["inflight"]})
            if st["status"] in ("merged", "blocked", "drafted", "reviewed"):
                if st["status"] != "merged":
                    why = st["why"] or ("integration waits for " + ", ".join(
                        d for d in i["integrate_after"] if s["items"][d]["status"] != "merged") if st["status"] != "blocked" else "")
                    out["waiting"].append({"id": i["id"], "status": st["status"], "why": why or "awaiting review or merge"})
                continue
            c = None if checks is None else checks.get(str(i["n"]))
            if checks is not None and (c is None or any(e["settlement"] != "settled" for e in c["entries"])):
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "brief check not settled (XE-049.16)"}); continue
            blockers = [d for d in i["start_after"] if s["items"][d]["status"] != "merged"]
            if blockers:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "start waits for " + ", ".join(blockers)}); continue
            if out["stopped"]:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": out["stopped"]}); continue
            if len(running) >= ceiling:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "all workers busy"}); continue
            if s.get("host_file"):
                clash = next((k for k in running if any(_glob_overlap(a, b) for a in i["writes"] for b in writes[k])), None)
                if clash:
                    out["waiting"].append({"id": i["id"], "status": "pending", "why": f"writes overlap {clash}"}); continue
            if i["estimate_usd"] > _remaining(s) + 1e-9:
                if not running:
                    # spec review GO-017 C1: with nothing in flight no money can come back (a reservation is released
                    # only by a failed launch or a block before launch), so the item can never fit. Blocking it, and so its dependents, lets
                    # the run end through goal_run.py failed instead of waiting forever.
                    why = f"dispatch budget exhausted: ${_remaining(s):.2f} left, needs ${i['estimate_usd']:.2f}"
                    _block(run, s, i["id"], why)
                    out["waiting"].append({"id": i["id"], "status": "blocked", "why": why}); continue
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": f"budget: ${_remaining(s):.2f} left, needs ${i['estimate_usd']:.2f}"}); continue
            st["attempts"] += 1
            st["inflight"] = st["attempts"]
            key = f"{i['id']}#{st['attempts']}"
            s["reserved"][key] = i["estimate_usd"]       # reserved before the launch, released or settled after
            base = s["base"] if not i["start_after"] else s["integration_head"]
            claim = {"id": i["id"], "n": i["n"], "attempt": st["attempts"], "base": base,
                     "branch": f"swarm/{i['id']}-a{st['attempts']}", "writes": i["writes"], "contracts": i["contracts"],
                     "return": ["head SHA committed on the claim's branch, or a patch against the pinned base", "tests run and their result", "unresolved issues"],
                     "may_not": ["dispatch workers", "write run state", "merge", "deploy", "read the holdout"]}
            if s.get("host_file"):
                s["seq"] += 1
                claim["seq"] = s["seq"]
                st["started_at"] = None
            st.update(status="dispatched", why=None, claim=claim, sent=False)
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
    """The attempt must be the one in flight. A worker that was blocked while running may still report, so its
    reservation settles (review F5); its result is kept as evidence and the item stays blocked."""
    if st.get("inflight") != attempt or st["status"] not in RUNNING + ("blocked",):
        raise ValueError(f"{iid} attempt {attempt} isn't in flight (status {st['status']}, attempt {st['attempts']})")


def launch_sent(run, iid, attempt, halted=False, spend_stop=False):
    """For an opt-in swarm, validate and hold the slot in one run-state update immediately before sending."""
    def go(s):
        if not s.get("host_file"):
            raise ValueError("launch-sent is for swarms opted into more than three workers")
        _, st = _item(s, iid)
        if st["status"] != "dispatched" or st.get("inflight") != attempt:
            return "do not launch: no matching unsent claim"
        if halted or spend_stop or s["spent"] > s["budget"] + 1e-9:
            reason = "HALT" if halted else "spend stop"
            _release_unsent(run, s, 0, reason)
            return f"do not launch: {reason}"
        _release_unsent(run, s, _ceiling(s), "above the host limit")
        if st["status"] != "dispatched":
            return "do not launch: above the host limit"
        st.update(status="sent", sent=True)
        _event(run, "launch_sent", id=iid, attempt=attempt)
        return "launch"
    return mutate(run, go)


def launched(run, iid, attempt):
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        if s.get("host_file") and st["status"] != "sent" and not (st["status"] == "blocked" and st.get("sent")):
            raise ValueError(f"{iid}: only a sent launch can be acknowledged")
        if st["status"] == "blocked":
            if not st.get("sent"):
                raise ValueError(f"{iid} was blocked before its launch was recorded")
        else:
            st["status"] = "running"
        st["started_at"] = now()
        _event(run, "launched", id=iid, attempt=attempt)
    mutate(run, go)


def launch_failed(run, iid, attempt, reason, host_refused=False):
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        wide = s.get("host_file")
        if host_refused and not wide:
            raise ValueError("host backoff is for swarms opted into more than three workers")
        if wide and st["status"] != "sent" and not (st["status"] == "blocked" and st.get("sent")):
            raise ValueError(f"{iid}: only a sent launch can fail")
        if host_refused:
            held = _held(s) - 1
            previous, ceiling = host_limit(wide, held)
        s["reserved"].pop(f"{iid}#{attempt}", None)      # nothing ran, nothing is charged
        st.update(inflight=None, sent=False)
        if host_refused:
            if st["status"] != "blocked":
                st.update(status="pending", why=f"host refused: {reason}")
            _release_unsent(run, s, min(s["plan"]["max_workers"], ceiling), "above the reduced host limit")
            _event(run, "host_refused", id=iid, attempt=attempt, running=held, limit=ceiling, reason=reason)
            if previous != 1:
                return
        st["launch_failures"] = st.get("launch_failures", 0) + 1   # review F3: its own count, not the attempt number
        if st["status"] != "blocked":
            if st["launch_failures"] >= MAX_LAUNCHES:
                _block(run, s, iid, f"launch failed {st['launch_failures']} times: {reason}")
            else:
                st.update(status="pending", why=f"launch failed: {reason}")
        _event(run, "launch_failed", id=iid, attempt=attempt, reason=reason)
    mutate(run, go)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout.strip()


def _changed(repo, base, head):
    """Every path the change touches, both sides of a rename (review F6): a pinned contract moved away is a change to it.
    Paths come NUL-delimited and unquoted (-z), so the writable-path and pinned-contract checks compare the literal
    names; without -z git quotes and escapes a name such as caf\u00e9.json (review 20261119-212242 F1)."""
    out = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", "--no-renames", "-z", f"{base}..{head}"],
                         capture_output=True, check=True).stdout.decode("utf-8", "surrogateescape")
    return sorted({f for f in out.split("\0") if f})


def apply_patch(run, iid, attempt, repo, patch):
    """A worker returned a patch, not a head: the coordinator applies it to the claim's branch at the pinned base in a
    worktree of its own, commits it as the bot, and returns the head for result to check like any other."""
    st = load(run)["items"][iid]
    _attempt(st, attempt, iid)
    claim = st["claim"]
    wt = Path(tempfile.mkdtemp(prefix=f"swarm-{iid}-"))
    try:
        git(repo, "worktree", "add", "-q", "-B", claim["branch"], str(wt), claim["base"])
        git(wt, "apply", "--index", "--whitespace=nowarn", str(Path(patch).resolve()))
        git(wt, "-c", "user.name=moxywolf-agent[bot]", "-c", "user.email=331509232+moxywolf-agent[bot]@users.noreply.github.com",
            "commit", "-q", "-m", f"{iid}: worker patch, attempt {attempt}")
        return git(wt, "rev-parse", "HEAD")
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], capture_output=True)


def result(run, iid, attempt, head, repo, tests, cost=None, unresolved=""):
    """Check the worker's actual diff against its assignment before anything else believes it."""
    def go(s):
        i, st = _item(s, iid); _attempt(st, attempt, iid)
        if s.get("host_file") and st["status"] != "running" and not (
            st["status"] == "blocked" and st.get("started_at")
        ):
            raise ValueError(f"{iid}: a result needs a host-acknowledged launch")
        base = st["claim"]["base"]
        files = _changed(repo, base, head)
        outside = [f for f in files if not any(fnmatch.fnmatch(f, w) or f == w for w in i["writes"])]
        changed = [c["path"] for c in i["contracts"] if c["path"] in files]
        res = s["reserved"].pop(f"{iid}#{attempt}", 0.0)
        _settle(run, s, iid, attempt, res, cost)
        st["finished_at"] = now(); st["inflight"] = None
        if st["status"] == "blocked":                    # blocked while it ran: the spend settles, nothing advances
            _event(run, "result_after_block", id=iid, attempt=attempt, head=head)
            return {"accepted": False, "why": "the item was blocked while this attempt ran: " + (st["why"] or "")}
        if outside or changed or tests != "passed" or not files:
            why = ("wrote outside its paths: " + ", ".join(outside)) if outside else \
                  ("changed a pinned contract: " + ", ".join(changed)) if changed else \
                  ("tests " + tests) if tests != "passed" else "returned no change"
            st["result_failures"] = st.get("result_failures", 0) + 1
            if st["result_failures"] < MAX_LAUNCHES and not outside and not changed:
                st.update(status="pending", why=why)
            else:
                _block(run, s, iid, why)
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
            _block(run, s, iid, f"review cap {s['review_cap']} reached")
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
        files = _changed(repo, tip, head)
        outside = [f for f in files if not any(fnmatch.fnmatch(f, w) or f == w for w in i["writes"])]
        changed = [c["path"] for c in i["contracts"] if c["path"] in files]
        if outside or changed or tests != "passed" or not files:
            why = ("refresh wrote outside its paths: " + ", ".join(outside)) if outside else \
                  ("refresh changed a pinned contract: " + ", ".join(changed)) if changed else \
                  ("refresh tests " + tests) if tests != "passed" else "refresh carries no change"
            _block(run, s, iid, why)
            _event(run, "refresh_rejected", id=iid, head=head, why=why)
            return {"accepted": False, "why": why}
        st.update(status="drafted", review=None, why=None,
                  evidence=dict(st["evidence"], head=head, base=tip, files=files, tests=tests, refreshed_from=st["evidence"]["head"]))
        _event(run, "refreshed", id=iid, head=head, base=tip)
        return {"accepted": True, "files": files}
    return mutate(run, go)


def blocked(run, iid, reason):
    def go(s):
        _item(s, iid)
        _block(run, s, iid, reason)
    mutate(run, go)


def _block(run, s, iid, reason):
    """Block an item and, at once, every unmerged item that depends on it by any edge (review F4). A claim that never
    launched gives its reservation back (F5); one that is running keeps it until its worker reports."""
    edges = _edges(s)
    hit = [iid] + [j for j in edges if iid in _ancestors(edges, j)]
    for j in hit:
        st = s["items"][j]
        if st["status"] in ("merged", "blocked"):
            continue
        if st["status"] == "dispatched":
            s["reserved"].pop(f"{j}#{st['attempts']}", None); st["inflight"] = None
        st.update(status="blocked", why=reason if j == iid else f"a prerequisite is blocked ({iid})")
        _event(run, "blocked", id=j, why=st["why"])


def merge_gate(run, iid, repo, target, halted=False):
    """[] when the item may merge now; else every reason it may not. The candidate must be the reviewed head,
    rebased on the actual target, with every integration prerequisite merged."""
    s = load(run)
    i, st = _item(s, iid)
    reasons = []
    if halted:
        reasons.append("HALT")
    # XE-049.5: no per-item review; a drafted item whose tests passed may integrate, and the whole-goal review gates main
    if st["status"] not in ("drafted", "reviewed"):
        reasons.append(f"status is {st['status']}, not drafted or reviewed")
    elif (st["evidence"] or {}).get("tests") != "passed":
        reasons.append("its tests didn't pass at the drafted head")
    elif st["status"] == "reviewed" and st["review"]["head"] != st["evidence"]["head"]:
        reasons.append("review head differs from the tested head")
    tip = git(repo, "rev-parse", target)                 # review F7: a moved target is reported for any item
    if tip != s["integration_head"]:
        reasons.append(f"target moved to {tip[:12]} since the coordinator's last merge {s['integration_head'][:12]}")
    if st.get("evidence"):
        try:
            git(repo, "merge-base", "--is-ancestor", tip, st["evidence"]["head"])
        except subprocess.CalledProcessError:
            reasons.append(f"evidence at {st['evidence']['head'][:12]} isn't built on the target {tip[:12]}; refresh review and checks")
    reasons += [f"integration waits for {d}" for d in sorted(_edges(s)[iid]) if s["items"][d]["status"] != "merged"]
    return reasons


def merged(run, iid, sha):
    def go(s):
        _, st = _item(s, iid)
        if st["status"] not in ("drafted", "reviewed"):
            raise ValueError(f"{iid} isn't drafted or reviewed")
        st.update(status="merged", merged=sha); s["integration_head"] = sha
        _event(run, "merged", id=iid, sha=sha)
    mutate(run, go)


def status(run):
    s = load(run)
    return {"budget": s["budget"], "spent": round(s["spent"], 4), "reserved": round(sum(s["reserved"].values()), 4),
            "over_budget": s["spent"] > s["budget"] + 1e-9, "estimated_settlements": s.get("estimated", 0),
            "integration_head": s["integration_head"],
            "items": {k: {x: v.get(x) for x in ("status", "attempts", "review_rounds", "why", "started_at", "finished_at")}
                      for k, v in s["items"].items()}}


# The optional agent viewer (swarm-agent-view): agent-flow-app, pinned. Mac only, and the viewer binds 127.0.0.1 by default;
# no host option is passed. Its first start adds its own hooks to the user's ~/.claude/settings.json (it does that, never this
# file). A missing viewer never stops the swarm: both commands exit 0 when it is unavailable. Only <run>/viewer.pid is written.
VIEWER_PACKAGE = "agent-flow-app@0.9.6"


def _viewer_stamp(pid):
    """The process start time (ps lstart): a reused pid has a different one."""
    try:   # Linux: /proc/<pid>/stat field 3 is the state, field 22 the start tick (the comm field may hold spaces)
        f = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return "" if f[0] in ("Z", "X") else f[19]   # a zombie has ended; it only waits to be reaped
    except (OSError, IndexError):
        pass
    for ps in ("/bin/ps", "/usr/bin/ps"):   # absolute: the run's PATH may not have it
        try:
            r = subprocess.run([ps, "-o", "stat=,lstart=", "-p", str(pid)], capture_output=True, text=True)
        except OSError:
            continue
        f = r.stdout.split(None, 1)
        return "" if r.returncode or len(f) < 2 or f[0].startswith("Z") else " ".join(f[1].split())
    return ""


def _viewer_record(run):
    """(pid, port) of the viewer this run started and that still runs, else None. A pid whose start time
    changed was reused by another process, and is not ours to signal."""
    try:
        pid, port, stamp = (Path(run) / "viewer.pid").read_text().strip().split(" ", 2)
        pid, port = int(pid), int(port)
    except (OSError, ValueError):
        return None
    return (pid, port) if stamp and _viewer_stamp(pid) == stamp else None


def viewer_start(run):
    if not Path(run).is_dir():
        raise ValueError(f"no run folder {run}")
    host = os.environ.get("SWARM_VIEWER_PLATFORM")   # set (even empty) wins; the real platform only when unset
    if host is None:
        host = platform.system()
    npx = shutil.which("npx")
    why = "this host is not a Mac" if host != "Darwin" else None if npx else "npx was not found"
    if why:   # unavailable: answer before any running-viewer check
        print(f"viewer: unavailable ({why}); the swarm is unaffected", file=sys.stderr)
        return 0
    record = _viewer_record(run)
    if record:
        print(f"viewer: http://127.0.0.1:{record[1]}"); return 0
    if True:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
        try:
            proc = subprocess.Popen([npx, "--yes", VIEWER_PACKAGE, "--no-open", "--port", str(port)],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    start_new_session=True)
        except OSError as e:
            why = f"it could not start: {e}"
        else:
            try:
                (Path(run) / "viewer.pid").write_text(f"{proc.pid} {port} {_viewer_stamp(proc.pid)}\n")
            except OSError as e:   # an untracked viewer could never be stopped: end it, report unavailable
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except OSError:
                    proc.terminate()
                why = f"its pid record could not be written: {e}"
            else:
                print(f"viewer: http://127.0.0.1:{port}"); return 0
    print(f"viewer: unavailable ({why}); the swarm is unaffected", file=sys.stderr)
    return 0


def viewer_stop(run):
    if not Path(run).is_dir():
        raise ValueError(f"no run folder {run}")
    record = _viewer_record(run)
    if not record:
        try:
            (Path(run) / "viewer.pid").unlink(missing_ok=True)
        except OSError:
            pass
        print("viewer: not running"); return 0
    try:   # its own process group (start_new_session), so npx's child goes with it; never a group that isn't the viewer's
        if os.getpgid(record[0]) == record[0]:
            os.killpg(record[0], signal.SIGTERM)
        else:
            os.kill(record[0], signal.SIGTERM)
    except OSError:
        print("viewer: not running"); return 0
    try:
        (Path(run) / "viewer.pid").unlink(missing_ok=True)
    except OSError:   # the viewer is stopped; a record that stays is stale and its start time no longer matches
        pass
    print("viewer: stopped"); return 0


def goal_run(goal_id=None):
    """GO-025: the swarm run folder to view, read from GSTACK_GOAL_RUN_DIR alone, so the installed plugin can run it
    (goal_run.py needs its checkout). A named goal may have ended; unnamed, it's the one goal whose state.json has no
    outcome and that has a swarm/ folder. Several or none is refused, never picked. Reads only."""
    root = os.environ.get("GSTACK_GOAL_RUN_DIR")
    if not root:
        raise ValueError("set GSTACK_GOAL_RUN_DIR to the folder goal runs live in")
    root = Path(root)
    if goal_id is not None:
        if goal_id in ("", ".", "..") or Path(goal_id).name != goal_id:
            raise ValueError(f"not a goal id: {goal_id!r}")
        d = root / goal_id
        if not (d / "state.json").is_file():
            raise ValueError(f"no run of {goal_id} under {root}")
        if not (d / "swarm").is_dir():
            raise ValueError(f"{goal_id}'s run has no swarm folder; it isn't a parallel goal")
        return d / "swarm"
    running = []
    for f in sorted(root.glob("*/state.json")):
        if not (f.parent / "swarm").is_dir():
            continue                                   # a serial goal has nothing to view
        try:
            st = json.loads(f.read_text())
        except (OSError, ValueError) as e:
            raise ValueError(f"can't read {f}: {e}")
        if not isinstance(st, dict):
            raise ValueError(f"can't read {f}: not a JSON object")
        if st.get("outcome") is None:                  # goal_run.py's own test of a run in progress
            running.append(f.parent)
    if not running:
        raise ValueError("no goal is running a swarm; name the goal to view or stop an ended goal's viewer")
    if len(running) > 1:
        raise ValueError("several goals are running a swarm, name one: " + ", ".join(d.name for d in running))
    return running[0] / "swarm"


def main(argv):
    if argv[:1] == ["goal-run"]:                       # GO-025: its own grammar, one optional id, no options
        if len(argv) > 2 or any(t.startswith("-") for t in argv[1:]):
            print("usage: swarm.py goal-run [<goal id>]", file=sys.stderr); return 2
        try:
            print(goal_run(argv[1] if len(argv) == 2 else None)); return 0
        except ValueError as e:
            print(f"swarm: goal-run refused: {e}", file=sys.stderr); return 1
    viewer_cmds = ("viewer-start", "viewer-stop")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
    p.add_argument("cmd"); p.add_argument("path"); p.add_argument("id", nargs="?")
    for f in ("--patch", "--goal", "--base", "--budget", "--halt", "--reason", "--head", "--repo", "--tests", "--cost",
              "--unresolved", "--outcome", "--review-id", "--target", "--sha"):
        p.add_argument(f)
    p.add_argument("--attempt", type=int); p.add_argument("--review-cap", type=int)
    p.add_argument("--spend-stop", action="store_true")
    p.add_argument("--host-refused", action="store_true")
    # the parser itself says which command is invoked (abbreviations and option values included);
    # a viewer command then takes exactly its run folder and no option, in any position
    usage = "usage: swarm.py viewer-start|viewer-stop <run>   (one argument, no options)"
    p.add_argument("-h", "--help", action="store_true")
    real_error = p.error
    p.error = lambda m: (_ for _ in ()).throw(ValueError(m))
    try:
        known, extra = p.parse_known_args(argv)
    except ValueError:
        known, extra = None, []
    p.error = real_error
    if (known is not None and known.cmd in viewer_cmds) or (known is None and any(t in viewer_cmds for t in argv)):
        if not (known is not None and not extra and argv == [known.cmd, known.path]):
            print(usage, file=sys.stderr); return 2
    if (known is not None and known.help) or (known is None and ("-h" in argv or "--help" in argv)):
        p.print_help(); return 0   # help never reaches a handler, whatever else is on the line
    a = p.parse_args(argv)
    try:
        if a.cmd == "check":
            plan = load_plan(a.path); print(json.dumps({"serial": plan["serial"], "max_workers": plan["max_workers"],
                                                        "items": [i["id"] for i in plan["items"]]})); return 0
        if a.cmd == "init":
            init(a.path, a.goal, a.base, a.budget, a.review_cap); print("ok"); return 0
        if a.cmd == "viewer-start":
            return viewer_start(a.path)
        if a.cmd == "viewer-stop":
            return viewer_stop(a.path)
        halted = bool(a.halt) and Path(a.halt).exists()
        if a.cmd == "tick":
            print(json.dumps(tick(a.path, halted, a.spend_stop), indent=1)); return 0
        if a.cmd == "launch-sent":
            if not a.halt:
                raise ValueError("launch-sent requires --halt")
            verdict = launch_sent(a.path, a.id, a.attempt, halted, a.spend_stop)
            print(verdict); return 0 if verdict == "launch" else 1
        if a.cmd == "launched":
            launched(a.path, a.id, a.attempt); return 0
        if a.cmd == "launch-failed":
            launch_failed(a.path, a.id, a.attempt, a.reason, a.host_refused); return 0
        if a.cmd == "apply-patch":
            print(apply_patch(a.path, a.id, a.attempt, a.repo, a.patch)); return 0
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
