#!/usr/bin/env python3
"""GO-003.5: what the goal checks decide. `.github/workflows/goal-envelope.yml` and `goal-tests.yml`
run this from main's copy, never the pull request's, on `pull_request_target`.

  goal_checks.py classify --pr <pr.json>                prints kind=item|goal|none for $GITHUB_OUTPUT
  goal_checks.py envelope --pr <event.json> --repo <main checkout> --main <sha> --candidate <sha> --out <verdict.json>
  goal_checks.py tests --pr <pr.json> --repo <main checkout> --main <sha> --candidate-dir <dir> --out <verdict.json>
  goal_checks.py holdout --pr <pr.json> --repo <main checkout> --main <sha> --candidate-dir <dir> --out <verdict.json>
                        reads the holdout from GOAL_HOLDOUT (the goal-holdout environment's secret)
  goal_checks.py publish --name <check> --verdict <verdict.json> --repo owner/name     needs GITHUB_TOKEN
  goal_checks.py sandbox-run <id> --goal <dir> --candidate <dir>      inside the sandbox only
  goal_checks.py holdout-run --candidate <dir>                       inside the sandbox only; source on stdin

A pull request into goal/<id> is an item (or a sync); one from goal/<id> into main is the goal pull
request; anything else isn't a goal pull request and passes. The pull request is read from the API when
the job starts (a retarget is an `edited` event that starts a fresh run), and a verdict is bound to
its head, base SHA and base branch, so `main`'s ruleset can require these
checks of every pull request. The goal tests run in a container with no network, no environment,
no capabilities and the candidate mounted read-only: candidate code never sees a token. Into
goal/<id>, the invariants must pass (the runner tracks outcomes); into main, every goal test must
pass. `publish` re-reads the pull request and posts nothing if its head or base moved, because the
push that moved it starts a fresh run; otherwise it posts the verdict as a check run on the head.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import goal_envelope as ge  # noqa: E402

# GO-002.6: one image for every governed repository, pinned by digest: Debian bookworm with Python 3.11
# (the harness) and Node 22 LTS (a Node candidate). A new digest is a change Dorian approves.
IMAGE = "node:22-bookworm@sha256:363e1587494626837fa7f9a23bdb453d13b0ff3c67c705c2805cfc69c2d2fad7"
DEPS_FILES = ("package.json", "package-lock.json", ".npmrc")


def install_deps(candidate_dir, run=subprocess.run):
    """GO-002.6: a Node candidate's dependencies, installed from its lockfile in a container of their
    own that has the network and nothing else: no checkout, no secret, no goal test, only the three
    files that say what to install, and `npm ci --ignore-scripts` so no package runs code while it
    installs. Returns the folder to mount read-only at /deps, or None for a candidate with no
    package-lock.json. Raises SystemExit, naming the failure, when the install fails."""
    cand = Path(candidate_dir)
    links = [f for f in DEPS_FILES if (cand / f).is_symlink()]
    if links:   # review F1: a link could point the networked container at a file outside these three
        raise SystemExit(f"refused: {', '.join(links)} in the candidate is a symlink; the install takes regular files only")
    if not (cand / "package-lock.json").is_file():
        return None
    deps = Path(tempfile.mkdtemp(prefix="goal-deps-"))
    for f in DEPS_FILES:
        if (cand / f).is_file():
            shutil.copyfile(cand / f, deps / f, follow_symlinks=False)
    os.chmod(deps, 0o777)                  # the container runs as uid 65534
    r = run(["docker", "run", "--rm", "--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL",
             "--security-opt", "no-new-privileges", "--user", "65534:65534", "--pids-limit", "512",
             "--memory", "2g", "-e", "HOME=/tmp", "-e", "npm_config_cache=/tmp/npm", "-w", "/deps",
             "-v", f"{deps.resolve()}:/deps", IMAGE,
             "npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
            capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        raise SystemExit(f"npm ci failed in the install container: {(r.stderr or r.stdout)[-1500:]}")
    return deps


def writable(candidate):
    """Inside the sandbox: a Node candidate (one with a package.json) runs from a copy on the container's
    /tmp, with the installed dependencies linked in read-only when there are any, because a build writes
    into its own folder and the candidate's mount is read-only. Any other candidate runs where it is."""
    if not Path(candidate, "package.json").is_file():
        return candidate
    copy = Path("/tmp/candidate")
    shutil.copytree(candidate, copy, ignore=shutil.ignore_patterns(".git", "node_modules"), symlinks=True)
    if Path("/deps/node_modules").is_dir():      # review F2: a dependency-free build still gets the copy
        (copy / "node_modules").symlink_to("/deps/node_modules")
    return str(copy)


