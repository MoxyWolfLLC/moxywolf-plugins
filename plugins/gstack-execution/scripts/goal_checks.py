#!/usr/bin/env python3
"""GO-003.5: what the goal checks decide. `.github/workflows/goal-envelope.yml` and `goal-tests.yml`
run this from main's copy, never the pull request's, on `pull_request_target`.

  goal_checks.py classify --event <event.json>          prints kind=item|goal|none for $GITHUB_OUTPUT
  goal_checks.py envelope --event <event.json> --repo <main checkout> --main <sha> --candidate <sha> --out <verdict.json>
  goal_checks.py tests --event <event.json> --repo <main checkout> --main <sha> --candidate-dir <dir> --out <verdict.json>
  goal_checks.py publish --name <check> --verdict <verdict.json> --repo owner/name     needs GITHUB_TOKEN
  goal_checks.py sandbox-run <id> --goal <dir> --candidate <dir>      inside the sandbox only

A pull request into goal/<id> is an item (or a sync); one from goal/<id> into main is the goal pull
request; anything else isn't a goal pull request and passes, so `main`'s ruleset can require these
checks of every pull request. The goal tests run in a container with no network, no environment,
no capabilities and the candidate mounted read-only: candidate code never sees a token. Into
goal/<id>, the invariants must pass (the runner tracks outcomes); into main, every goal test must
pass. `publish` re-reads the pull request and posts nothing if its head or base moved, because the
push that moved it starts a fresh run; otherwise it posts the verdict as a check run on the head.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import goal_envelope as ge  # noqa: E402

IMAGE = "python:3.11-slim"


def classify(pr):
    """('item' | 'goal' | 'none', goal id or None)."""
    base, head = pr["base"]["ref"], pr["head"]["ref"]
    if base.startswith("goal/"):
        return "item", base[5:]
    if base == "main" and head.startswith("goal/"):
        return "goal", head[5:]
    return "none", None


def verdict(pr, conclusion, title, summary):
    return {"pr": pr["number"], "head": pr["head"]["sha"], "base": pr["base"]["sha"],
            "conclusion": conclusion, "title": title, "summary": summary}


def envelope(pr, repo, main_sha, candidate):
    kind, gid = classify(pr)
    if kind == "none":
        return verdict(pr, "success", "not a goal pull request", "Nothing for the envelope to check.")
    if not ge.GOAL_ID.match(gid):
        return verdict(pr, "failure", f"'{gid}' is not a goal id", "A goal branch is goal/<lowercase id>.")
    try:
        errors, n = ge.check(repo, gid, candidate, base=main_sha)
        on_main = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", candidate, main_sha]).returncode == 0
    except SystemExit as e:
        return verdict(pr, "failure", "envelope could not be read", str(e))
    if not errors and n == 0 and not on_main:
        errors = ["examined no goal-authored commits and the candidate is not on main"]
    summary = f"Examined {n} goal-authored commits against main {main_sha[:12]}.\n\n" + "\n".join(f"- {e}" for e in errors)
    return verdict(pr, "failure" if errors else "success",
                   f"{len(errors)} file(s) outside the envelope" if errors else f"inside the envelope ({n} commits)", summary)


def sandbox_cmd(main_dir, candidate_dir, gid):
    """The container the goal tests run in: no network, no host environment, no capabilities, an
    unprivileged user and read-only mounts. Only /tmp is writable."""
    return ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
            "--pids-limit", "256", "--memory", "1g", "-e", "HOME=/tmp", "-w", "/tmp",
            "-v", f"{Path(main_dir).resolve()}:/main:ro", "-v", f"{Path(candidate_dir).resolve()}:/candidate:ro",
            IMAGE, "python3", "-B", "/main/plugins/gstack-execution/scripts/goal_checks.py", "sandbox-run", gid,
            "--goal", f"/main/goals/{gid}", "--candidate", "/candidate"]


def sandbox_run(gid, goal_dir, candidate):
    import goal_brief as gb
    tests = gb.goal_tests(gb.sections(Path(goal_dir, "GOAL.md").read_text()).get("Goal tests", ""), [])
    return {tid: {"kind": kind, "result": gb.run_test(candidate, goal_dir, tid)} for tid, kind in tests}


def tests(pr, repo, main_sha, candidate_dir, run=subprocess.run):
    kind, gid = classify(pr)
    if kind == "none":
        return verdict(pr, "success", "not a goal pull request", "No goal tests apply.")
    if not ge.GOAL_ID.match(gid) or not Path(repo, "goals", gid, "GOAL.md").is_file():
        return verdict(pr, "failure", f"goals/{gid}/ is not on main", "Only an approved goal has goal tests.")
    r = run(sandbox_cmd(repo, candidate_dir, gid), capture_output=True, text=True, timeout=1800)
    try:
        results = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return verdict(pr, "failure", "the goal tests did not report", (r.stderr or r.stdout)[-2000:])
    if not results:
        return verdict(pr, "failure", "examined no goal tests", "A check over no tests is not a pass.")
    gating = {t: v for t, v in results.items() if kind == "goal" or v["kind"] == "invariant"}
    bad = sorted(t for t, v in gating.items() if v["result"] != "passed")
    lines = [f"- `{t}` ({v['kind']}): {v['result']}" for t, v in sorted(results.items())]
    rule = "every goal test must pass" if kind == "goal" else "every invariant must pass"
    return verdict(pr, "failure" if bad else "success",
                   f"{len(bad)} gating goal test(s) not passing" if bad else f"{len(results)} goal tests ran; {rule}",
                   f"Main {main_sha[:12]}, goals/{gid}/; {rule}.\n\n" + "\n".join(lines))


def api(token, method, path, data=None):
    req = urllib.request.Request("https://api.github.com/" + path, method=method,
                                 data=None if data is None else json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def publish(name, v, repo_name, call):
    """Post the verdict on the head it was reached for, or nothing if the PR moved."""
    pr = call("GET", f"repos/{repo_name}/pulls/{v['pr']}")
    if pr["head"]["sha"] != v["head"] or pr["base"]["sha"] != v["base"]:
        return f"PR #{v['pr']} moved (head {pr['head']['sha'][:12]}, base {pr['base']['sha'][:12]}); published nothing"
    call("POST", f"repos/{repo_name}/check-runs",
         {"name": name, "head_sha": v["head"], "status": "completed", "conclusion": v["conclusion"],
          "output": {"title": v["title"][:255], "summary": v["summary"][:60000]}})
    return f"published {name}: {v['conclusion']} on {v['head'][:12]}"


def main(argv):
    cmd = argv[0] if argv else None
    if cmd == "sandbox-run" and len(argv) == 6:
        o = dict(zip(argv[2::2], argv[3::2]))
        print(json.dumps(sandbox_run(argv[1], o["--goal"], o["--candidate"])))
        return 0
    o = dict(zip(argv[1::2], argv[2::2]))
    if cmd == "classify" and set(o) == {"--event"}:
        print("kind=" + classify(json.loads(Path(o["--event"]).read_text())["pull_request"])[0])
        return 0
    if cmd in ("envelope", "tests") and "--event" in o:
        pr = json.loads(Path(o["--event"]).read_text())["pull_request"]
        v = (envelope(pr, o["--repo"], o["--main"], o["--candidate"]) if cmd == "envelope"
             else tests(pr, o["--repo"], o["--main"], o["--candidate-dir"]))
        Path(o["--out"]).write_text(json.dumps(v))
        print(f"{v['conclusion']}: {v['title']}\n{v['summary']}")
        return 0
    if cmd == "publish" and {"--name", "--verdict", "--repo"} <= set(o):
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("publish needs GITHUB_TOKEN")
            return 2
        print(publish(o["--name"], json.loads(Path(o["--verdict"]).read_text()), o["--repo"],
                      lambda m, p, d=None: api(token, m, p, d)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
