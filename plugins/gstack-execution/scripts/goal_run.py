#!/usr/bin/env python3
"""GO-003: the goal runner. The agent drives a goal with it, one step at a time, under
`agent_token.py exec --` so git and the GitHub API act as the bot.

  goal_run.py start <id> --pr N --builder <family>/<model> [--repo owner/name]
        verifies the goal (GO-001.3), refuses a builder from the family that drafted or read the
        goal tests and a token with a secrets permission (GO-003.3), opens goal/<id> from main
  goal_run.py next <id>
        exit 0 with the next PLAN.md item (JSON) to build through /gstack-build into goal/<id>, or
        with {"step": "finish"} when every goal test passes; exit 3 while a judgment call waits for
        Dorian; exit 1 with the outcome when the run has ended (stopped or exhausted). Checks, in order: HALT on main (GO-004.3), the goal folder
        unchanged on main (GO-002.5), the spend ledger (GO-004.2), Max items.
  goal_run.py merged <id> --item N --head <sha> --unsure <text> [--review <review-id>]
        after item N's pull request merged into goal/<id> as <sha>: runs the goal tests at that head
        and stops the run on a failing invariant or an outcome test that passed and now fails
        (GO-003.4). N must be the item `next` issued and <sha> a head not already recorded. --unsure
        is what the agent is least sure of in the item, for its digest (GO-006.1); --review names the
        item's review, whose blocking findings' files are compared with the previous item's
  goal_run.py failed <id> --item N --reason <text>
        item N's build ended without a merge (rounds_exhausted, review_unavailable, ...): the run
        stops with that reason
  goal_run.py call <id> --question <text> --options <json list> --proposed-by <fam/model>
                  --framed-by <fam/model> --head <sha>
        records a judgment call (GO-005): code types the change at <sha> and names the decider
  goal_run.py council <id> --call N --votes <json list>
        the council's two votes on an in_envelope_code call: unanimous decides, split escalates
  goal_run.py answer <id> --call N --choice <option> --words <Dorian's words>
        Dorian's answer to a call that's his; until then `next` exits 3 and the run waits
  goal_run.py finalize <id> [--repo owner/name]
        every goal test passes: commits the run record, goal-runs/<id>/RESULT.md, alone on a branch
        from goal/<id> and opens its pull request into goal/<id> (GO-003.7)
  goal_run.py propose <id> [--repo owner/name]
        the finalize pull request merged: opens the goal pull request from goal/<id> into main, which
        the goal checks, the holdout, a fresh cross-vendor review and Dorian's approval gate
  goal_run.py may <id> --action <class> --resource <r> [--head <sha> --review <review-id> --pr <n>] [--repo owner/name]
        before every push, pull request, merge or outside call the agent makes in a run (GO-005.4, .5):
        exit 0 if the goal ledger grants it (an item merge: into goal/<id>, after a clean review at
        <sha>); exit 1 if it's Dorian's, or if what a push, pull request or merge sets off changed
        since the start, which stops the run. Resources: vcs.push <branch>; pr.open <base><-<head>;
        merge <target>; net.connect <host>; review.send_code <tool>; external.model_call <model>
  goal_run.py resync <id> --head <sha>
        the goal pull request's head moved because a sync from main merged into goal/<id>
        (GO-004.1): accepts the new head only if it merges the recorded head with a commit on main,
        keeps the run record and passes the envelope check
  goal_run.py holdout-failed <id> --detail <text>
        goal-holdout failed on the goal pull request: escalates and ends the run (GO-003.6, GO-006.2)
  goal_run.py ack <id> --escalation N --words <Dorian's words>
        Dorian's acknowledgement of an escalation that holds the run; until then `next` exits 3
  Every command also prints {"messages": [...]}, when there are new ones: GO-006's digests and
  escalations, for the agent to relay to Dorian. They're kept in the run record either way.
  goal_run.py stop <id> --reason <text>
        ends a run that hasn't ended, e.g. when goal-holdout fails (a possible reward hack, GO-003.6)
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
import goal_calls as gcalls  # noqa: E402
import goal_guard as gguard  # noqa: E402

OUTCOMES = ("complete", "stopped", "exhausted")
REPO = "MoxyWolfLLC/moxywolf-plugins"


Refused = gguard.Refused


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


def granted_beyond(granted):
    """Permissions a goal run's token must not hold: anything reaching secrets (GO-003.3) and the
    workflows permission (GO-003.5), so no workflow of the agent's runs before a merge-time check."""
    return sorted(k for k in granted if "secret" in k.lower() or k == "workflows")