def classify(pr):
    """('item' | 'goal' | 'none', goal id or None)."""
    base, head = pr["base"]["ref"], pr["head"]["ref"]
    if base.startswith("goal/"):
        return "item", base[5:]
    if base == "main" and head.startswith("goal/"):
        return "goal", head[5:]
    return "none", None


def verdict(pr, conclusion, title, summary):
    return {"pr": pr["number"], "head": pr["head"]["sha"], "base": pr["base"]["sha"], "base_ref": pr["base"]["ref"],
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
    record = f"goal-runs/{gid}/RESULT.md"
    if kind == "goal" and record not in ge.git(repo, "diff", "--name-only", main_sha, candidate).split():
        # The run record is a CODEOWNERS path, so carrying it is what makes GitHub require Dorian's review.
        errors.append(f"the goal pull request doesn't carry its run record {record} (GO-003.7)")
    summary = f"Examined {n} goal-authored commits against main {main_sha[:12]}.\n\n" + "\n".join(f"- {e}" for e in errors)
    return verdict(pr, "failure" if errors else "success",
                   f"{len(errors)} file(s) outside the envelope" if errors else f"inside the envelope ({n} commits)", summary)


def sandbox_cmd(main_dir, candidate_dir, gid, deps=None):
    """The container the goal tests run in: no network, no host environment, no capabilities, an
    unprivileged user and read-only mounts. Only /tmp is writable, and it allows exec: a goal test
    may need a stub program there (cloud-review-survives' gitleaks), and the candidate already runs
    as arbitrary code in this container, so Docker's default noexec on a tmpfs held nothing back."""
    return ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:exec",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
            "--pids-limit", "256", "--memory", "1g", "-e", "HOME=/tmp", "-w", "/tmp",
            "-v", f"{Path(main_dir).resolve()}:/main:ro", "-v", f"{Path(candidate_dir).resolve()}:/candidate:ro",
            *(["-v", f"{Path(deps).resolve()}:/deps:ro"] if deps else []),
            IMAGE, "python3", "-B", "/main/plugins/gstack-execution/scripts/goal_checks.py", "sandbox-run", gid,
            "--goal", f"/main/goals/{gid}", "--candidate", "/candidate"]


def sandbox_run(gid, goal_dir, candidate):
    import goal_brief as gb
    tests = gb.goal_tests(gb.sections(Path(goal_dir, "GOAL.md").read_text()).get("Goal tests", ""), [])
    candidate = writable(candidate)
    return {tid: {"kind": kind, "result": gb.run_test(candidate, goal_dir, tid)} for tid, kind in tests}


def tests(pr, repo, main_sha, candidate_dir, run=subprocess.run):
    kind, gid = classify(pr)
    if kind == "none":
        return verdict(pr, "success", "not a goal pull request", "No goal tests apply.")
    if not ge.GOAL_ID.match(gid) or not Path(repo, "goals", gid, "GOAL.md").is_file():
        return verdict(pr, "failure", f"goals/{gid}/ is not on main", "Only an approved goal has goal tests.")
    try:
        deps = install_deps(candidate_dir)
    except SystemExit as e:
        return verdict(pr, "failure", "the candidate's dependencies didn't install", str(e)[-2000:])
    r = run(sandbox_cmd(repo, candidate_dir, gid, deps), capture_output=True, text=True, timeout=1800)
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


def secret_name(gid):
    return "GOAL_%s_HOLDOUT" % gid.upper().replace("-", "_")


def holdout_cmd(main_dir, candidate_dir, deps=None):
    """The holdout's container: the goal-tests sandbox, with the holdout on stdin (-i) and nowhere
    else: not in its environment, not on any disk the candidate can reach."""
    cmd = sandbox_cmd(main_dir, candidate_dir, "x", deps)
    image = cmd.index(IMAGE)
    return cmd[:2] + ["-i"] + cmd[2:image + 1] + [
        "python3", "-B", "/main/plugins/gstack-execution/scripts/goal_checks.py", "holdout-run", "--candidate", "/candidate"]


