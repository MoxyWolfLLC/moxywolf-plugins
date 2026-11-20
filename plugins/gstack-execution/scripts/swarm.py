#!/usr/bin/env python3
"""GO-017: build and test independent work in parallel; integrate in dependency order through one coordinator.

A goal's PLAN.md stays as goal_brief.py checks it. A parallel plan adds goals/<id>/DEPS.json beside it, approved
and frozen with the goal; without one the plan is serial (each item starts after the one before), exactly the
one-item loop goal_run.py has always run.

DEPS.json: {"version": 1, "max_workers": 5,           (optional: a positive integer, the goal's own ceiling; absent, none)
            "items": {"<plan item n>": {"id": "page", "writes": ["assets/x.html", "tests/test_x.py"],
                                        "start_after": [{"id": "cli", "because": "needs its CLI"}], "integrate_after": ["cli"],
                                        "contracts": [{"path": "assets/gate.js", "sha256": "..."}],
                                        "estimate_usd": 2.0}},
            "order": [["cli", "page"]]}
A start dependency blocks dispatch until the dependency has merged. An integration dependency blocks only the
merge: the item is drafted and tested against its pinned contracts meanwhile. Two items that write the same
path need an order between them (integrate_after, directly or through others, or an "order" pair).
A start_after entry is an item id (approved before GO-023) or {"id", "because"}.

GO-023: no fixed worker cap. tick claims every ready item while running and claimed slots stay under the smaller of
the goal's max_workers and the host limit, where each applies. The host limit lives in
<GSTACK_GOAL_RUN_DIR>/hosts/<host>.json ({limit, events, approvals_used}); only a refused launch lowers it and only an
approved retest that ran with no refusal raises it.

The coordinator is the only writer of <run>/swarm.json. Workers get a claim (item, attempt, pinned base, branch,
writable paths, contracts, what to return) and return the head SHA they committed on the claim's branch, test results
and unresolved issues.
They don't dispatch workers, write run state, merge, deploy or see the holdout.

  swarm.py check <goal dir>                                   validate DEPS.json against PLAN.md
  swarm.py init <run> --goal <goal dir> --base <sha> --budget <usd> [--review-cap N] [--host H]
               [--retest --approval <owner>/<repo>#<pr>]   a retest goes above the host limit, once per approval
                                                              --budget is a dispatch budget, not a spend cap
                                                              the cap is the brief's Max review rounds per item when
                                                              the goal has a GOAL.md; --review-cap must then agree
  swarm.py tick <run> [--halt <path>] [--spend-stop]          claims every ready item under the ceiling
  swarm.py launch-check <run> <id> --attempt N [--halt <path>] [--spend-stop]
                                                              prints launch, or do not launch: <why> (claim returned)
  swarm.py launch-sent <run> <id> --attempt N                 the launch is sent; it holds its slot until answered
  swarm.py launched <run> <id> --attempt N                    the Agent call started
  swarm.py launch-failed <run> <id> --attempt N --reason R [--host-refused]
                                                              it didn't; visible, retried by a later tick
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
"""
import argparse
import fcntl
import fnmatch
import math
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from task_graph import write   # the graph's atomic write, reused

MAX_LAUNCHES = 2           # a launch that failed twice is blocked, not retried forever
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
RUNNING = ("dispatched", "sent", "running")
HOST = re.compile(r"^[A-Za-z0-9._-]{1,255}$")
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