def tree_on(repo, ref, goal_id):
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}:goals/{goal_id}"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def start(repo, goal_id, pr, builder, verify, granted, create_branch, base="origin/main", repo_name=REPO, *, environments):
    d = run_dir(goal_id)
    if (d / "state.json").is_file() and load(goal_id).get("outcome") is None:
        raise Refused(f"{goal_id} already has a run in progress")
    if base.startswith("origin/"):                     # GO-005.5 assesses current main, so fetch it first
        b = base.split("/", 1)[1]
        try:
            ge.git(repo, "fetch", "--no-tags", "origin", f"+refs/heads/{b}:refs/remotes/{base}")
        except SystemExit as e:
            raise Refused(f"can't fetch {b} to check what the run would set off: {e}")
    record, errors = verify(goal_id, pr, repo_name)
    if errors:
        raise Refused("verify refused the goal: " + "; ".join(errors))
    family = builder.split("/", 1)[0].lower()
    if family in record["drafted_by"] or family == record["read_by"]:
        raise Refused(f"the builder's family {family} drafted or read the goal tests "
                      f"(drafted by {sorted(record['drafted_by'])}, read by {record['read_by']})")
    if granted_beyond(granted):
        raise Refused(f"the token holds {granted_beyond(granted)}; a goal run's token holds contents and "
                      f"pull_requests only")
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
    problems, triggers = gguard.assess(repo, base, brief, environments())    # GO-005.5
    if problems:
        raise Refused("a goal push, pull request or merge would set off more than the checks: " + "; ".join(problems))
    gguard.open_ledger(d / "ledger.jsonl", goal_id, pr, builder)               # GO-005.4
    gguard.granted(d / "ledger.jsonl", "vcs.push", f"goal/{goal_id}", [])
    create_branch(f"goal/{goal_id}", main_sha)
    budgets, cap, max_calls = gs.limits(brief)
    secs = gb.sections(brief)
    state = {"goal": goal_id, "pr": pr, "builder": builder, "tree": record["tree"], "approved_head": record["head"],
             "review_id": record["review_id"], "drafted_by": record["drafted_by"], "read_by": record["read_by"],
             "branch": f"goal/{goal_id}", "main_at_start": main_sha,
             "items": [{"n": i + 1, "title": t, "criteria": c} for i, (t, c) in enumerate(plan_items((goal / "PLAN.md").read_text()))],
             "max_items": int(secs["Max items"]), "max_rounds": int(secs["Max review rounds per item"]),
             "tests": gb.goal_tests(secs["Goal tests"], []), "done": [], "passing": [], "results": [],
             "outcome": None, "reason": None, "merge": None, "calls": [], "triggers": triggers, "spent": []}
    (d / "spend.jsonl").touch()
    save(state)
    return state


def notify(state, kind, text, trigger=None, item=None, waits=False):
    """GO-006: a digest or an escalation, written into the run's state (so the run record carries
    it) and printed by the CLI for the agent to relay to Dorian. A digest never waits; an escalation
    with waits=True holds the run until Dorian acknowledges it."""
    from datetime import datetime, timezone
    msgs = state.setdefault("messages", [])
    msgs.append({"n": len(msgs) + 1, "kind": kind, "trigger": trigger, "item": item, "text": text,
                 "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "waits": waits,
                 "status": "open" if waits else "noted", "words": None, "delivered": False})
    return msgs[-1]


def escalate(state, trigger, text, waits=False):
    return notify(state, "escalation", text, trigger=trigger, waits=waits)