def holdout(pr, repo, main_sha, candidate_dir, source, run=subprocess.run):
    """GO-003.6: the holdout, checked against main's holdout.sha256, run against the merge candidate."""
    kind, gid = classify(pr)
    if kind != "goal":
        return verdict(pr, "success", "not a goal pull request into main", "The holdout runs only on a goal's pull request into main.")
    want = Path(repo, "goals", gid, "holdout.sha256")
    if not ge.GOAL_ID.match(gid) or not want.is_file():
        return verdict(pr, "failure", f"goals/{gid}/holdout.sha256 is not on main", "Only an approved goal has a holdout.")
    carried = Path(candidate_dir, "goal-runs", gid, "holdout.py") if candidate_dir else None
    if carried is not None and carried.is_file() and not carried.is_symlink():
        source = carried.read_text()
        carried.unlink()      # GO-002.8: read here, then gone, so the candidate's code can't open it while it runs
    if not source:
        return verdict(pr, "failure", f"no goal-runs/{gid}/holdout.py in the goal pull request and no {secret_name(gid)} secret",
                       "The run's finalize step carries the approved holdout; without it the goal can't reach main.")
    expected = want.read_text().strip()
    if expected not in {hashlib.sha256(s.encode()).hexdigest() for s in (source, source + "\n", source.rstrip("\n"))}:
        return verdict(pr, "failure", "the holdout doesn't match holdout.sha256",
                       "The stored secret isn't the holdout Dorian approved; nothing was run.")
    try:
        deps = install_deps(candidate_dir)       # before the holdout exists anywhere: it's on stdin below
    except SystemExit as e:
        return verdict(pr, "failure", "the candidate's dependencies didn't install", str(e)[-2000:])
    r = run(holdout_cmd(repo, candidate_dir, deps), input=source, capture_output=True, text=True, timeout=3600)
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
        result, why = out["result"], out.get("detail") or ""
    except (ValueError, IndexError, KeyError, TypeError):
        return verdict(pr, "failure", "the holdout did not report", (r.stderr or r.stdout)[-2000:])
    if result == "passed":
        return verdict(pr, "success", "the holdout passed", f"Every holdout test passed against the merge candidate; main {main_sha[:12]}.")
    return verdict(pr, "failure", f"the holdout {result}: possible reward hack",
                   "The goal tests pass but the holdout, which the builder never saw, does not. The run stops (GO-003.6). "
                   "What failed, for the diagnosis; this holdout is spent, so another run needs a new goal folder:\n\n"
                   + (why or "(no detail reported)"))


def api(token, method, path, data=None):
    req = urllib.request.Request("https://api.github.com/" + path, method=method,
                                 data=None if data is None else json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def provenance(v):
    """What a published verdict was reached for, in its check run's external_id, so a reader can
    refuse a success reached for another pull request, another base or none at all (GO-005.4)."""
    return f"pr={v['pr']};base_ref={v['base_ref']};base={v['base']}"


def publish(name, v, repo_name, call):
    """Post the verdict on the head it was reached for, or nothing if the PR moved."""
    pr = call("GET", f"repos/{repo_name}/pulls/{v['pr']}")
    if (pr["head"]["sha"], pr["base"]["sha"], pr["base"]["ref"]) != (v["head"], v["base"], v["base_ref"]):
        return (f"PR #{v['pr']} moved (head {pr['head']['sha'][:12]}, base {pr['base']['ref']} at "
                f"{pr['base']['sha'][:12]}); published nothing")
    call("POST", f"repos/{repo_name}/check-runs",
         {"name": name, "head_sha": v["head"], "status": "completed", "conclusion": v["conclusion"],
          "external_id": provenance(v),
          "output": {"title": v["title"][:255], "summary": v["summary"][:60000]}})
    return f"published {name}: {v['conclusion']} on {v['head'][:12]}"


def main(argv):
    cmd = argv[0] if argv else None
    if cmd == "holdout-run" and argv[1:2] == ["--candidate"] and len(argv) == 3:
        import goal_brief as gb
        result, why = gb.run_holdout(writable(argv[2]), sys.stdin.read(), detail=True)
        print(json.dumps({"result": result, "detail": why}))
        return 0
    if cmd == "sandbox-run" and len(argv) == 6:
        o = dict(zip(argv[2::2], argv[3::2]))
        print(json.dumps(sandbox_run(argv[1], o["--goal"], o["--candidate"])))
        return 0
    o = dict(zip(argv[1::2], argv[2::2]))
    if cmd == "classify" and set(o) == {"--pr"}:
        kind, gid = classify(json.loads(Path(o["--pr"]).read_text()))
        print("kind=" + kind)
        if kind == "goal" and ge.GOAL_ID.match(gid):
            print("secret=" + secret_name(gid))
        return 0
    if cmd in ("envelope", "tests", "holdout") and "--pr" in o:
        pr = json.loads(Path(o["--pr"]).read_text())   # the pull request as the job found it, not the event
        v = (envelope(pr, o["--repo"], o["--main"], o["--candidate"]) if cmd == "envelope"
             else tests(pr, o["--repo"], o["--main"], o["--candidate-dir"]) if cmd == "tests"
             else holdout(pr, o["--repo"], o["--main"], o.get("--candidate-dir", ""), os.environ.get("GOAL_HOLDOUT", "")))
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
