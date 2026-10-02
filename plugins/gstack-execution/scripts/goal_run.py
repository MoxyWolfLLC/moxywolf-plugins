#!/usr/bin/env python3
"""GO-003: the goal runner. The agent drives a goal with it, one step at a time, under
`agent_token.py exec --` so git and the GitHub API act as the bot.

  goal_run.py start <id> --pr N --builder <family>/<model> [--repo owner/name]
        verifies the goal (GO-001.3), refuses a builder from the family that drafted or read the
        goal tests and a token with a secrets permission (GO-003.3), opens goal/<id> from main
  goal_run.py next <id>
        exit 0 with the next PLAN.md item (JSON) to build through /gstack-build into goal/<id>, or
        with {"step": "finish"} when every goal test passes; exit 1 with the outcome when the run
        has ended (stopped or exhausted). Checks, in order: HALT on main (GO-004.3), the goal folder
        unchanged on main (GO-002.5), the spend ledger (GO-004.2), Max items.
  goal_run.py merged <id> --head <sha>
        after an item's pull request merged into goal/<id>: runs the goal tests at that head and
        stops the run on a failing invariant or an outcome test that passed and now fails (GO-003.4)
  goal_run.py complete <id> --pr N --merge <sha> [--repo owner/name]
        records `complete` once GitHub shows the goal pull request from goal/<id> merged into main as
        <sha> at the head whose goal tests passed (GO-003.8)
  goal_run.py record <id>
        prints the run record, goal-runs/<id>/RESULT.md

Run it from a checkout of the repository it governs; an installed plugin copy has no main,
CODEOWNERS or goal folder to read and refuses. State lives in GSTACK_GOAL_RUN_DIR/<id>/ (a durable folder, like the review records): state.json,
the frozen copy of the approved goal folder, and the spend ledger. Every exit but 0 means stop.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if not (Path(__file__).resolve().parents[3] / ".github" / "CODEOWNERS").is_file():
    # an installed plugin copy has no repository around it: the runner reads main, CODEOWNERS and
    # the goal folder from the checkout it lives in, so it runs only from inside one
    sys.exit("goal_run.py runs from a checkout of the repository it governs "
             "(plugins/gstack-execution/scripts/goal_run.py there), not from an installed plugin copy")
import goal_brief as gb  # noqa: E402
import goal_envelope as ge  # noqa: E402
import goal_spend as gs  # noqa: E402

OUTCOMES = ("complete", "stopped", "exhausted")
REPO = "MoxyWolfLLC/moxywolf-plugins"


class Refused(Exception):
    pass


def run_dir(goal_id):
    root = os.environ.get("GSTACK_GOAL_RUN_DIR")
    if not root:
        raise Refused("set GSTACK_GOAL_RUN_DIR to a durable folder (the vault), not the session's home")
    if not ge.GOAL_ID.match(goal_id):
        raise Refused(f"goal id must be lowercase letters, digits and hyphens, got: {goal_id}")
    return Path(root, goal_id)


def load(goal_id):
    f = run_dir(goal_id) / "state.json"
    if not f.is_file():
        raise Refused(f"no run of {goal_id}; start it first")
    return json.loads(f.read_text())


def save(state):
    d = run_dir(state["goal"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(d / "state.json")


def plan_items(text):
    """[(title, [criteria])] from a PLAN.md that goal_brief.py check accepted."""
    items = []
    for line in text.splitlines():
        if re.match(r"^\d+\.\s+\S", line):
            items.append([re.sub(r"^\d+\.\s+", "", line).strip(), []])
        elif items and re.match(r"^\s+[-*]\s+\S", line):
            items[-1][1].append(re.sub(r"^\s+[-*]\s+", "", line).strip())
    return items


def granted_secrets(granted):
    """Permission names that reach secrets. The runner refuses a token that holds any of them."""
    return sorted(k for k in granted if "secret" in k.lower())


def tree_on(repo, ref, goal_id):
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}:goals/{goal_id}"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def start(repo, goal_id, pr, builder, verify, granted, create_branch, base="origin/main", repo_name=REPO):
    d = run_dir(goal_id)
    if (d / "state.json").is_file() and load(goal_id).get("outcome") is None:
        raise Refused(f"{goal_id} already has a run in progress")
    record, errors = verify(goal_id, pr, repo_name)
    if errors:
        raise Refused("verify refused the goal: " + "; ".join(errors))
    family = builder.split("/", 1)[0].lower()
    if family in record["drafted_by"] or family == record["read_by"]:
        raise Refused(f"the builder's family {family} drafted or read the goal tests "
                      f"(drafted by {sorted(record['drafted_by'])}, read by {record['read_by']})")
    if granted_secrets(granted):
        raise Refused(f"the token holds {granted_secrets(granted)}; a goal run's token never reaches secrets")
    if tree_on(repo, base, goal_id) != record["tree"]:
        raise Refused(f"goals/{goal_id}/ on {base} isn't the tree Dorian approved; fetch main")
    main_sha = ge.git(repo, "rev-parse", f"{base}^{{commit}}").strip()
    goal = d / "goal"
    if goal.exists():
        shutil.rmtree(goal)
    goal.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(repo), "archive", record["tree"]], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(goal)], input=archive, check=True)
    brief = (goal / "GOAL.md").read_text()
    create_branch(f"goal/{goal_id}", main_sha)
    budgets, cap, max_calls = gs.limits(brief)
    secs = gb.sections(brief)
    state = {"goal": goal_id, "pr": pr, "builder": builder, "tree": record["tree"], "approved_head": record["head"],
             "review_id": record["review_id"], "drafted_by": record["drafted_by"], "read_by": record["read_by"],
             "branch": f"goal/{goal_id}", "main_at_start": main_sha,
             "items": [{"n": i + 1, "title": t, "criteria": c} for i, (t, c) in enumerate(plan_items((goal / "PLAN.md").read_text()))],
             "max_items": int(secs["Max items"]), "max_rounds": int(secs["Max review rounds per item"]),
             "tests": gb.goal_tests(secs["Goal tests"], []), "done": [], "passing": [], "results": [],
             "outcome": None, "reason": None, "merge": None}
    (d / "spend.jsonl").touch()
    save(state)
    return state


def end(state, outcome, reason):
    state["outcome"], state["reason"] = outcome, reason
    save(state)
    return {"outcome": outcome, "reason": reason}


def next_step(repo, goal_id, base="origin/main"):
    state = load(goal_id)
    if state["outcome"]:
        return False, {"outcome": state["outcome"], "reason": state["reason"]}
    d = run_dir(goal_id)
    try:
        if ge.halted(repo, goal_id, base):
            return False, end(state, "stopped", f"goals/{goal_id}/HALT is on main")
        if tree_on(repo, base, goal_id) != state["tree"]:
            return False, end(state, "stopped", f"goals/{goal_id}/ changed on main mid-run; a changed goal is a new goal")
    except SystemExit as e:
        return False, end(state, "stopped", str(e))
    stop, reasons, totals = gs.status(d / "spend.jsonl", (d / "goal" / "GOAL.md").read_text())
    if stop:
        return False, end(state, "stopped", "; ".join(reasons))
    ids = [t for t, _ in state["tests"]]
    if ids and set(ids) <= set(state["passing"]):
        return True, {"step": "finish", "branch": state["branch"], "spend": totals}
    remaining = [i for i in state["items"] if i["n"] not in state["done"]]
    if not remaining or len(state["done"]) >= state["max_items"]:
        failing = sorted(set(ids) - set(state["passing"]))
        return False, end(state, "exhausted", f"the plan ran out with goal tests still failing: {failing}")
    item = remaining[0]
    return True, {"step": "build", "item": item, "base_branch": state["branch"], "max_rounds": state["max_rounds"],
                  "ledger": str(d / "spend.jsonl"), "spend": totals}


def merged(repo, goal_id, head):
    """Run the goal tests at head; stop on a failing invariant or a regressed outcome."""
    state = load(goal_id)
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    remaining = [i for i in state["items"] if i["n"] not in state["done"]]
    if not remaining:
        raise Refused("no item is in progress")
    goal = run_dir(goal_id) / "goal"
    wt = tempfile.mkdtemp(prefix="goal-head-")
    ge.git(repo, "worktree", "add", "--detach", wt, head)
    try:
        results = {tid: gb.run_test(wt, goal, tid) for tid, _ in state["tests"]}
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", wt], capture_output=True)
    state["done"].append(remaining[0]["n"])
    state["results"].append({"item": remaining[0]["n"], "head": head, "results": results})
    kinds = dict(state["tests"])
    bad = [f"invariant {t} {r}" for t, r in results.items() if kinds[t] == "invariant" and r != "passed"]
    bad += [f"outcome {t} passed before and is now {r}" for t, r in results.items()
            if kinds[t] == "outcome" and t in state["passing"] and r != "passed"]
    state["passing"] = sorted(t for t, r in results.items() if r == "passed")
    if bad:
        return end(state, "stopped", "regression at " + head[:12] + ": " + "; ".join(bad))
    save(state)
    return {"item": remaining[0]["n"], "results": results}


def complete(goal_id, pr, merge_sha, get, repo_name=REPO):
    """Record `complete` only on GitHub's word that this goal's pull request merged into main as
    merge_sha, from goal/<id> at the head whose goal tests last passed."""
    state = load(goal_id)
    ids = [t for t, _ in state["tests"]]
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    if not ids or not set(ids) <= set(state["passing"]):
        raise Refused("complete needs every goal test passing at the last merged head")
    p = get(f"repos/{repo_name}/pulls/{pr}")
    tested = state["results"][-1]["head"]
    problems = [m for ok, m in [
        (p["base"]["ref"] == "main", f"PR #{pr} targets {p['base']['ref']}, not main"),
        (p["head"]["ref"] == state["branch"], f"PR #{pr} is from {p['head']['ref']}, not {state['branch']}"),
        (p.get("merged") is True, f"PR #{pr} is not merged"),
        (p.get("merge_commit_sha") == merge_sha, f"PR #{pr} merged as {(p.get('merge_commit_sha') or 'nothing')[:12]}, not {merge_sha[:12]}"),
        (p["head"]["sha"] == tested, f"PR #{pr} merged head {p['head']['sha'][:12]}, not {tested[:12]} where the goal tests passed"),
    ] if not ok]
    if problems:
        raise Refused("; ".join(problems))
    state["merge"], state["final_pr"] = merge_sha, pr
    return end(state, "complete", f"PR #{pr} merged to main in {merge_sha[:12]}")


def record(goal_id):
    state, d = load(goal_id), run_dir(goal_id)
    _, _, totals = gs.status(d / "spend.jsonl", (d / "goal" / "GOAL.md").read_text())
    lines = [f"# Goal run: {goal_id}", "",
             f"- Outcome: {state['outcome'] or 'running'}" + (f" ({state['reason']})" if state["reason"] else ""),
             f"- Approved in PR #{state['pr']} by review {state['review_id']} at {state['approved_head'][:12]}, tree {state['tree'][:12]}",
             f"- Goal tests drafted by {', '.join(state['drafted_by'])}, read by {state['read_by']}",
             f"- Builder: {state['builder']}", f"- Goal branch: {state['branch']} from {state['main_at_start'][:12]}",
             f"- Spend: ${totals.get('total', '?')} across {json.dumps(totals.get('spent', {}))}; {totals.get('calls', '?')} counted calls",
             "", "## Items", ""]
    for i in state["items"]:
        lines.append(f"{i['n']}. {i['title']} - {'merged' if i['n'] in state['done'] else 'not built'}")
    lines += ["", "## Goal tests at the last merged head", ""]
    last = state["results"][-1]["results"] if state["results"] else {}
    for t, k in state["tests"]:
        lines.append(f"- `{t}` ({k}): {last.get(t, 'not run')}")
    if state["merge"]:
        lines += ["", "## Rolling back", "", "```", ge.revert_commands(state["merge"]), "```"]
    return "\n".join(lines) + "\n"


def main(argv, repo=gb.ROOT):
    cmd, goal_id = (argv + [None, None])[:2]
    opts = dict(zip(argv[2::2], argv[3::2]))
    try:
        if cmd == "start" and goal_id and {"--pr", "--builder"} <= set(opts) <= {"--pr", "--builder", "--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise Refused("start needs GITHUB_TOKEN: run it under agent_token.py exec --")
            name = opts.get("--repo", REPO)
            get = gb.github(token)
            perms = subprocess.run([sys.executable, str(Path(__file__).with_name("agent_token.py")), "permissions",
                                    "--repo", name], capture_output=True, text=True)
            if perms.returncode:
                raise Refused(f"can't read the token's permissions: {perms.stderr.strip()[-300:]}")
            granted = dict(re.findall(r"^\s{2}(\w+)\s+(\w+)\s*$", perms.stdout, re.M))

            def create_branch(ref, sha):
                ge.git(repo, "push", "origin", f"{sha}:refs/heads/{ref}")

            start(repo, goal_id, int(opts["--pr"]), opts["--builder"],
                  lambda g, p, n: gb.verify(g, p, n, get), granted, create_branch, repo_name=name)
            print(json.dumps({"started": goal_id}))
            return 0
        if cmd == "next" and goal_id and not opts:
            ok, out = next_step(repo, goal_id)
            print(json.dumps(out))
            return 0 if ok else 1
        if cmd == "merged" and goal_id and set(opts) == {"--head"}:
            out = merged(repo, goal_id, opts["--head"])
            print(json.dumps(out))
            return 1 if out.get("outcome") else 0
        if cmd == "complete" and goal_id and {"--pr", "--merge"} <= set(opts) <= {"--pr", "--merge", "--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise Refused("complete needs GITHUB_TOKEN: run it under agent_token.py exec --")
            print(json.dumps(complete(goal_id, int(opts["--pr"]), opts["--merge"], gb.github(token),
                                      opts.get("--repo", REPO))))
            return 0
        if cmd == "record" and goal_id and not opts:
            print(record(goal_id), end="")
            return 0
    except Refused as e:
        print(f"REFUSED: {e}")
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