def is_hard_cap(goal_dir, deps):
    """GO-023.8: the marker that makes a goal hard-cap, or None. A hard-cap goal never runs through the swarm."""
    brief = Path(goal_dir) / "GOAL.md"
    text = brief.read_text() if brief.is_file() else ""
    if re.search(r"^## Hard cap\s*$", text, re.M):
        return "## Hard cap"
    if isinstance(deps, dict) and deps.get("hard_dollar_cap"):
        return "hard_dollar_cap"
    m = re.search(r"^## Spend cap\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if m and re.search(r"\bhard\b", m.group(1), re.I):
        return "Spend cap says hard"
    return None


def refuse_hard_cap(goal_dir, deps):
    """Dorian, 2026-11-19: swarm workers are Agent-tool workers, and nothing can stop one from spending past its
    reservation once launched, so the swarm's budget limits dispatch only. A goal that needs a hard dollar cap is
    refused here rather than run on a promise the coordinator can't keep."""
    if is_hard_cap(goal_dir, deps) == "hard_dollar_cap":
        raise ValueError("this goal requires a hard dollar cap; swarm workers can't be held to one, so it can't run as a swarm")
    unknown = set(deps) - TOP_KEYS - {"hard_dollar_cap"}
    unknown |= {f"items.{k}.{x}" for k, v in (deps.get("items") or {}).items() if isinstance(v, dict) for x in set(v) - ITEM_KEYS}
    if unknown:
        raise ValueError(f"DEPS.json has keys the coordinator doesn't read: {sorted(unknown)}")
    if is_hard_cap(goal_dir, {}) == "Spend cap says hard":
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
    match_plan(numbers, d)
    return plan_from_deps(d)


def match_plan(numbers, d):
    """PLAN.md's item numbers against DEPS.json's keys: the one check load_plan and goal_successor share."""
    if sorted(int(k) for k in d["items"]) != sorted(numbers):
        raise ValueError(f"DEPS.json items {sorted(d['items'])} don't match PLAN.md items {numbers}")


def plan_from_deps(d):
    """A parsed DEPS.json's validated plan, without the PLAN.md match or the hard-cap refusal (goal_successor reuses it)."""
    items = []
    for k, v in sorted(d["items"].items(), key=lambda kv: int(kv[0])):
        items.append({"n": int(k), "id": v.get("id"), "writes": v.get("writes") or [], "start_after": _start_ids(k, v.get("start_after", [])),
                      "integrate_after": v.get("integrate_after", []), "contracts": v.get("contracts", []),
                      "estimate_usd": money(v.get("estimate_usd", DEFAULT_ESTIMATE), f"item {k} estimate_usd", positive=True)})
    return validate({"version": d.get("version"), "max_workers": d.get("max_workers"), "serial": False,
                     "items": items, "order": d.get("order", [])})


def _start_ids(k, entries):
    """start_after entries: an id (legacy, approved goals) or {"id", "because"} with a non-empty reason (GO-023.8)."""
    out = []
    for e in entries if isinstance(entries, list) else [entries]:
        if isinstance(e, dict):
            if set(e) != {"id", "because"} or not isinstance(e["because"], str) or not e["because"].strip():
                raise ValueError(f"item {k}: a start_after entry is an id or {{id, because}} with a non-empty because")
            e = e["id"]
        out.append(e)
    return out


def validate(plan):
    items = plan["items"]
    ids = [i["id"] for i in items]
    if plan.get("version") != 1:
        raise ValueError("DEPS.json version must be 1")
    mw = plan["max_workers"]
    if mw is not None and (isinstance(mw, bool) or not isinstance(mw, int) or mw < 1):
        raise ValueError(f"max_workers must be a positive integer when present, not {mw!r}")
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
            _retest_close(run, s)
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


# ---- the host limit (GO-023): one record per host, shared by every run on it ----

def host_file(run, host):
    if not HOST.match(host or ""):
        raise ValueError(f"host name {host!r} can't name a host record")
    root = os.environ.get("GSTACK_GOAL_RUN_DIR")
    return (Path(root) if root else Path(run).resolve().parent) / "hosts" / f"{host}.json"


def host_update(path, fn=None):
    """Read (and with fn, change) a host record under its own lock. Taken inside a run's lock, never the other way."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            rec = json.loads(path.read_text()) if path.is_file() else {"limit": None, "events": [], "approvals_used": []}
            out = fn(rec) if fn else None
            if fn:
                write(path, rec)
            return rec if fn is None else out
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _ceiling(s):
    """The smaller of the goal's max_workers and the host's ceiling, where each applies; None is no ceiling. An open
    retest with no refusal runs to its approved ceiling instead of the host limit."""
    caps = [s["plan"]["max_workers"]]
    rt = s.get("retest")
    if rt and rt["open"] and not rt["refused"]:
        caps.append(rt["ceiling"])
    elif s.get("host_file"):
        caps.append(host_update(s["host_file"])["limit"])
    caps = [c for c in caps if c is not None]
    return min(caps) if caps else None


def _held(s, states=("sent", "running")):
    """Slots held by launches sent or accepted, a worker blocked while in flight included."""
    return sum(1 for v in s["items"].values()
               if v["status"] in states or (v["status"] == "blocked" and v.get("inflight") and v.get("sent")))


def _return_claim(run, s, iid, why):
    """An unlaunched claim goes back to pending; its reservation is released uncharged. Never a sent launch."""
    st = s["items"][iid]
    assert st["status"] == "dispatched"
    s["reserved"].pop(f"{iid}#{st['inflight']}", None)
    st.update(status="pending", inflight=None, why=why)
    _event(run, "claim_returned", id=iid, attempt=st["attempts"], why=why)


def _return_above(run, s, ceiling, why):
    """Every unlaunched claim whose slot is above the ceiling, slots counted after sent and running launches."""
    claims = sorted((v["claim"]["seq"], k) for k, v in s["items"].items() if v["status"] == "dispatched")
    held = _held(s)
    out = []
    for rank, (_, k) in enumerate(claims, 1):
        if ceiling is not None and held + rank > ceiling:
            _return_claim(run, s, k, why); out.append(k)
    return out


def _retest_close(run, s):
    """GO-023.5: a retest run that ends (nothing left to dispatch or in flight) with no refusal raises the host limit
    to the most workers that ran at once. A refusal already applied criterion 4."""
    rt = s.get("retest")
    if not rt or not rt["open"] or any(v["status"] not in ("merged", "blocked") or v.get("inflight") for v in s["items"].values()):
        return
    rt["open"] = False
    if rt["refused"]:
        return
    def go(rec):
        rec["limit"] = max(rec["limit"] or 0, rt["peak"]) or rec["limit"]
        rec["events"].append({"run": str(run), "kind": "retest", "running": rt["peak"], "approval": rt["approval"], "at": now()})
        return rec["limit"]
    _event(run, "retest_closed", peak=rt["peak"], limit=host_update(s["host_file"], go))


def init(run, goal_dir, base, budget, review_cap=None, host=None, retest=False, approval=None):
    plan = load_plan(goal_dir)
    marker = is_hard_cap(goal_dir, {})
    if marker:
        raise ValueError(f"a hard-cap goal ({marker}) never runs through the swarm")
    brief_cap = goal_review_cap(goal_dir)
    if brief_cap is not None and review_cap is not None and review_cap != brief_cap:
        raise ValueError(f"--review-cap {review_cap} differs from the brief's Max review rounds per item {brief_cap}")
    review_cap = brief_cap if brief_cap is not None else (review_cap or 3)
    run = Path(run)
    if _paths(run)[0].exists():
        raise ValueError(f"{run} already has a swarm; resume it with tick")
    host = host or socket.gethostname()
    hf = host_file(run, host)
    budget_usd = money(budget, "--budget", positive=True)
    rt = None
    if retest or approval:
        rt = _approve_retest(run, plan, hf, host, budget_usd, approval)
    run.mkdir(parents=True, exist_ok=True)
    s = {"plan": plan, "base": base, "integration_head": base, "budget": budget_usd, "spent": 0.0,
         "host": host, "host_file": str(hf), "retest": rt,
         "reserved": {}, "review_cap": review_cap,
         "items": {i["id"]: {"status": "pending", "attempts": 0, "review_rounds": 0, "evidence": None, "why": None}
                   for i in plan["items"]}}
    write(_paths(run)[0], s)
    _event(run, "init", base=base, budget=budget, serial=plan["serial"], items=[i["id"] for i in plan["items"]], host=host,
           retest=rt and {k: rt[k] for k in ("approval", "limit", "ceiling")})
    return s


def _approve_retest(run, plan, hf, host, budget_usd, approval):
    """GO-023.5: a retest needs Dorian's approving review on a pull request whose body names this host, its current
    limit, the retest ceiling and the dispatch budget. The host and limit must match; the run's ceiling
    (min(2 x limit, ready items)) and budget may be at or below the approved ones, never above. Each approval is
    consumed once, in the host record, when init accepts it, whatever ceiling and budget it ran at."""
    m = re.fullmatch(r"([\w.-]+/[\w.-]+)#(\d+)", approval or "")
    if not m:
        raise ValueError("--retest needs --approval <owner>/<repo>#<pr>; free text is not an approval")
    limit = host_update(hf)["limit"]
    if limit is None:
        raise ValueError(f"host {host} has no limit; there is nothing to retest")
    ready = sum(1 for i in plan["items"] if not i["start_after"])
    ceiling = min(2 * limit, ready)
    repo, pr = m.group(1), int(m.group(2))
    import goal_brief
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("verifying a retest approval needs GITHUB_TOKEN; run under `agent_token.py exec --`")
    fetch, seen = goal_brief.github(token), {}
    def get(path):                                   # goal_brief's own GitHub helper; keeps the body it verified
        out = fetch(path)
        if path == f"repos/{repo}/pulls/{pr}":
            seen["body"] = (out or {}).get("body") or ""
        return out
    required = [f"host `{host}`", f"current limit {limit} workers"]
    r = goal_brief.verify_review_approval(repo, pr, required, get=get)   # raises ValueError when it doesn't verify
    body = seen.get("body", "")
    ceilings = re.findall(r"retest ceiling (\d+) workers", body)
    budgets = re.findall(r"dispatch budget \$(\d+(?:\.\d+)?) USD", body)
    if len(ceilings) != 1 or len(budgets) != 1:
        raise ValueError(f"{approval}'s body must name one `retest ceiling <n> workers` and one `dispatch budget $<usd> USD`")
    if ceiling > int(ceilings[0]):
        raise ValueError(f"the retest ceiling {ceiling} is above the approved {ceilings[0]}")
    if budget_usd > float(budgets[0]) + 1e-9:
        raise ValueError(f"the dispatch budget ${budget_usd:.2f} is above the approved ${float(budgets[0]):.2f}")
    key = f"{approval}@{r['review_id']}"
    def go(rec):
        if key in rec["approvals_used"]:
            raise ValueError(f"approval {key} was already used")
        if rec["limit"] != limit:
            raise ValueError(f"host {host}'s limit changed to {rec['limit']} while the approval was checked")
        rec["approvals_used"].append(key)
    host_update(hf, go)
    return {"approval": key, "limit": limit, "ceiling": ceiling, "open": True, "refused": False, "peak": 0}


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


def tick(run, halted=False, spend_stop=False):
    """Claim every ready item while running and claimed slots stay under the ceiling (_ceiling). Never claims an item that is already claimed, so a restarted
    coordinator that ticks again dispatches nothing twice. Returns what to launch, what's running, and why the
    rest waits."""
    def go(s):
        out = {"dispatch": [], "running": [], "waiting": [], "stopped": None}
        for k, v in list(s["items"].items()):             # an item blocked by any path blocks its dependents now
            if v["status"] == "blocked":
                _block(run, s, k, v["why"] or "blocked")
        if halted or spend_stop:
            out["stopped"] = "HALT" if halted else "spend stop"
        # review F9: a worker blocked while it runs holds its slot until it reports
        running = [k for k, v in s["items"].items() if v["status"] in RUNNING or (v["status"] == "blocked" and v.get("inflight"))]
        ceiling = _ceiling(s)
        writes = {i["id"]: i["writes"] for i in s["plan"]["items"]}
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
            blockers = [d for d in i["start_after"] if s["items"][d]["status"] != "merged"]
            if blockers:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "start waits for " + ", ".join(blockers)}); continue
            if out["stopped"]:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": out["stopped"]}); continue
            if ceiling is not None and len(running) >= ceiling:
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "all workers busy"}); continue
            clash = [k for k in running if any(_glob_overlap(a, b) for a in i["writes"] for b in writes[k])]
            if clash:   # GO-023.2: against running items and items claimed earlier in this tick
                out["waiting"].append({"id": i["id"], "status": st["status"], "why": "writes overlap " + ", ".join(clash)}); continue
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
            st["inflight"] = st["attempts"]; st["sent"] = False
            s["seq"] = s.get("seq", 0) + 1
            key = f"{i['id']}#{st['attempts']}"
            s["reserved"][key] = i["estimate_usd"]       # reserved before the launch, released or settled after
            base = s["base"] if not i["start_after"] else s["integration_head"]
            claim = {"id": i["id"], "n": i["n"], "attempt": st["attempts"], "base": base,
                     "seq": s["seq"], "branch": f"swarm/{i['id']}-a{st['attempts']}", "writes": i["writes"], "contracts": i["contracts"],
                     "return": ["head SHA committed on the claim's branch, or a patch against the pinned base", "tests run and their result", "unresolved issues"],
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
    """The attempt must be the one in flight. A worker that was blocked while running may still report, so its
    reservation settles (review F5); its result is kept as evidence and the item stays blocked."""
    if st.get("inflight") != attempt or st["status"] not in RUNNING + ("blocked",):
        raise ValueError(f"{iid} attempt {attempt} isn't in flight (status {st['status']}, attempt {st['attempts']})")


def launch_check(run, iid, attempt, halted=False, spend_stop=False):
    """GO-023.3, run immediately before a launch: re-reads HALT, the spend stop and the host limit. 'launch', or
    'do not launch: <why>' with the claim returned to pending and its reservation released uncharged. A launch
    already sent is never touched here: it holds its slot and reservation until launched or launch-failed."""
    def go(s):
        _, st = _item(s, iid)
        if st["status"] != "dispatched" or st.get("inflight") != attempt:   # released or stale: answer, never raise
            return f"do not launch: {iid} attempt {attempt} is not a pending claim (status {st['status']})" + (", already sent" if st.get("sent") else "")
        _attempt(st, attempt, iid)
        if halted or spend_stop or s["spent"] > s["budget"] + 1e-9:
            why = "HALT" if halted else "spend stop" if spend_stop else "over budget"
            for k, v in s["items"].items():          # every claim not yet launched stops, not just this one
                if v["status"] == "dispatched":
                    _return_claim(run, s, k, why)
            return f"do not launch: {why}"
        ceiling = _ceiling(s)
        if iid in _return_above(run, s, ceiling, f"above the host limit {ceiling}"):
            return f"do not launch: its slot is above the limit {ceiling}"
        return "launch"
    return mutate(run, go)


def launch_sent(run, iid, attempt):
    """The coordinator is sending this launch now. From here it is in flight: HALT, a spend stop, a host refusal
    and a restart leave its slot and reservation alone until launched or launch-failed records the host's answer."""
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        if st["status"] != "dispatched":
            raise ValueError(f"{iid} is {st['status']}; only a checked claim is sent")
        st.update(status="sent", sent=True)
        _event(run, "launch_sent", id=iid, attempt=attempt)
    mutate(run, go)


def launched(run, iid, attempt):
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        if st["status"] == "blocked":
            if not st.get("sent"):
                raise ValueError(f"{iid} was blocked before its launch was recorded")
            st["started_at"] = now()                     # sent, then blocked: it runs, holds its slot and reports
            _event(run, "launched_after_block", id=iid, attempt=attempt); return
        st.update(status="running", sent=True, started_at=now())
        rt = s.get("retest")
        if rt and rt["open"]:
            rt["peak"] = max(rt["peak"], _held(s, ("running",)))
        _event(run, "launched", id=iid, attempt=attempt)
    mutate(run, go)


def launch_failed(run, iid, attempt, reason, host_refused=False):
    def go(s):
        _, st = _item(s, iid); _attempt(st, attempt, iid)
        s["reserved"].pop(f"{iid}#{attempt}", None)      # nothing ran, nothing is charged
        was = st["status"]
        st.update(inflight=None, sent=False)
        if was != "blocked":
            st["status"] = "pending"                     # out of the count before the host's running number is taken
        if host_refused and s.get("host_file"):
            running = _held(s)
            rt = s.get("retest")
            def lower(rec):
                old = rec["limit"]
                rec["events"].append({"run": str(run), "kind": "refused", "running": running,
                                      "approval": rt["approval"] if rt and rt["open"] else None, "at": now()})
                if old == 1:
                    return None                          # refusals can't repeat without end: this one counts
                rec["limit"] = max(1, running) if old is None else min(old, max(1, running))
                return rec["limit"]
            new = host_update(s["host_file"], lower)
            if rt and rt["open"]:
                rt["refused"] = True
            _event(run, "host_refused", id=iid, attempt=attempt, running=running, limit=new, reason=reason)
            if new is not None:                          # GO-023.4: not counted toward the item's block
                if was != "blocked":
                    st["why"] = f"host refused at {running} running; waits for a slot under {new}"
                _return_above(run, s, _ceiling(s), f"above the host limit {new} after a refusal")
                return
        st["launch_failures"] = st.get("launch_failures", 0) + 1   # review F3: its own count, not the attempt number
        if was != "blocked":
            if st["launch_failures"] >= MAX_LAUNCHES:
                _block(run, s, iid, f"launch failed {st['launch_failures']} times: {reason}")
            else:
                st["why"] = f"launch failed: {reason}"
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
    if st["status"] != "reviewed":
        reasons.append(f"status is {st['status']}, not reviewed")
    elif st["review"]["head"] != st["evidence"]["head"]:
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
        if st["status"] != "reviewed":
            raise ValueError(f"{iid} isn't reviewed")
        st.update(status="merged", merged=sha); s["integration_head"] = sha
        _event(run, "merged", id=iid, sha=sha)
    mutate(run, go)


def status(run):
    s = load(run)
    return {"host": s.get("host"), "ceiling": _ceiling(s), "retest": s.get("retest"), "budget": s["budget"], "spent": round(s["spent"], 4), "reserved": round(sum(s["reserved"].values()), 4),
            "over_budget": s["spent"] > s["budget"] + 1e-9, "estimated_settlements": s.get("estimated", 0),
            "integration_head": s["integration_head"],
            "items": {k: {x: v.get(x) for x in ("status", "attempts", "review_rounds", "why", "started_at", "finished_at")}
                      for k, v in s["items"].items()}}


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd"); p.add_argument("path"); p.add_argument("id", nargs="?")
    for f in ("--patch", "--goal", "--base", "--budget", "--halt", "--reason", "--head", "--repo", "--tests", "--cost",
              "--unresolved", "--outcome", "--review-id", "--target", "--sha"):
        p.add_argument(f)
    p.add_argument("--attempt", type=int); p.add_argument("--review-cap", type=int)
    p.add_argument("--spend-stop", action="store_true"); p.add_argument("--host-refused", action="store_true")
    p.add_argument("--host"); p.add_argument("--retest", action="store_true"); p.add_argument("--approval")
    a = p.parse_args(argv)
    try:
        if a.cmd == "check":
            plan = load_plan(a.path); print(json.dumps({"serial": plan["serial"], "max_workers": plan["max_workers"],
                                                        "items": [i["id"] for i in plan["items"]]})); return 0
        if a.cmd == "init":
            if a.retest and not a.approval:
                raise ValueError("--retest needs --approval <owner>/<repo>#<pr>")
            if a.approval and not a.retest:
                raise ValueError("--approval is only for --retest")
            init(a.path, a.goal, a.base, a.budget, a.review_cap, a.host, a.retest, a.approval); print("ok"); return 0
        halted = bool(a.halt) and Path(a.halt).exists()
        if a.cmd == "tick":
            print(json.dumps(tick(a.path, halted, a.spend_stop), indent=1)); return 0
        if a.cmd == "launch-check":
            print(launch_check(a.path, a.id, a.attempt, halted, a.spend_stop)); return 0
        if a.cmd == "launch-sent":
            launch_sent(a.path, a.id, a.attempt); return 0
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