def digest(state, item=None, unsure=None):
    """GO-006.1: which calls were close, what the agent is least sure of, what changed against the
    brief. Dissent is shown. It asks nothing and gates nothing."""
    close = [c for c in state.get("calls", []) if c.get("dissent")]
    lines = ["Close calls: " + ("none" if not close else
                                "; ".join(f"#{c['n']} {c['question']} ({c['status']}{', ' + c['choice'] if c['choice'] else ''})"
                                          for c in close))]
    lines += [f"  dissent on #{c['n']}: {x}" for c in close for x in c["dissent"]]
    lines.append("Least sure of: " + (unsure or "the agent didn't say"))
    ids = [t for t, _ in state["tests"]]
    d = run_dir(state["goal"])
    _, _, totals = gs.status(d / "spend.jsonl", (d / "goal" / "GOAL.md").read_text())
    lines.append(f"Against the brief: {len(state['done'])} of {len(state['items'])} items merged; "
                 f"{len(set(ids) & set(state['passing']))} of {len(ids)} goal tests passing"
                 + (f" ({', '.join(sorted(set(ids) - set(state['passing'])))} still failing)" if set(ids) - set(state["passing"]) else "")
                 + f"; spend ${totals.get('total', '?')}, {totals.get('calls', '?')} counted calls"
                 + (f"; outcome {state['outcome']}: {state['reason']}" if state["outcome"] else ""))
    head = f"Item {item} merged" if item else f"Run {state['outcome'] or 'ended'}"
    return notify(state, "digest", head + "\n" + "\n".join(lines), item=item)


def end(state, outcome, reason):
    state["outcome"], state["reason"] = outcome, reason
    last = next((r for r in reversed(state["results"]) if r.get("unsure")), {})
    digest(state, unsure=last.get("unsure"))            # GO-006.1: one at the end, whatever the outcome
    save(state)
    return {"outcome": outcome, "reason": reason}


def outbox(goal_id):
    """Messages not yet printed; printing marks them delivered. Missed ones stay in the record."""
    try:
        state = load(goal_id)
    except Refused:
        return []
    out = [m for m in state.get("messages", []) if not m["delivered"]]
    for m in out:
        m["delivered"] = True
    if out:
        save(state)
    return out


def acknowledge(goal_id, n, words):
    """Dorian's acknowledgement, in his words, of an escalation that holds the run."""
    state = load(goal_id)
    hit = [m for m in state.get("messages", []) if m["n"] == n and m["kind"] == "escalation"]
    if not hit or hit[0]["status"] != "open":
        raise Refused(f"no open escalation {n}")
    if not str(words or "").strip():
        raise Refused("record Dorian's acknowledgement in his own words")
    hit[0].update(status="acknowledged", words=words)
    save(state)
    return hit[0]


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
        escalate(state, "spend", "Spend reached its stop: " + "; ".join(reasons))
        return False, end(state, "stopped", "; ".join(reasons))
    pending = gcalls.waiting(state.get("calls", []))
    held = [m for m in state.get("messages", []) if m["kind"] == "escalation" and m["status"] == "open"]
    if pending or held:                               # GO-005.3, GO-006.2: the run waits for Dorian, it doesn't end
        return None, {"waiting": [{k: c[k] for k in ("n", "question", "options", "type", "type_reasons", "dissent")}
                                  for c in pending],
                      "escalations": [{k: m[k] for k in ("n", "trigger", "text")} for m in held]}
    ids = [t for t, _ in state["tests"]]
    if ids and set(ids) <= set(state["passing"]):
        return True, {"step": "finish", "branch": state["branch"], "spend": totals}
    remaining = [i for i in state["items"] if i["n"] not in state["done"]]
    if not remaining or len(state["done"]) >= state["max_items"]:
        failing = sorted(set(ids) - set(state["passing"]))
        return False, end(state, "exhausted", f"the plan ran out with goal tests still failing: {failing}")
    item = remaining[0]
    return True, {"step": "build", "item": item, "base_branch": state["branch"], "branch_from": f"origin/{state['branch']}",
                  "max_rounds": state["max_rounds"],
                  "ledger": str(d / "spend.jsonl"), "spend": totals}


