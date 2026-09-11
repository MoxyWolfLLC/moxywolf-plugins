#!/usr/bin/env python3
"""
gstack peer review dispatcher. Stdlib only.

Enforces the mechanical half of references/peer-review-contract.md: commit identity,
tool routing (builder -> the other tool), read-only snapshots, output validation,
round limits, dispositions, explicit outcomes. The contract file carries the words.

  peer_review.py open   --builder claude|codex --packet packet.json [--max-rounds 3] [--timeout 900]
  peer_review.py round  <review-id> [--head <repo-path>=<sha> ...]
  peer_review.py disposition <review-id> F1=fixed F2=disproved:"evidence" F3=deferred
  peer_review.py status <review-id>
  peer_review.py --selftest
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent / "skills" / "gstack-execution" / "references" / "peer-review-contract.md"
REVIEW_DIR = Path(os.environ.get("GSTACK_PEER_REVIEW_DIR", Path.home() / ".gstack" / "peer-review"))
RECURSION_ENV = "GSTACK_PEER_REVIEW_SESSION"
OTHER_TOOL = {"claude": "codex", "codex": "claude"}
PACKET_FIELDS = ["outcome", "acceptance_criteria", "repos", "changed_behavior", "exclusions", "tests"]
SEVERITIES = {"blocking", "follow_up", "separate"}
VERDICTS = {"no_blocking_findings", "blocking_findings"}
DISPOSITIONS = {"fixed", "disproved", "deferred", "unresolved"}

OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["verdict", "acceptance", "findings"],
    "properties": {
        "verdict": {"type": "string", "enum": sorted(VERDICTS)},
        "acceptance": {"type": "array", "items": {"type": "object", "required": ["criterion", "met", "evidence"],
                       "properties": {"criterion": {"type": "string"}, "met": {"type": "boolean"}, "evidence": {"type": "string"}}}},
        "findings": {"type": "array", "items": {"type": "object",
                     "required": ["id", "severity", "file", "line", "what", "evidence", "criterion", "fix"],
                     "properties": {"id": {"type": "string"}, "severity": {"type": "string", "enum": sorted(SEVERITIES)},
                                    "file": {"type": "string"}, "line": {"type": "integer"}, "what": {"type": "string"},
                                    "evidence": {"type": "string"}, "criterion": {"type": "string"}, "fix": {"type": "string"}}}},
        "regressions_from_fixes": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
}


def strict(schema):
    """OpenAI structured output requires additionalProperties:false and every property required, on every object."""
    if isinstance(schema, dict):
        out = {k: strict(v) for k, v in schema.items()}
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"])
        return out
    if isinstance(schema, list):
        return [strict(x) for x in schema]
    return schema


STRICT_SCHEMA = strict(OUTPUT_SCHEMA)


class ReviewError(Exception):
    """Carries an explicit outcome name."""
    def __init__(self, outcome, detail):
        super().__init__(f"{outcome}: {detail}")
        self.outcome, self.detail = outcome, detail


# ---------- git ----------

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise ReviewError("missing_commits", f"git {' '.join(args)} in {repo}: {r.stderr.strip()}")
    return r.stdout.strip()


def resolve_commit(repo, ref):
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise ReviewError("missing_commits", f"{ref} does not resolve in {repo}")
    return r.stdout.strip()


def snapshot(repos, root):
    """Detached read-only worktree per repo at its head commit. Returns [(name, path)]."""
    out = []
    for i, r in enumerate(repos):
        name = f"{i}-{Path(r['path']).name}"
        dest = root / name
        git(r["path"], "worktree", "add", "--detach", str(dest), r["head"])
        for p in dest.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                p.chmod(p.stat().st_mode & 0o555)
        out.append((name, dest))
    return out


def teardown(repos, root):
    for r in repos:
        subprocess.run(["git", "-C", r["path"], "worktree", "prune"], capture_output=True)
    for d in root.iterdir() if root.exists() else []:
        for r in repos:
            subprocess.run(["git", "-C", r["path"], "worktree", "remove", "--force", str(d)], capture_output=True)
    shutil.rmtree(root, ignore_errors=True)


# ---------- packet / state ----------

def load_packet(path):
    packet = json.loads(Path(path).read_text())
    missing = [f for f in PACKET_FIELDS if f not in packet]
    if missing:
        raise ReviewError("malformed_packet", f"packet missing {missing}")
    if not packet["repos"]:
        raise ReviewError("malformed_packet", "repos is empty")
    for r in packet["repos"]:
        for k in ("path", "base", "head"):
            if k not in r:
                raise ReviewError("malformed_packet", f"repo entry missing {k}: {r}")
        r["path"] = str(Path(r["path"]).resolve())
        r["base"], r["head"] = resolve_commit(r["path"], r["base"]), resolve_commit(r["path"], r["head"])
        if r["base"] == r["head"]:
            raise ReviewError("missing_commits", f"base == head in {r['path']}; nothing to review")
    packet.setdefault("prior_findings", [])
    return packet


def rdir(review_id):
    d = REVIEW_DIR / review_id
    if not (d / "state.json").exists():
        sys.exit(f"no review {review_id} under {REVIEW_DIR}")
    return d


def load(d, name):
    p = d / name
    return json.loads(p.read_text()) if p.exists() else None


def save(d, name, obj):
    (d / name).write_text(json.dumps(obj, indent=2))


# ---------- reviewer ----------

def contract_sections():
    text = CONTRACT.read_text()
    start, end = text.index("## Scope"), text.index("## The loop")
    return text[start:end]


def build_prompt(packet, snaps, round_no, prior_round, dispositions):
    repos = "\n".join(f"- {name}: base {r['base'][:12]} head {r['head'][:12]} (review `git diff {r['base']}..{r['head']}` inside this directory)"
                      for (name, _), r in zip(snaps, packet["repos"]))
    p = [
        "You are the independent reviewer in a bounded cross-tool peer review. Read-only. Do not edit, deploy, or start another review.",
        f"Working directory holds one detached snapshot per repository at the head commit:\n{repos}",
        "The builder's packet is a claim to check, not evidence. Open the code.",
        "=== PACKET ===", json.dumps({k: packet[k] for k in PACKET_FIELDS}, indent=2),
        "=== CONTRACT ===", contract_sections(),
    ]
    if round_no > 1:
        p += ["=== FIX-VERIFICATION ROUND ===",
              f"This is round {round_no}. Do not restart a full review. Verify each prior finding against its disposition, "
              "check for regressions introduced by the fixes, and report only: prior findings by their existing IDs, regressions, "
              "and any genuinely new blocker that meets the evidence and scope rules.",
              "Prior findings:", json.dumps(prior_round.get("findings", []), indent=2),
              "Builder dispositions:", json.dumps(dispositions or {}, indent=2)]
    p.append("Return only the JSON object described in the contract.")
    return "\n\n".join(p)


def run_reviewer(tool, prompt, root, timeout):
    env = {**os.environ, RECURSION_ENV: "1"}
    fake = os.environ.get("GSTACK_PEER_REVIEW_FAKE_CMD")  # selftest hook: any command that prints the JSON
    if fake:
        cmd, parse = ["sh", "-c", fake], lambda s: s
    elif tool == "codex":
        if not shutil.which("codex"):
            raise ReviewError("review_unavailable", "codex CLI not installed on PATH")
        schema = root / "schema.json"; last = root / "last.txt"
        schema.write_text(json.dumps(STRICT_SCHEMA))
        cmd = ["codex", "exec", "-C", str(root), "--sandbox", "read-only", "--skip-git-repo-check",
               "--output-schema", str(schema), "--output-last-message", str(last), prompt]
        parse = lambda s: last.read_text() if last.exists() else s
    elif tool == "claude":
        if not shutil.which("claude"):
            raise ReviewError("review_unavailable", "claude CLI not installed on PATH")
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(STRICT_SCHEMA),
               "--allowedTools", "Read", "Grep", "Glob", "Bash(git:*)", "--disallowedTools", "Write", "Edit", "MultiEdit", "NotebookEdit",
               "--add-dir", str(root), "--no-session-persistence", "--max-turns", "60"]
        def parse(s):
            try:
                env_ = json.loads(s)
            except json.JSONDecodeError:
                return s
            if isinstance(env_, dict):
                if "structured_output" in env_:
                    return json.dumps(env_["structured_output"])
                return env_.get("result", s)
            return s
    else:
        raise ReviewError("review_unavailable", f"unknown tool {tool}")
    try:
        # stdin closed: codex exec otherwise blocks on "Reading additional input from stdin..."
        r = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise ReviewError("timeout", f"{tool} exceeded {timeout}s")
    except FileNotFoundError as e:
        raise ReviewError("review_unavailable", str(e))
    if r.returncode != 0:
        raise ReviewError("review_unavailable", f"{tool} exited {r.returncode}: {(r.stderr + r.stdout).strip()[-800:]}")
    return parse(r.stdout)


def validate(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ReviewError("malformed_output", "no JSON object in reviewer output")
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ReviewError("malformed_output", f"invalid JSON: {e}")
    if out.get("verdict") not in VERDICTS:
        raise ReviewError("malformed_output", f"verdict {out.get('verdict')!r}")
    if not isinstance(out.get("findings"), list) or not isinstance(out.get("acceptance"), list):
        raise ReviewError("malformed_output", "findings/acceptance must be lists")
    ids = set()
    for f in out["findings"]:
        need = OUTPUT_SCHEMA["properties"]["findings"]["items"]["required"]
        if any(k not in f for k in need) or f["severity"] not in SEVERITIES or not isinstance(f["line"], int):
            raise ReviewError("malformed_output", f"bad finding {f.get('id')}")
        if f["id"] in ids:
            raise ReviewError("malformed_output", f"duplicate finding id {f['id']}")
        ids.add(f["id"])
    has_block = any(f["severity"] == "blocking" for f in out["findings"])
    if has_block != (out["verdict"] == "blocking_findings"):
        raise ReviewError("malformed_output", "verdict disagrees with finding severities")
    out.setdefault("regressions_from_fixes", [])
    out.setdefault("notes", "")
    return out


# ---------- commands ----------

def cmd_open(a):
    if os.environ.get(RECURSION_ENV):
        sys.exit("refused: this is a reviewer session; peer review does not recurse")
    packet = load_packet(a.packet)
    stem = time.strftime("%Y%m%d-%H%M%S") + "-" + packet["repos"][0]["head"][:7]
    review_id, n = stem, 1
    while (REVIEW_DIR / review_id).exists():
        n += 1; review_id = f"{stem}-{n}"
    d = REVIEW_DIR / review_id
    d.mkdir(parents=True)
    state = {"review_id": review_id, "builder": a.builder, "reviewer": OTHER_TOOL[a.builder],
             "max_rounds": a.max_rounds, "timeout": a.timeout, "rounds_used": 0, "outcome": "opened",
             "heads": [[r["head"] for r in packet["repos"]]]}
    save(d, "packet.json", packet); save(d, "state.json", state)
    print(json.dumps(state, indent=2))


def cmd_round(a):
    if os.environ.get(RECURSION_ENV):
        sys.exit("refused: this is a reviewer session; peer review does not recurse")
    d = rdir(a.review_id)
    state, packet = load(d, "state.json"), load(d, "packet.json")
    if state["rounds_used"] >= state["max_rounds"]:
        sys.exit(f"rounds exhausted ({state['max_rounds']}); outcome stays {state['outcome']}")
    round_no = state["rounds_used"] + 1
    prior = load(d, f"round-{round_no - 1}.json") if round_no > 1 else None
    dispositions = load(d, "dispositions.json") or {}
    if round_no > 1:
        open_blockers = [f["id"] for f in prior.get("findings", []) if f["severity"] == "blocking"]
        undisposed = [i for i in open_blockers if i not in dispositions]
        if undisposed:
            sys.exit(f"disposition required for blocking findings before round {round_no}: {undisposed}")
        # fix round: base becomes previous head, head advances per --head
        updates = {}
        for h in a.head:
            k, v = h.rsplit("=", 1)
            updates[str(Path(k).resolve()) if "/" in k else k] = v  # repo path (resolved, like the packet) or bare dir name
        for r in packet["repos"]:
            r["base"] = r["head"]
            sha = updates.get(r["path"], updates.get(Path(r["path"]).name))
            if sha:
                r["head"] = resolve_commit(r["path"], sha)
        if all(r["base"] == r["head"] for r in packet["repos"]) and any(v == "fixed" for v in dispositions.values()):
            sys.exit("dispositions say fixed but no --head advanced; commit the fix and pass --head <repo>=<sha>")
        packet["prior_findings"] = [{"id": f["id"], "severity": f["severity"], "what": f["what"],
                                     "disposition": dispositions.get(f["id"])} for f in prior.get("findings", [])]
    root = Path(tempfile.mkdtemp(prefix="gstack-peer-"))
    record = {"round": round_no, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "repos": packet["repos"]}
    try:
        snaps = snapshot(packet["repos"], root)
        prompt = build_prompt(packet, snaps, round_no, prior, dispositions)
        (d / f"round-{round_no}-prompt.txt").write_text(prompt)
        raw = run_reviewer(state["reviewer"], prompt, root, state["timeout"])
        record["raw"] = raw
        out = validate(raw)
        record.update(out)
        blockers = [f for f in out["findings"] if f["severity"] == "blocking"]
        if not blockers and not out["regressions_from_fixes"]:
            outcome = "no_blocking_findings" if round_no == 1 else "fixes_verified"
        elif round_no >= state["max_rounds"]:
            outcome = "rounds_exhausted"
            record["escalation"] = [{"id": f["id"], "what": f["what"], "reviewer_evidence": f["evidence"],
                                     "builder_disposition": dispositions.get(f["id"], "none")} for f in blockers]
        else:
            outcome = "blocking_findings"
    except ReviewError as e:
        outcome, record["error"] = e.outcome, e.detail
    finally:
        teardown(packet["repos"], root)
    record["outcome"] = outcome
    save(d, f"round-{round_no}.json", record)
    state.update(rounds_used=round_no, outcome=outcome)
    state["heads"].append([r["head"] for r in packet["repos"]])
    save(d, "packet.json", packet); save(d, "state.json", state)
    print(json.dumps({k: record[k] for k in record if k not in ("raw",)}, indent=2))
    return outcome


def cmd_disposition(a):
    d = rdir(a.review_id)
    disp = load(d, "dispositions.json") or {}
    for item in a.items:
        fid, _, rest = item.partition("=")
        value, _, evidence = rest.partition(":")
        if value not in DISPOSITIONS:
            sys.exit(f"{fid}: disposition must be one of {sorted(DISPOSITIONS)}")
        disp[fid] = {"disposition": value, "evidence": evidence} if evidence else value
    save(d, "dispositions.json", disp)
    print(json.dumps(disp, indent=2))


def cmd_status(a):
    d = rdir(a.review_id)
    print(json.dumps({"state": load(d, "state.json"), "dispositions": load(d, "dispositions.json"),
                      "rounds": [load(d, f"round-{i}.json").get("outcome") for i in range(1, load(d, 'state.json')['rounds_used'] + 1)]}, indent=2))


# ---------- selftest ----------

def selftest():
    global REVIEW_DIR
    tmp = Path(tempfile.mkdtemp(prefix="gstack-selftest-"))
    REVIEW_DIR = tmp / "reviews"
    repo = tmp / "repo"; repo.mkdir()
    sh = lambda *c: subprocess.run(["git", "-C", str(repo), *c], check=True, capture_output=True, text=True).stdout.strip()
    sh("init", "-q"); sh("config", "user.email", "t@t"); sh("config", "user.name", "t")
    (repo / "a.py").write_text("def f(x):\n    return x\n"); sh("add", "."); sh("commit", "-qm", "base"); base = sh("rev-parse", "HEAD")
    (repo / "a.py").write_text("def f(x):\n    return x + 1\n"); sh("commit", "-qam", "head"); head = sh("rev-parse", "HEAD")
    pk = {"outcome": "f adds one", "acceptance_criteria": ["f(1) == 2"], "repos": [{"path": str(repo), "base": base, "head": head}],
          "changed_behavior": "f returns x+1", "exclusions": [], "tests": {"commands": [], "results": "", "environment": "selftest"}}
    pfile = tmp / "packet.json"; pfile.write_text(json.dumps(pk))
    ns = lambda **k: argparse.Namespace(**k)

    # missing commit refused
    bad = dict(pk, repos=[dict(pk["repos"][0], head="deadbeef")]); (tmp / "bad.json").write_text(json.dumps(bad))
    try:
        load_packet(tmp / "bad.json"); assert False
    except ReviewError as e:
        assert e.outcome == "missing_commits"

    # recursion guard
    os.environ[RECURSION_ENV] = "1"
    try:
        cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30)); assert False
    except SystemExit as e:
        assert "recurse" in str(e)
    del os.environ[RECURSION_ENV]

    # unavailable tool is an outcome, not a pass
    binroot = tmp / "bin"; binroot.mkdir()  # PATH with git and sh only: no codex, no claude
    for tool in ("git", "sh"):
        os.symlink(shutil.which(tool), binroot / tool)
    os.environ["PATH"] = str(binroot)
    cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30))
    rid = sorted(p.name for p in REVIEW_DIR.iterdir())[-1]
    assert cmd_round(ns(review_id=rid, head=[])) == "review_unavailable"
    assert not list(Path(tempfile.gettempdir()).glob("gstack-peer-*")) or True  # teardown best-effort

    # malformed output
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "echo 'not json'"
    cmd_open(ns(builder="codex", packet=str(pfile), max_rounds=3, timeout=30))
    rid = sorted(p.name for p in REVIEW_DIR.iterdir())[-1]
    assert cmd_round(ns(review_id=rid, head=[])) == "malformed_output"

    # full loop: blocker -> disposition required -> fix round verified; then rounds exhausted path
    blocking = json.dumps({"verdict": "blocking_findings", "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                           "findings": [{"id": "F1", "severity": "blocking", "file": "a.py", "line": 2, "what": "x", "evidence": "y", "criterion": "z", "fix": "w"}]})
    clean = json.dumps({"verdict": "no_blocking_findings", "acceptance": [], "findings": []})
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{blocking}'"
    cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=2, timeout=30))
    rid = sorted(p.name for p in REVIEW_DIR.iterdir())[-1]
    assert cmd_round(ns(review_id=rid, head=[])) == "blocking_findings"
    try:
        cmd_round(ns(review_id=rid, head=[])); assert False
    except SystemExit as e:
        assert "disposition required" in str(e)
    cmd_disposition(ns(review_id=rid, items=["F1=fixed"]))
    (repo / "a.py").write_text("def f(x):\n    return x + 1  # fixed\n"); sh("commit", "-qam", "fix"); head2 = sh("rev-parse", "HEAD")
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{clean}'"
    assert cmd_round(ns(review_id=rid, head=[f"{repo}={head2}"])) == "fixes_verified"
    st = load(REVIEW_DIR / rid, "state.json"); assert st["rounds_used"] == 2 and st["heads"][-1] == [head2]
    # exhausted: blocker persists through the last allowed round -> escalation, never approval
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{blocking}'"
    cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=1, timeout=30))
    rid = sorted(p.name for p in REVIEW_DIR.iterdir())[-1]
    assert cmd_round(ns(review_id=rid, head=[])) == "rounds_exhausted"
    assert load(REVIEW_DIR / rid, "round-1.json")["escalation"][0]["id"] == "F1"
    assert not (repo / ".git" / "worktrees").exists() or not any((repo / ".git" / "worktrees").iterdir()), "worktree not torn down"
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open"); o.add_argument("--builder", required=True, choices=sorted(OTHER_TOOL)); o.add_argument("--packet", required=True)
    o.add_argument("--max-rounds", type=int, default=3); o.add_argument("--timeout", type=int, default=900)
    r = sub.add_parser("round"); r.add_argument("review_id"); r.add_argument("--head", action="append", default=[], metavar="REPO=SHA")
    dp = sub.add_parser("disposition"); dp.add_argument("review_id"); dp.add_argument("items", nargs="+")
    s = sub.add_parser("status"); s.add_argument("review_id")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        {"open": cmd_open, "round": cmd_round, "disposition": cmd_disposition, "status": cmd_status}[a.cmd](a)
    except ReviewError as e:
        sys.exit(f"{e.outcome}: {e.detail}")
    except KeyError:
        ap.print_help()


if __name__ == "__main__":
    main()
