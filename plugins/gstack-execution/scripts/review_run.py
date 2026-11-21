#!/usr/bin/env python3
"""review_run.py: one ledger that holds a multi-lane review's limits, a manifest that fixes its jobs, and a
runner that starts, times and stops its lanes (GR-001).

Commands
  init     --run ID --ledger FILE [--max-fanouts|rechecks|codex-calls|disputes|dollars|deadline-minutes N, lower only]
           [--council-gate-ruling REF]
  resume   --run ID --ledger FILE [--draft-sha SHA] [--council-gate-ruling REF]   same counters, no fresh allowance
  manifest --run ID --ledger FILE --out FILE --draft F --evidence F.. --prompts F.. --lessons F --key F --width N
  reserve  --run ID --ledger FILE --phase fanout|recheck|council --lane L [--tool codex|claude] ...
           records one reservation and prints it (the path a Council dispatch takes; launches nothing)
  dispatch --run ID --ledger FILE --out-root DIR --lane L --tool codex|claude --prompt-file F ...
           reserves, then starts the lane as a process group under timeout and records its findings or failure
  disposition --run ID --ledger FILE --decision TEXT
  report   --run ID --ledger FILE [--ps FILE]
Exit codes: 0 ok, 1 refused (the spent counter is named), 3 a lane failed.

ponytail: one JSON ledger file under flock, no daemon; a lane is one subprocess, concurrency is the caller
starting several `dispatch` processes. Lanes write one findings file, never anything else.

Write boundary (GR-001.5), as far as this runner enforces it: a lane starts with its own directory as cwd and
TMPDIR, under `timeout`, in its own process group; a Codex lane is `--sandbox read-only --ephemeral`; a claude lane
has Bash, Edit, MultiEdit, Write and NotebookEdit denied and gets its prompt on stdin, and the runner (not the
worker) writes its findings file from stdout. There is no operating-system confinement of a worker that ignores its
own tool limits, and HOME and CODEX_HOME stay in the environment because the CLIs keep their sign-in there.
Dispatch is bound to the run's manifest: it refuses (counter manifest_missing, not_the_same_manifest or
prompt_not_in_manifest) when the manifest, any file it recorded, or the prompt file differs from what was hashed.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import peer_review  # noqa: E402  (codex_argv: the one Codex command builder)

DEFAULTS = {"fanouts": 1, "rechecks": 2, "codex_calls": 10, "disputes": 2, "dollars": 1.0, "deadline_minutes": 90.0}
CEILING = 900  # seconds, per call (Codex and claude lanes)
CLASSES = ("false_premise", "wording_defect", "behavior_gap", "unresolved_decision")
FIELDS = ("finding_id", "lane", "claim", "cited_clause", "class", "evidence", "smallest_fix")
KEEP_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "USER", "SHELL", "CODEX_HOME")  # names no *_API_KEY; HOME and CODEX_HOME carry the CLIs' own sign-in, not a key
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")      # a run id or lane name is one path component
CITE = re.compile(r"^(?:[^\s:]+:\d+|[0-9a-f]{64})$")        # file:line or a sha256
CLAUDE_DENY = "Bash,Edit,MultiEdit,Write,NotebookEdit"   # the claude lane reads; the runner writes its one findings file
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["findings"], "properties": {"findings": {
    "type": "array", "items": {"type": "object", "additionalProperties": False, "required": list(FIELDS), "properties": {
        "finding_id": {"type": "string"}, "lane": {"type": "string"}, "claim": {"type": "string"},
        "cited_clause": {"type": "string"}, "class": {"type": "string", "enum": list(CLASSES)},
        "evidence": {"type": "array", "items": {"type": "string"}}, "smallest_fix": {"type": "string"}}}}}}

wall = time.time          # tests replace these two clocks
mono = time.monotonic


class Refused(Exception):
    def __init__(self, counter):
        super().__init__(counter)
        self.counter = counter


# ---------- ledger ----------

@contextlib.contextmanager
def locked(ledger):
    ledger = Path(ledger)
    with open(str(ledger) + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            db = json.loads(ledger.read_text()) if ledger.is_file() else {"runs": {}}
            yield db
            tmp = ledger.with_name(ledger.name + ".tmp")
            tmp.write_text(json.dumps(db, indent=1, sort_keys=True))
            os.replace(tmp, ledger)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _run(db, run):
    if run not in db["runs"]:
        raise ValueError(f"no run {run} in this ledger")
    return db["runs"][run]


def _gate(r, ref):
    if ref:
        r["council_gate"], r["council_gate_ruling"] = "open", ref


def _num(v, label):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise ValueError(f"{label} {v!r} must be a finite number, zero or more")
    return v


def init(ledger, run, council_gate_ruling=None, **flags):
    limits = dict(DEFAULTS)
    for k, v in flags.items():
        if v is None:
            continue
        _num(v, f"--max-{k.replace('_', '-')}")
        if v > DEFAULTS[k]:
            raise ValueError(f"--max-{k.replace('_', '-')} {v} raises the limit {DEFAULTS[k]}; a flag may only lower it")
        limits[k] = v
    with locked(ledger) as db:
        if run in db["runs"]:
            raise ValueError(f"{run} is already in this ledger; init refuses an id the file holds, use resume")
        now = wall()
        r = db["runs"][run] = {"run_id": run, "limits": limits, "init_at": now, "deadline_at": now + limits["deadline_minutes"] * 60,
                               "used": {"codex_calls": 0, "disputes": 0, "dollars": 0.0}, "rounds": {"fanout": [], "recheck": []},
                               "council_gate": "closed", "status": "running", "lanes": {}, "events": []}
        _gate(r, council_gate_ruling)
        return r


def resume(ledger, run, draft_sha=None, council_gate_ruling=None):
    """Reads the same counters: a revised draft, a new draft hash or a restart gets no fresh allowance."""
    with locked(ledger) as db:
        r = _run(db, run)
        if draft_sha:
            r["events"].append({"event": "resume", "draft_sha256": draft_sha, "mono": mono()})
        _gate(r, council_gate_ruling)
        return json.loads(json.dumps(r))


def counters(r):
    u, lim = r["used"], r["limits"]
    return {"fanouts": [len(r["rounds"]["fanout"]), lim["fanouts"]], "rechecks": [len(r["rounds"]["recheck"]), lim["rechecks"]],
            "codex_calls": [u["codex_calls"], lim["codex_calls"]], "disputes": [u["disputes"], lim["disputes"]],
            "dollars": [round(u["dollars"], 6), lim["dollars"]], "deadline_left_s": round(r["deadline_at"] - wall(), 3)}


def _bound(r, prompt_file):
    """GR-001.4: the jobs run are the jobs the manifest fixed. The name of what differs, or None."""
    m = r.get("manifest")
    if not m:
        return "manifest_missing"
    try:
        if sha(m["path"]) != m["sha256"] or _core(m["files"])[1] != m["core_sha256"]:
            return "not_the_same_manifest"
        if sha(prompt_file) not in _core(m["files"])[0]["prompts_sha256"]:
            return "prompt_not_in_manifest"
    except OSError:
        return "not_the_same_manifest"
    return None


def _spent(r, phase, tool, rnd, usd, key=None, bind=None):
    """The name of the counter this reservation would exceed, or None."""
    u, lim = r["used"], r["limits"]
    if r["status"] == "failed":
        return "run_failed"
    if r["deadline_at"] - wall() <= 0:
        return "deadline"
    if key in r.get("jobs", ()):
        return "duplicate_attempt"
    if bind:
        why = _bound(r, bind)
        if why:
            return why
    if phase == "council":
        if r["council_gate"] != "open":
            return "council_gate"
        if u["disputes"] >= lim["disputes"]:
            return "disputes"
    elif rnd not in r["rounds"][phase] and len(r["rounds"][phase]) >= lim[phase + "s"]:
        return phase + "s"
    if tool == "codex" and u["codex_calls"] >= lim["codex_calls"]:
        return "codex_calls"
    if u["dollars"] >= lim["dollars"] - 1e-9 or u["dollars"] + usd > lim["dollars"] + 1e-9:
        return "dollars"
    return None


def reserve(ledger, run, phase, lane, tool="codex", rnd="1", usd=0.0, revision=1, attempt=1, bind=None):
    """Record the reservation before anything starts. A refusal is a ledger event and raises Refused(counter).
    bind: the prompt file a launch will read; given, it must be one the run's manifest fixed."""
    _num(usd, "usd")
    key = f"{lane}/r{revision}/a{attempt}"
    err, out = None, None
    with locked(ledger) as db:
        r = _run(db, run)
        err = _spent(r, phase, tool, rnd, usd, key, bind)
        if err:
            r["events"].append({"event": "refused", "counter": err, "job": key, "phase": phase, "mono": mono()})
        else:
            if phase != "council" and rnd not in r["rounds"][phase]:
                r["rounds"][phase].append(rnd)
            r["used"]["codex_calls"] += tool == "codex"
            r["used"]["disputes"] += phase == "council"
            r["used"]["dollars"] += usd
            r.setdefault("jobs", []).append(key)
            t = mono()
            r["events"].append({"event": "admit", "job": key, "phase": phase, "tool": tool, "round": rnd, "usd": usd, "mono": t})
            left = r["deadline_at"] - wall()
            out = {"job": key, "admitted": t, "timeout": min(CEILING, left), "deadline_bound": left < CEILING}
    if err:
        raise Refused(err)
    return out