def act(repo, goal_id, klass, resource, environments, base="origin/main", head=None, review=None, checks=None, pr=None):
    """GO-005.4 and .5 before an action the runner or a builder takes: a push, pull request or merge
    first rechecks what it would set off and stops the run if that changed since the start; then the
    ledger (or, for an item merge, DR-113's conditions) must allow it, or it's Dorian's."""
    state = load(goal_id)
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    if klass in ("vcs.push", "pr.open", "merge"):
        brief = (run_dir(goal_id) / "goal" / "GOAL.md").read_text()
        problems, now = gguard.assess(repo, base, brief, environments())
        if now != state.get("triggers"):
            end(state, "stopped", f"what a {klass} sets off changed since the run started"
                + (": " + "; ".join(problems) if problems else ""))
            raise Refused(f"the run stopped: the workflows or deployment environments changed since the start")
    if klass == "merge":
        if head is None or review is None or checks is None or pr is None:
            raise Refused("an item merge names its pull request, its head, its review and the checks at that head")
        gguard.merge_allowed(state["branch"], resource, head, review, checks, pr)
        return {"allowed": klass, "resource": resource, "by": "DR-113"}
    row = gguard.granted(run_dir(goal_id) / "ledger.jsonl", klass, resource, state["spent"])
    if row and row["scope"] == "once":
        state["spent"].append(row["id"])
        save(state)
    return {"allowed": klass, "resource": resource, "by": row and row["id"]}


def current_item(state, item):
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    remaining = [i for i in state["items"] if i["n"] not in state["done"]]
    if not remaining:
        raise Refused("no item is in progress")
    if item != remaining[0]["n"]:
        raise Refused(f"item {item} isn't the item in progress; that's item {remaining[0]['n']}")
    return remaining


def failed(goal_id, item, reason):
    """An item build that ended without a merge ends the run."""
    state = load(goal_id)
    current_item(state, item)
    if "rounds_exhausted" in reason:
        escalate(state, "review_cap", f"Item {item} reached the review cap: {reason}")
    return end(state, "stopped", f"item {item} ended without a merge: {reason}")


def merged(repo, goal_id, head, item, unsure="", review_files=()):
    """Run the goal tests at head; stop on a failing invariant or a regressed outcome."""
    state = load(goal_id)
    remaining = current_item(state, item)
    if head in {r["head"] for r in state["results"]}:
        raise Refused(f"{head[:12]} was already recorded; one merge advances one item")
    goal = run_dir(goal_id) / "goal"
    wt = tempfile.mkdtemp(prefix="goal-head-")
    ge.git(repo, "worktree", "add", "--detach", wt, head)
    try:
        results = {tid: gb.run_test(wt, goal, tid) for tid, _ in state["tests"]}
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", wt], capture_output=True)
    state["done"].append(remaining[0]["n"])
    state["results"].append({"item": remaining[0]["n"], "head": head, "results": results, "unsure": unsure,
                             "blocking_files": sorted(set(review_files))})
    kinds = dict(state["tests"])
    bad = [f"invariant {t} {r}" for t, r in results.items() if kinds[t] == "invariant" and r != "passed"]
    bad += [f"outcome {t} passed before and is now {r}" for t, r in results.items()
            if kinds[t] == "outcome" and t in state["passing"] and r != "passed"]
    state["passing"] = sorted(t for t, r in results.items() if r == "passed")
    if bad:
        escalate(state, "regression", f"Goal tests regressed at {head[:12]} after item {remaining[0]['n']}: " + "; ".join(bad))
        return end(state, "stopped", "regression at " + head[:12] + ": " + "; ".join(bad))
    digest(state, item=remaining[0]["n"], unsure=unsure)
    # ponytail: a finding's file stands in for its category, which findings don't carry
    if len(state["results"]) >= 2:
        again = sorted(set(state["results"][-1]["blocking_files"]) & set(state["results"][-2]["blocking_files"]))
        if again:
            escalate(state, "repeat_finding", f"Blocking findings in {', '.join(again)} on items "
                     f"{state['results'][-2]['item']} and {remaining[0]['n']} in a row", waits=True)
    save(state)
    return {"item": remaining[0]["n"], "results": results}


def finishing(goal_id):
    state = load(goal_id)
    ids = [t for t, _ in state["tests"]]
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    if not ids or not set(ids) <= set(state["passing"]):
        raise Refused("the finish needs every goal test passing at the last merged head")
    return state


def finalize(repo, goal_id, post, repo_name=REPO, *, environments, base="origin/main"):
    """Commit RESULT.md alone on goal-finalize/<id> from goal/<id>'s head and open its pull request."""
    state = finishing(goal_id)
    if state.get("finalize_pr"):
        raise Refused(f"the finalize pull request is already #{state['finalize_pr']}")
    branch, path = f"goal-finalize/{goal_id}", f"goal-runs/{goal_id}/RESULT.md"
    ge.git(repo, "fetch", "--no-tags", "origin", f"+refs/heads/{state['branch']}:refs/remotes/origin/{state['branch']}")
    head = ge.git(repo, "rev-parse", f"origin/{state['branch']}").strip()
    if head != state["results"][-1]["head"]:
        raise Refused(f"{state['branch']} is at {head[:12]}, not {state['results'][-1]['head'][:12]} where the goal tests passed")
    act(repo, goal_id, "vcs.push", branch, environments, base)
    act(repo, goal_id, "pr.open", f"{state['branch']}<-{branch}", environments, base)
    wt = tempfile.mkdtemp(prefix="goal-finalize-")
    ge.git(repo, "worktree", "add", "-b", branch, wt, head)
    try:
        Path(wt, path).parent.mkdir(parents=True, exist_ok=True)
        Path(wt, path).write_text(record(goal_id))
        ge.git(wt, "add", path)
        ge.git(wt, "commit", "-q", "-m", f"Run record for goal {goal_id}")
        ge.git(wt, "push", "origin", f"HEAD:refs/heads/{branch}")
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", wt], capture_output=True)
    pr = post(f"repos/{repo_name}/pulls", {"title": f"Run record for goal {goal_id}", "head": branch, "base": state["branch"],
                                           "body": f"The finalize pull request (GO-003.7): only `{path}` changes."})
    state["finalize_pr"] = pr["number"]
    save(state)
    return {"finalize_pr": pr["number"], "branch": branch}


def propose(goal_id, get, post, repo_name=REPO, *, repo, environments, base="origin/main"):
    """Open the goal pull request into main once the finalize pull request has merged into goal/<id>."""
    state = finishing(goal_id)
    if not state.get("finalize_pr"):
        raise Refused("finalize first: the goal pull request carries the run record")
    if state.get("final_pr"):
        raise Refused(f"the goal pull request is already #{state['final_pr']}")
    f = get(f"repos/{repo_name}/pulls/{state['finalize_pr']}")
    if not (f.get("merged") is True and f["base"]["ref"] == state["branch"] and f.get("merge_commit_sha")):
        raise Refused(f"finalize pull request #{state['finalize_pr']} hasn't merged into {state['branch']}")
    tested, final = state["results"][-1]["head"], f["merge_commit_sha"]
    files = [x["filename"] for x in (get(f"repos/{repo_name}/compare/{tested}...{final}") or {}).get("files", [])]
    if files != [f"goal-runs/{goal_id}/RESULT.md"]:
        raise Refused(f"between the tested head and {final[:12]}, {state['branch']} changed {files}, not only the run record")
    act(repo, goal_id, "pr.open", f"main<-{state['branch']}", environments, base)
    state = load(goal_id)
    state["finalized_head"] = final
    pr = post(f"repos/{repo_name}/pulls", {
        "title": f"Goal {goal_id}", "head": state["branch"], "base": "main",
        "body": record(goal_id) + "\nThis pull request reaches main only with goal-envelope, goal-tests and goal-holdout "
                                  "green, a fresh cross-vendor review, and Dorian's approving review at its head (GO-003.7)."})
    state["final_pr"] = pr["number"]
    save(state)
    return {"final_pr": pr["number"]}


def resync(repo, goal_id, head, base="origin/main"):
    """Rebind the goal pull request to a head that only a sync from main moved."""
    state = finishing(goal_id)
    if not (state.get("final_pr") and state.get("finalized_head")):
        raise Refused("resync applies only after propose")
    parents = ge.git(repo, "rev-list", "--parents", "-n", "1", head).split()
    record_path = f"goal-runs/{goal_id}/RESULT.md"
    if len(parents) != 3 or parents[1] != state["finalized_head"]:
        raise Refused(f"{head[:12]} isn't a merge onto the recorded head {state['finalized_head'][:12]}")
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", parents[2], base]).returncode:
        raise Refused(f"{head[:12]} merges {parents[2][:12]}, which isn't on main")
    if ge.git(repo, "diff", "--name-only", state["finalized_head"], head, "--", record_path).strip():
        raise Refused(f"{head[:12]} changes the run record")
    errors, _ = ge.check(repo, goal_id, head, base)
    if errors:
        escalate(state, "outside_envelope", f"The goal branch moved to {head[:12]} with changes outside the envelope: "
                 + "; ".join(errors))
        save(state)
        raise Refused("the envelope check refuses the new head: " + "; ".join(errors))
    state.setdefault("resyncs", []).append({"from": state["finalized_head"], "to": head})
    state["finalized_head"] = head
    save(state)
    return {"finalized_head": head}