# ---------- manifest ----------

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _core(files):
    """The manifest's hashed fields, computed from the files as they are now, and the sha256 of them."""
    core = {"draft_sha256": sha(files["draft"]), "evidence_sha256": sorted(sha(f) for f in files["evidence"]),
            "prompts_sha256": sorted(sha(f) for f in files["prompts"]), "lesson_state_sha256": sha(files["lessons"]),
            "scoring_key_sha256": sha(files["key"])}
    return core, hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()


def manifest(ledger, run, out, draft, evidence, prompts, lessons, key, width):
    out = Path(out).resolve()
    files = {"draft": str(Path(draft).resolve()), "evidence": [str(Path(f).resolve()) for f in evidence],
             "prompts": [str(Path(f).resolve()) for f in prompts], "lessons": str(Path(lessons).resolve()), "key": str(Path(key).resolve())}
    core, core_sha = _core(files)
    with locked(ledger) as db:
        r = _run(db, run)
        if out.exists() or r.get("manifest"):
            raise ValueError("a manifest is written once; this run or this file already has one")
        for other, o in db["runs"].items():
            if other != run and o.get("manifest") and o["manifest"]["core_sha256"] != core_sha:
                raise ValueError(f"not the same manifest as run {other}: only width may differ")
        out.write_text(json.dumps({**core, "width": width}, indent=1, sort_keys=True))
        r["manifest"] = {"sha256": sha(out), "core_sha256": core_sha, "width": width, "path": str(out), "files": files}
        return r["manifest"]


# ---------- lanes ----------

def lane_env(tmpdir=None):
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ and not k.endswith("_API_KEY")}
    if tmpdir:
        env["TMPDIR"] = str(tmpdir)      # scratch writes land in the lane's own directory
    return env


def validate_findings(path):
    """None when the file is a valid findings file, else the reason. Nothing is repaired or partly read."""
    try:
        d = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return f"unparseable: {e}"
    if not isinstance(d, dict) or not isinstance(d.get("findings"), list):
        return "no findings list"
    for i, f in enumerate(d["findings"]):
        if not isinstance(f, dict) or any(k not in f for k in FIELDS):
            return f"finding {i} is missing a field"
        if set(f) - set(FIELDS):
            return f"finding {i} has a field outside the schema"
        for k in ("finding_id", "lane", "claim", "smallest_fix"):
            if not isinstance(f[k], str) or not f[k].strip():
                return f"finding {i} {k} is not a non-empty string"
        if f["class"] not in CLASSES:
            return f"finding {i} has class {f['class']!r}"
        if not isinstance(f["cited_clause"], str) or not CITE.match(f["cited_clause"]):
            return f"finding {i} cited_clause is not file:line or a sha256"
        if not isinstance(f["evidence"], list) or any(not isinstance(e, str) or not CITE.match(e) for e in f["evidence"]):
            return f"finding {i} evidence is not a list of file:line or sha256 strings"
    return None


def _alive(pgid):
    """True: the group is still in the process table. False: seen absent. None: the table could not be read."""
    for _ in range(20):
        ps = subprocess.run(["ps", "-A", "-o", "pgid="], capture_output=True, text=True)
        if ps.returncode != 0 or not ps.stdout.strip():
            return None
        if str(pgid) not in ps.stdout.split():
            return False
        time.sleep(0.1)
    return True


def _time_left(ledger, run):
    with locked(ledger) as db:
        return _run(db, run)["deadline_at"] - wall()


def _event(ledger, run, **ev):
    with locked(ledger) as db:
        _run(db, run)["events"].append({**ev, "mono": mono()})