def open_call(repo, goal_id, question, options, proposed_by, framed_by, head, base="origin/main"):
    state = load(goal_id)
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    kind, reasons = gcalls.action_type(repo, goal_id, head, base)
    commits = [sha for sha, _ in ge.goal_commits(repo, base, head)]
    try:
        call = gcalls.new_call(len(state.setdefault("calls", [])) + 1, question, options, proposed_by, framed_by,
                               kind, reasons, commits)
    except ValueError as e:
        raise Refused(str(e))
    state["calls"].append(call)
    if call["decider"] == "dorian":
        outside = any("outside the envelope" in r for r in reasons)
        escalate(state, "outside_envelope" if outside else "dorian_call",
                 f"Call #{call['n']} is Dorian's ({kind}): {question} Options: {', '.join(options)}. "
                 f"Typed by code: {'; '.join(reasons)}")
    save(state)
    return call


def _call(state, n):
    hit = [c for c in state.get("calls", []) if c["n"] == n]
    if not hit:
        raise Refused(f"no call {n}")
    return hit[0]


def council_votes(goal_id, n, votes):
    state = load(goal_id)
    try:
        call = gcalls.council(_call(state, n), votes, state["builder"])
    except ValueError as e:
        raise Refused(str(e))
    if call["status"] == "escalated":
        escalate(state, "dorian_call", f"The council split on call #{n}, {call['question']}: " + "; ".join(call["dissent"]))
    save(state)
    return call


def dorian_answers(goal_id, n, choice, words):
    state = load(goal_id)
    try:
        call = gcalls.answer(_call(state, n), choice, words)
    except ValueError as e:
        raise Refused(str(e))
    save(state)
    return call


def holdout_failed(goal_id, detail):
    state = load(goal_id)
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    escalate(state, "holdout", f"goal-holdout failed, a possible reward hack: {detail}")
    return end(state, "stopped", f"goal-holdout failed: {detail}")


def stop(goal_id, reason):
    state = load(goal_id)
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    return end(state, "stopped", reason)