def _finish(ledger, run, key, admitted, status, reason, out):
    _event(ledger, run, event="finish", job=key, admitted=admitted, lane_status=status, reason=reason)
    with locked(ledger) as db:
        _run(db, run)["lanes"][key] = {"status": status, "reason": reason, "out": str(out)}
    return status, reason


def dispatch(ledger, run, out_root, lane, tool, prompt_file, phase="fanout", rnd="1", usd=0.0, revision=1, attempt=1):
    """Reserve, then start the lane. Returns (lane status, reason)."""
    for label, v in (("run", run), ("lane", lane)):
        if not SAFE.match(str(v)):
            raise ValueError(f"{label} {v!r} must be one path component of letters, digits, . _ -")
    if not all(isinstance(n, int) and not isinstance(n, bool) and n >= 1 for n in (revision, attempt)):
        raise ValueError("revision and attempt must be whole numbers, 1 or more")
    wrap = shutil.which("timeout") or shutil.which("gtimeout")
    if not wrap:
        raise ValueError("no timeout executable on PATH; a lane is never started without one (GR-001.5)")
    prompt_file = Path(prompt_file).resolve()
    resv = reserve(ledger, run, phase, lane, tool, rnd, usd, revision, attempt, bind=prompt_file)
    key = resv["job"]
    root = Path(out_root).resolve()
    out = root / run / lane / f"rev{revision}" / f"attempt{attempt}"
    try:
        out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return _finish(ledger, run, key, resv["admitted"], "failed", "output directory already exists", out)
    if root not in out.resolve().parents:
        return _finish(ledger, run, key, resv["admitted"], "failed", "output directory escapes the output root", out)
    (out / "tmp").mkdir()
    findings, prompt = out / "findings.json", prompt_file.read_text()
    stdin = subprocess.DEVNULL
    if tool == "codex":
        schema = out / "schema.json"
        schema.write_text(json.dumps(SCHEMA))
        cmd = peer_review.codex_argv(out, schema, findings, prompt, ephemeral=True)
    else:
        cmd = ["claude", "-p", "--disallowedTools", CLAUDE_DENY]    # the prompt goes in on stdin
        stdin = open(prompt_file)
    left = _time_left(ledger, run)                                    # the deadline again, just before launch
    deadline_at = wall() + left
    secs = min(CEILING, left)
    if secs <= 0:
        return _finish(ledger, run, key, resv["admitted"], "failed", "deadline_before_launch", out)
    _event(ledger, run, event="start", job=key, admitted=resv["admitted"])
    status, reason, expired = "ok", None, False
    with open(out / "stdout.txt", "w") as so, open(out / "stderr.txt", "w") as se:
        try:
            p = subprocess.Popen([wrap, "-s", "KILL", f"{secs:.2f}"] + cmd, cwd=out, env=lane_env(out / "tmp"), stdin=stdin,
                                 stdout=so, stderr=se, start_new_session=True)
        except OSError as e:
            p, status, reason = None, "failed", f"could not start: {e}"
        if p:
            try:
                rc = p.wait(timeout=secs + 2)
            except subprocess.TimeoutExpired:
                rc, expired = 124, True
            expired = expired or rc in (124, 137, -9)
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(p.pid, signal.SIGKILL)
            with contextlib.suppress(Exception):
                p.wait(timeout=5)
            gone = _alive(p.pid)
            killed = ("deadline_killed" if wall() >= deadline_at - 1.0 else "timeout_killed") if expired else None
            if gone is not False:
                status, reason = "failed", "exit_unconfirmed"
                _event(ledger, run, event="exit_unconfirmed", job=key, pgid=p.pid, confirmed_gone=False)
                with locked(ledger) as db:
                    _run(db, run)["status"] = "failed"
            elif killed:
                status, reason = "failed", killed
                _event(ledger, run, event=killed, job=key, pgid=p.pid, confirmed_gone=True)
            elif rc != 0:
                status, reason = "failed", f"exit {rc}"
    if stdin is not subprocess.DEVNULL:
        stdin.close()
    if tool != "codex" and status == "ok":
        findings.write_text((out / "stdout.txt").read_text())
    if status == "ok":
        bad = validate_findings(findings) if findings.exists() else "no findings file"
        status, reason = ("failed", bad) if bad else ("ok", None)
    return _finish(ledger, run, key, resv["admitted"], status, reason, out)


# ---------- report ----------

def compute_report(events):
    """Peak, review wait and draft-to-decision time, from the start/finish/admit/disposition events alone."""
    starts = {e["job"]: e for e in events if e["event"] == "start"}
    ends = {e["job"]: e for e in events if e["event"] == "finish"}
    spans = [(starts[j]["mono"], ends[j]["mono"]) for j in starts if j in ends]
    marks = sorted([(a, 1) for a, _ in spans] + [(b, 0) for _, b in spans])  # an end sorts before a start at a tie
    peak = cur = 0
    for _, is_start in marks:
        cur += 1 if is_start else -1
        peak = max(peak, cur)
    wait = sum(starts[j]["mono"] - starts[j]["admitted"] for j in starts)
    admits = [e["mono"] for e in events if e["event"] == "admit"]
    done = [e["mono"] for e in events if e["event"] == "disposition"]
    d2d = round(max(done) - min(admits), 3) if admits and done else None
    return {"peak": peak, "review_wait_s": round(wait, 3), "draft_to_decision_s": d2d}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def A(flag, **kw):
        return ((flag,), kw)

    def add(name, *args):
        sp = sub.add_parser(name)
        sp.add_argument("--run", required=True)
        sp.add_argument("--ledger", required=True)
        for a in args:
            sp.add_argument(*a[0], **a[1])

    lim = [A(f"--max-{k.replace('_', '-')}", dest=k, type=float if k in ("dollars", "deadline_minutes") else int) for k in DEFAULTS]
    add("init", A("--council-gate-ruling"), *lim)
    add("resume", A("--draft-sha"), A("--council-gate-ruling"))
    add("manifest", A("--out", required=True), A("--draft", required=True), A("--evidence", nargs="+", required=True),
        A("--prompts", nargs="+", required=True), A("--lessons", required=True), A("--key", required=True), A("--width", type=int, required=True))
    common = [A("--phase", choices=["fanout", "recheck", "council"], default="fanout"), A("--lane", required=True), A("--round", dest="rnd", default="1"),
              A("--usd", type=float, default=0.0), A("--revision", type=int, default=1), A("--attempt", type=int, default=1)]
    add("reserve", A("--tool", choices=["codex", "claude"], default="codex"), *common)
    add("dispatch", A("--tool", choices=["codex", "claude"], required=True), A("--out-root", required=True), A("--prompt-file", required=True), *common)
    add("disposition", A("--decision", required=True))
    add("report", A("--ps"))
    a = ap.parse_args(argv)
    try:
        if a.cmd == "init":
            print(json.dumps(counters(init(a.ledger, a.run, a.council_gate_ruling, **{k: getattr(a, k) for k in DEFAULTS}))))
        elif a.cmd == "resume":
            print(json.dumps(counters(resume(a.ledger, a.run, a.draft_sha, a.council_gate_ruling))))
        elif a.cmd == "manifest":
            print(json.dumps(manifest(a.ledger, a.run, a.out, a.draft, a.evidence, a.prompts, a.lessons, a.key, a.width)))
        elif a.cmd == "reserve":
            print(json.dumps(reserve(a.ledger, a.run, a.phase, a.lane, a.tool, a.rnd, a.usd, a.revision, a.attempt)))
        elif a.cmd == "dispatch":
            status, reason = dispatch(a.ledger, a.run, a.out_root, a.lane, a.tool, a.prompt_file, a.phase, a.rnd, a.usd, a.revision, a.attempt)
            print(json.dumps({"lane": a.lane, "status": status, "reason": reason}))
            return 0 if status == "ok" else 3
        elif a.cmd == "disposition":
            _event(a.ledger, a.run, event="disposition", decision=a.decision)
            with locked(a.ledger) as db:
                r = _run(db, a.run)
                r["status"] = "failed" if r["status"] == "failed" else "complete"
        elif a.cmd == "report":
            with locked(a.ledger) as db:
                events = list(_run(db, a.run)["events"])
            print(json.dumps(compute_report(events)))
            if a.ps:
                print("ps samples (corroboration only):", Path(a.ps).read_text().strip().replace("\n", "; "))
                print("sampling can miss a short peak")
    except Refused as e:
        print(json.dumps({"refused": e.counter}))
        return 1
    except ValueError as e:
        print(json.dumps({"refused": str(e)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