def complete(goal_id, pr, merge_sha, get, repo_name=REPO):
    """Record `complete` only on GitHub's word that this goal's pull request merged into main as
    merge_sha, from goal/<id> at the head whose goal tests last passed."""
    state = load(goal_id)
    ids = [t for t, _ in state["tests"]]
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    if not ids or not set(ids) <= set(state["passing"]):
        raise Refused("complete needs every goal test passing at the last merged head")
    if not (state.get("finalize_pr") and state.get("final_pr") and state.get("finalized_head")):
        raise Refused("complete needs the finish: finalize, then propose, then the goal pull request's merge")
    if pr != state["final_pr"]:
        raise Refused(f"the goal pull request is #{state['final_pr']}, not #{pr}")
    p = get(f"repos/{repo_name}/pulls/{pr}")
    tested = state["results"][-1]["head"]
    problems = [m for ok, m in [
        (p["base"]["ref"] == "main", f"PR #{pr} targets {p['base']['ref']}, not main"),
        (p["head"]["ref"] == state["branch"], f"PR #{pr} is from {p['head']['ref']}, not {state['branch']}"),
        (p.get("merged") is True, f"PR #{pr} is not merged"),
        (p.get("merge_commit_sha") == merge_sha, f"PR #{pr} merged as {(p.get('merge_commit_sha') or 'nothing')[:12]}, not {merge_sha[:12]}"),
        (p["head"]["sha"] == state["finalized_head"],
         f"PR #{pr} merged head {p['head']['sha'][:12]}, not {state['finalized_head'][:12]}, the tested head plus the run record"),
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
    if state.get("calls"):
        lines += ["", "## Judgment calls", ""]
        for c in state["calls"]:
            lines.append(f"{c['n']}. {c['question']} ({c['type']}, decided by {c['decider']}): "
                         f"{c['choice'] or c['status']}" + (f"; Dorian: \u201c{c['words']}\u201d" if c["words"] else ""))
            lines.append(f"   - options: {', '.join(c['options'])}; proposed by {c['proposed_by']}, framed by {c['framed_by']}")
            lines.append(f"   - type by code: {'; '.join(c['type_reasons'])}")
            lines.append(f"   - commits: {', '.join(x[:12] for x in c['commits']) or 'none'}")
            lines += [f"   - vote: {v['model']} ({v['role']}): {v['choice']} - {v.get('reason', '')}" for v in c["votes"]]
            lines += [f"   - dissent: {x}" for x in c["dissent"]]
    if state.get("messages"):
        lines += ["", "## Digests and escalations", ""]
        for m in state["messages"]:
            what = m["kind"] + (f" ({m['trigger']})" if m["trigger"] else "")
            lines.append(f"{m['n']}. {m['at']} {what}" + (f", acknowledged: \u201c{m['words']}\u201d" if m["words"] else
                                                          ", waiting for Dorian" if m["status"] == "open" else ""))
            lines += [f"   {ln}" for ln in m["text"].splitlines()]
    if state["merge"]:
        lines += ["", "## Rolling back", "", "```", ge.revert_commands(state["merge"]), "```"]
    return "\n".join(lines) + "\n"


def _api(token, method, path, data):
    import urllib.request
    req = urllib.request.Request("https://api.github.com/" + path, method=method, data=json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def blocking_files(review_id):
    """Repo-relative files named by a review's blocking findings, every round, from the review
    record (the bound subject's path where there is one)."""
    rdir = os.environ.get("GSTACK_PEER_REVIEW_DIR")
    d = Path(rdir or "", review_id)
    if not rdir or not (d / "state.json").is_file():
        raise Refused(f"no review record {review_id} under GSTACK_PEER_REVIEW_DIR")
    files = set()
    for f in sorted(d.glob("round-*.json")):
        rec = json.loads(f.read_text())
        for x in rec.get("findings", []):
            if x.get("severity") == "blocking":
                s = (rec.get("subjects") or {}).get(x["id"]) or {}
                files.add(s["path"] if s.get("bound") else x["file"])
    return sorted(files)


def environments_of(get, name):
    """Every deployment environment GitHub reports for the repository: its environments and the
    environments its deployments name. A read that fails stops the caller; it never reads as none."""
    def read():
        envs = {e["name"] for e in get(f"repos/{name}/environments")["environments"]}
        return sorted(envs | {x["environment"] for x in get(f"repos/{name}/deployments?per_page=100")})
    return read


def main(argv, repo=gb.ROOT):
    rc = _main(argv, repo)
    goal_id = (argv + [None, None])[1]
    if goal_id and argv[0] not in ("record",) and ge.GOAL_ID.match(goal_id or "") and os.environ.get("GSTACK_GOAL_RUN_DIR"):
        msgs = outbox(goal_id)
        if msgs:                                      # GO-006: relay each one to Dorian
            print(json.dumps({"messages": [{k: m[k] for k in ("n", "kind", "trigger", "waits", "text")} for m in msgs]}))
    return rc


def _main(argv, repo=gb.ROOT):
    cmd, goal_id = (argv + [None, None])[:2]
    opts = dict(zip(argv[2::2], argv[3::2]))
    try:
        if cmd == "start" and goal_id and {"--pr", "--builder"} <= set(opts) <= {"--pr", "--builder", "--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token or os.environ.get("GSTACK_GOAL_RUN_TOKEN") != "1":
                raise Refused("start needs a goal-run token: run it under agent_token.py exec --goal-run --")
            name = opts.get("--repo", REPO)
            get = gb.github(token)
            perms = subprocess.run([sys.executable, str(Path(__file__).with_name("agent_token.py")), "permissions",
                                    "--goal-run", "--repo", name], capture_output=True, text=True)
            if perms.returncode:
                raise Refused(f"can't read the token's permissions: {perms.stderr.strip()[-300:]}")
            granted = dict(re.findall(r"^\s{2}(\w+)\s+(\w+)\s*$", perms.stdout, re.M))

            def create_branch(ref, sha):
                ge.git(repo, "push", "origin", f"{sha}:refs/heads/{ref}")

            start(repo, goal_id, int(opts["--pr"]), opts["--builder"],
                  lambda g, p, n: gb.verify(g, p, n, get), granted, create_branch, repo_name=name,
                  environments=environments_of(get, name))
            print(json.dumps({"started": goal_id}))
            return 0
        if cmd == "next" and goal_id and not opts:
            ok, out = next_step(repo, goal_id)
            print(json.dumps(out))
            return 0 if ok else 3 if ok is None else 1
        if cmd == "call" and goal_id and set(opts) == {"--question", "--options", "--proposed-by", "--framed-by", "--head"}:
            print(json.dumps(open_call(repo, goal_id, opts["--question"], json.loads(opts["--options"]),
                                       opts["--proposed-by"], opts["--framed-by"], opts["--head"])))
            return 0
        if cmd == "council" and goal_id and set(opts) == {"--call", "--votes"}:
            print(json.dumps(council_votes(goal_id, int(opts["--call"]), json.loads(opts["--votes"]))))
            return 0
        if cmd == "answer" and goal_id and set(opts) == {"--call", "--choice", "--words"}:
            print(json.dumps(dorian_answers(goal_id, int(opts["--call"]), opts["--choice"], opts["--words"])))
            return 0
        if cmd == "merged" and goal_id and {"--head", "--item", "--unsure"} <= set(opts) <= {"--head", "--item", "--unsure", "--review"}:
            files = blocking_files(opts["--review"]) if "--review" in opts else ()
            out = merged(repo, goal_id, opts["--head"], int(opts["--item"]), opts["--unsure"], files)
            print(json.dumps(out))
            return 1 if out.get("outcome") else 0
        if cmd == "failed" and goal_id and set(opts) == {"--item", "--reason"}:
            print(json.dumps(failed(goal_id, int(opts["--item"]), opts["--reason"])))
            return 1
        if cmd in ("finalize", "propose") and goal_id and set(opts) <= {"--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token or os.environ.get("GSTACK_GOAL_RUN_TOKEN") != "1":
                raise Refused(f"{cmd} needs a goal-run token: run it under agent_token.py exec --goal-run --")
            name = opts.get("--repo", REPO)
            post = lambda path, data: _api(token, "POST", path, data)
            get = gb.github(token)
            envs = environments_of(get, name)
            ge.git(repo, "fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
            out = (finalize(repo, goal_id, post, name, environments=envs) if cmd == "finalize"
                   else propose(goal_id, get, post, name, repo=repo, environments=envs))
            print(json.dumps(out))
            return 0
        if cmd == "may" and goal_id and {"--action", "--resource"} <= set(opts) <= {"--action", "--resource", "--head", "--review", "--pr", "--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise Refused("may needs GITHUB_TOKEN to read the deployment environments: run it under agent_token.py exec --")
            review = None
            if "--review" in opts:
                rdir = os.environ.get("GSTACK_PEER_REVIEW_DIR")
                f = Path(rdir or "", opts["--review"], "state.json")
                if not rdir or not f.is_file():
                    raise Refused(f"no review record {opts['--review']} under GSTACK_PEER_REVIEW_DIR")
                review = json.loads(f.read_text())
            ge.git(repo, "fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
            get, name = gb.github(token), opts.get("--repo", REPO)
            checks = pr = None
            if opts["--action"] == "merge" and "--head" in opts and "--pr" in opts:
                checks = gguard.latest_checks(get(f"repos/{name}/commits/{opts['--head']}/check-runs?per_page=100")["check_runs"])
                p = get(f"repos/{name}/pulls/{int(opts['--pr'])}")
                pr = {"number": p["number"], "head": p["head"]["sha"], "base_ref": p["base"]["ref"], "base": p["base"]["sha"]}
            print(json.dumps(act(repo, goal_id, opts["--action"], opts["--resource"], environments_of(get, name),
                                 head=opts.get("--head"), review=review, checks=checks, pr=pr)))
            return 0
        if cmd == "resync" and goal_id and set(opts) == {"--head"}:
            print(json.dumps(resync(repo, goal_id, opts["--head"])))
            return 0
        if cmd == "holdout-failed" and goal_id and set(opts) == {"--detail"}:
            print(json.dumps(holdout_failed(goal_id, opts["--detail"])))
            return 1
        if cmd == "ack" and goal_id and set(opts) == {"--escalation", "--words"}:
            print(json.dumps(acknowledge(goal_id, int(opts["--escalation"]), opts["--words"])))
            return 0
        if cmd == "stop" and goal_id and set(opts) == {"--reason"}:
            print(json.dumps(stop(goal_id, opts["--reason"])))
            return 1
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
