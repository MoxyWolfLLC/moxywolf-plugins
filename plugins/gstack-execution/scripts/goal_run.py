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
  goal_run.py resume <id> [--repo owner/name]
        GO-003.12: pick the delivery up from its persisted record: re-observe GitHub and the review
        records, record a merge only from GitHub's own answer, and print the next supervisor action with
        delivery_status; an unreadable budget or authority record blocks; a goal-run token is required
        the goal pull request's head moved because a sync from main merged into goal/<id>
        (GO-004.1): accepts the new head only if it merges the recorded head with a commit on main,
        keeps the run record and passes the envelope check
  goal_run.py refused <id> --pr N [--repo owner/name]
        a pull request into goal/<id> that goal-envelope refused: escalates a change outside the
        envelope (GO-006.2), quoting GitHub's own check output, not the agent's words, into the run
        record; the run holds until Dorian acknowledges it
  goal_run.py holdout-failed <id> --detail <text>
        goal-holdout failed on the goal pull request: escalates and ends the run (GO-003.6, GO-006.2)
  goal_run.py ack <id> --escalation N --words <Dorian's words>
        Dorian's acknowledgement of an escalation that holds the run; until then `next` exits 3
  Every command also prints {"messages": [...]}, when there are new ones: GO-006's digests and
  escalations, for the agent to relay to Dorian. They're kept in the run record either way.
  goal_run.py stop <id> --reason <text>
        ends a run that hasn't ended, e.g. when goal-holdout fails (a possible reward hack, GO-003.6)
  goal_run.py complete <id> --pr N --merge <sha> [--repo owner/name]
        records the goal merge once GitHub shows the goal pull request from goal/<id> merged into main
        as <sha> at the finalized head (GO-003.8); with a delivery record the run stays open and
        `resume` ends it once the release record, the companion and the checkouts are observed (GO-012.4)
  goal_run.py companion <id> --pr N --review <review id> [--repo owner/name]
        binds the declared release companion from GitHub's pull request and the review record, after the
        goal merge is recorded (GO-012.2); resume then merges, records and synchronizes it
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
import time
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
def _origin_repo():
    """owner/name of the checkout goal_run.py lives in, from origin: the governed repository (GO-008)."""
    r = subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[3]), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", r.stdout.strip())
    return m.group(1) if m else "MoxyWolfLLC/moxywolf-plugins"


REPO = _origin_repo()


def checkout_repo(repo, repo_name):
    """GO-012.1 (review F2): the governed repository is the one the supplied checkout's origin names,
    a github.com repository. `repo_name` may only agree with it. A checkout with no origin, or one
    that isn't on github.com, is refused: a label is never written in its place."""
    import goal_delivery
    r = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"], capture_output=True, text=True)
    url = r.stdout.strip() if r.returncode == 0 else ""
    # review F2 (round 3): the whole URL must be a github.com remote (goal_delivery.GITHUB_REMOTE, one home,
    # matched in full), so a local mirror path or another host that merely contains "github.com/o/r" is refused
    if not goal_delivery.github_repo(url):
        raise Refused(f"the checkout's origin {url or 'is unset and'} names no github.com repository; a goal run is "
                      "governed by the repository its checkout's origin names")
    name = goal_delivery.GITHUB_REMOTE.fullmatch(url).group(1)      # as spelled, case kept
    if repo_name and name.lower() != repo_name.lower():
        raise Refused(f"the checkout's origin is {name}, not {repo_name}; the delivery record names the checkout's repository")
    return name


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
    budgets, cap, max_calls = gs.limits(brief)
    secs = gb.sections(brief)
    state = {"goal": goal_id, "pr": pr, "builder": builder, "tree": record["tree"], "approved_head": record["head"],
             "review_id": record["review_id"], "drafted_by": record["drafted_by"], "read_by": record["read_by"],
             "branch": f"goal/{goal_id}", "main_at_start": main_sha,
             "items": [{"n": i + 1, "title": t, "criteria": c} for i, (t, c) in enumerate(plan_items((goal / "PLAN.md").read_text()))],
             "max_items": int(secs["Max items"]), "max_rounds": int(secs["Max review rounds per item"]),
             "tests": gb.goal_tests(secs["Goal tests"], []), "done": [], "passing": [], "results": [],
             "outcome": None, "reason": None, "merge": None, "calls": [], "triggers": triggers, "spent": []}
    state["delivery"] = initial_delivery(repo, checkout_repo(repo, repo_name), record, state, secs)    # GO-012.1, before any side effect
    gguard.open_ledger(d / "ledger.jsonl", goal_id, pr, builder)               # GO-005.4
    gguard.granted(d / "ledger.jsonl", "vcs.push", f"goal/{goal_id}", [])
    create_branch(f"goal/{goal_id}", main_sha)
    (d / "spend.jsonl").touch()
    save(state)
    return state


def initial_delivery(repo, repo_name, record, state, secs):
    """GO-012.1: the delivery record, written by the run that will use it, from the approval `start`
    already verified. One change, `final` (goal/<id> into main), plus the release companion when the
    brief declares one under `## Release companion` (`marketplace`, or `none`); `## Required checkouts`
    lists one checkout per line as `name path host branch`. Plan items are not repeated here: the run
    keeps them in items, done and results. Each later phase binds its own fact into `final`
    (GO-012.2): propose the finalized head and pull request, may-merge-main the review id, resume the
    merge GitHub reports."""
    def change(target, final=False):
        return {"repo": repo_name, "path": str(Path(repo).resolve()), "base": state["main_at_start"], "head": None,
                "target": target, "pr": None, "review_id": None, "final": final, "review_attempts": [],
                "original_findings": [], "merge": None, "release_record": None}
    companion = (secs.get("Release companion") or "none").strip().split()[0].lower()
    if companion not in ("none", "marketplace"):
        raise Refused(f"Release companion is {companion!r}; it is `marketplace` or `none`")
    changes = {"final": change("main", final=True)}
    if companion != "none":
        changes[companion] = change("main")
    checkouts = []
    for line in (secs.get("Required checkouts") or "").splitlines():
        parts = line.strip().lstrip("-").split()
        if not parts:
            continue
        if len(parts) != 4:
            raise Refused(f"Required checkouts line {line.strip()!r} isn't `name path host branch`")
        checkouts.append({"name": parts[0], "path": parts[1], "host": parts[2], "branch": parts[3], "repo": repo_name})
    return {"schema_version": 1, "goal": state["goal"],
            "approval": {"repo": repo_name, "pr": state["pr"], "review_id": record["review_id"], "head": record["head"],
                         "owner": gb.OWNER},
            "max_review_rounds": state["max_rounds"], "active_seconds": 0, "source_bindings": [],
            "changes": changes, "release_companion": companion if companion != "none" else None,
            "required_checkouts": checkouts}


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
    d = run_dir(state["goal"])
    stop, reasons, _ = gs.status(d / "spend.jsonl", (d / "goal" / "GOAL.md").read_text())
    if stop and not any(m["trigger"] == "spend" for m in state.get("messages", [])):
        escalate(state, "spend", "Spend reached its stop: " + "; ".join(reasons))   # whichever path ends the run
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


def held(state):
    """Open escalations that hold the run; progress refuses while there are any."""
    return [m for m in state.get("messages", []) if m["kind"] == "escalation" and m["status"] == "open"]


def refuse_if_held(state):
    h = held(state)
    if h:
        raise Refused(f"escalation {h[0]['n']} ({h[0]['trigger']}) holds the run until Dorian acknowledges it")


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
    holds = held(state)
    if pending or holds:                               # GO-005.3, GO-006.2: the run waits for Dorian, it doesn't end
        return None, {"waiting": [{k: c[k] for k in ("n", "question", "options", "type", "type_reasons", "dissent")}
                                  for c in pending],
                      "escalations": [{k: m[k] for k in ("n", "trigger", "text")} for m in holds]}
    ids = [t for t, _ in state["tests"]]
    remaining = [i for i in state["items"] if i["n"] not in state["done"]]
    capped = len(state["done"]) >= state["max_items"]
    # GO-003.3: every plan item is built, even after the goal tests pass; an item the tests don't
    # reach (cloud-review-survives' instructions) is still part of the goal Dorian approved.
    if ids and set(ids) <= set(state["passing"]) and (not remaining or capped):
        return True, {"step": "finish", "branch": state["branch"], "spend": totals}
    if not remaining or capped:
        failing = sorted(set(ids) - set(state["passing"]))
        return False, end(state, "exhausted", f"the plan ran out with goal tests still failing: {failing}")
    item = remaining[0]
    return True, {"step": "build", "item": item, "base_branch": state["branch"], "branch_from": f"origin/{state['branch']}",
                  "max_rounds": state["max_rounds"],
                  # MR-001.6: a launched builder reads the routing mode here; the tier itself comes from
                  # model_select.mjs once the item's packet exists
                  "model_routing": "route" if os.environ.get("GSTACK_MODEL_ROUTING") == "route" else "shadow",
                  "ledger": str(d / "spend.jsonl"), "spend": totals}


def act(repo, goal_id, klass, resource, environments, base="origin/main", head=None, review=None, checks=None, pr=None,
        sync=False):
    """GO-005.4 and .5 before an action the runner or a builder takes: a push, pull request or merge
    first rechecks what it would set off and stops the run if that changed since the start; then the
    ledger (or, for an item merge, DR-113's conditions) must allow it, or it's Dorian's."""
    state = load(goal_id)
    if state["outcome"]:
        raise Refused(f"the run already ended: {state['outcome']}")
    refuse_if_held(state)
    d = run_dir(goal_id)
    stop, reasons, _ = gs.status(d / "spend.jsonl", (d / "goal" / "GOAL.md").read_text())
    if stop:                                          # GO-006.2: at once, not at the next item
        escalate(state, "spend", "Spend reached its stop: " + "; ".join(reasons))
        end(state, "stopped", "; ".join(reasons))
        raise Refused("the run stopped: " + "; ".join(reasons))
    if klass in ("vcs.push", "pr.open", "merge"):
        brief = (run_dir(goal_id) / "goal" / "GOAL.md").read_text()
        problems, now = gguard.assess(repo, base, brief, environments())
        if problems or now != state.get("triggers"):   # review F2: a problem stops it even if the fingerprint held
            end(state, "stopped", f"what a {klass} sets off changed since the run started"
                + (": " + "; ".join(problems) if problems else ""))
            raise Refused(f"the run stopped: the workflows or deployment environments changed since the start")
    if klass == "merge" and sync:
        if head is None or checks is None or pr is None:
            raise Refused("a sync merge names its pull request, its head and the checks at that head")
        changed = [f for f in ge.git(repo, "diff", "--name-only", base, head).split() if f]
        tip = ge.git(repo, "rev-parse", f"{base}^{{commit}}").strip()
        parents = ge.git(repo, "rev-list", "--parents", "-n", "1", head).split()[1:]
        tree = lambda c: ge.git(repo, "rev-parse", f"{c}^{{tree}}").strip()
        if parents != [tip] or tree(head) != tree(tip):
            raise Refused(f"a sync's head is one empty commit on main's tip {tip[:12]}; {head[:12]} isn't")
        gguard.sync_allowed(state["branch"], resource, head, checks, pr, changed)
        return {"allowed": klass, "resource": resource, "by": "GO-004.1 sync"}
    if klass == "merge" and resource == state["branch"] and pr and pr.get("number") == state.get("finalize_pr"):
        if head is None or checks is None:
            raise Refused("the finalize merge names its head and the checks at that head")
        gguard.finalize_merge_allowed(state["branch"], head, state["results"][-1]["head"],
                                      [f for f in ge.git(repo, "diff", "--name-only", state["results"][-1]["head"], head).split() if f],
                                      ge.git(repo, "rev-list", "--parents", "-n", "1", head).split()[1:],
                                      {f"goal-runs/{goal_id}/RESULT.md", holdout_path(goal_id)}, checks, pr)
        return {"allowed": klass, "resource": resource, "by": "GO-003.7 finalize"}
    if klass == "merge" and resource == "main" and state.get("final_pr"):
        if head is None or review is None or checks is None or pr is None:
            raise Refused("a merge into main names its pull request, its head, its review and the checks at that head")
        companion = companion_change(state)
        if companion and companion.get("pr") is not None and pr.get("number") == companion["pr"]:
            # GO-012.2 (review F3): the declared companion's own pull request, after the goal merge is
            # recorded, under DR-113's conditions for a reviewed pull request; not the goal gate
            if not state.get("merge"):
                raise Refused("the companion merges after the goal merge is recorded")
            if head != companion.get("head") or review.get("review_id") != companion.get("review_id"):
                raise Refused(f"the companion is bound at {str(companion.get('head'))[:12]} with review {companion.get('review_id')}, "
                              f"not {str(head)[:12]} with {review.get('review_id')}")
            gguard.reviewed_merge_allowed("main", head, review, checks, pr)
            return {"allowed": klass, "resource": resource, "by": "GO-012.2 companion"}
        gguard.final_merge_allowed(release_relation(repo, goal_id, state, review, head, pr), review, checks, pr)
        bind_final(state, review_id=review.get("review_id"))     # GO-012.2: the review that allowed the merge
        return {"allowed": klass, "resource": resource, "by": "GO-011.2"}
    if klass == "merge":
        if head is None or review is None or checks is None or pr is None:
            raise Refused("an item merge names its pull request, its head, its review and the checks at that head")
        gguard.merge_allowed(state["branch"], resource, head, review, checks, pr)
        return {"allowed": klass, "resource": resource, "by": "DR-113"}
    try:
        row = gguard.granted(run_dir(goal_id) / "ledger.jsonl", klass, resource, state["spent"])
    except Refused as e:
        escalate(state, "dorian_call", f"The goal ledger refused {klass} on {resource}: {e}", waits=True)
        save(state)
        raise
    if row and row["scope"] == "once":
        state["spent"].append(row["id"])
        save(state)
    return {"allowed": klass, "resource": resource, "by": row and row["id"]}


def final_review_scope(repo, goal_id, state, review, head, pr):
    """Problems with what the whole-goal review covered (review F1): its packet (peer_review.py open
    writes packet.json with review_base = base, and fix rounds keep it; its self-test checks that)
    names every plan item
    of this goal, one repository, and a base that is where main and the goal head meet, so the
    reviewed diff is the whole goal and not one item's."""
    packet = review.get("packet") or {}
    want = {f"{goal_id}/{i['n']}" for i in state["items"]}
    problems = []
    if not want <= set(packet.get("items") or []):
        problems.append(f"the review's packet doesn't name every item of {goal_id} ({sorted(want - set(packet.get('items') or []))} missing)")
    repos = packet.get("repos") or []
    meet = subprocess.run(["git", "-C", str(repo), "merge-base", str(pr.get("base")), head], capture_output=True, text=True).stdout.strip()
    if len(repos) != 1 or not meet or repos[0].get("review_base", repos[0].get("base")) != meet:   # review F8
        problems.append(f"the review's base isn't {meet[:12] or 'where main and the goal head meet'}, so it isn't the whole goal")
    return problems


def final_review_pinned(repo, goal_id, state, review):
    """GO-011.2 and review F2: the whole-goal review's last head is the goal head without its holdout.
    Before any resync that's the head where the goal tests passed (the finalize commit's parent); once
    main has been synced in, it's a commit whose one parent is the current goal head and which only
    deletes the holdout, so whatever the sync brought is in the reviewed surface."""
    last = (review.get("heads") or [[]])[-1]
    if not state.get("resyncs"):
        return state["results"][-1]["head"] in last
    for h in last:
        p = subprocess.run(["git", "-C", str(repo), "rev-list", "--parents", "-n", "1", h], capture_output=True, text=True)
        if p.returncode or p.stdout.split()[1:] != [state["finalized_head"]]:
            continue
        d = ge.git(repo, "diff", "--name-status", state["finalized_head"], h).split("\n")
        if [x for x in d if x] == [f"D\t{holdout_path(goal_id)}"]:
            return True
    return False


def release_relation(repo, goal_id, state, review, head, pr):
    """GO-012.3: the goal pull request's release relationship, read once here for every caller: the
    pinned and whole-goal readings this module owns, judged by goal_guard.release_relationship."""
    return gguard.release_relationship(state, head, pr, final_review_pinned(repo, goal_id, state, review),
                                       final_review_scope(repo, goal_id, state, review, head, pr))


def bind_final(state, unbind=(), **facts):
    """GO-012.2: a phase binds the facts it establishes into the delivery's `final` change and saves;
    `unbind` names facts a phase withdraws (a resync withdraws the review). A run started before
    GO-012 has no record; nothing is invented for it."""
    final = ((state.get("delivery") or {}).get("changes") or {}).get("final")
    if isinstance(final, dict):
        final.update({k: v for k, v in facts.items() if v is not None})
        final.update({k: None for k in unbind})
        save(state)


def companion_change(state):
    """The declared release companion's change in the delivery record, or None."""
    delivery = state.get("delivery") or {}
    cid = delivery.get("release_companion")
    return (delivery.get("changes") or {}).get(cid) if cid else None


def bind_companion(goal_id, get, pr_number, review_id, repo_name=REPO):
    """GO-012.2 (review F3): the declared release companion is bound from GitHub's pull request and
    the review record, never from a declaration: the pull request targets main from the recorded goal
    merge onward, the review is clean at the pull request's head and of this checkout, and the goal
    merge is already recorded (the companion follows it). Writes head, base, pr and review_id into
    the companion change."""
    state = load(goal_id)
    delivery = state.get("delivery") or {}
    cid = delivery.get("release_companion")
    if not cid or cid not in (delivery.get("changes") or {}):
        raise Refused(f"{goal_id} declares no release companion")
    if not state.get("merge"):
        raise Refused("the companion follows the goal merge; run complete first")
    ch = delivery["changes"][cid]
    p = get(f"repos/{repo_name}/pulls/{int(pr_number)}")
    if not p or (p.get("base") or {}).get("ref") != "main":
        raise Refused(f"pull request #{pr_number} isn't a pull request into main")
    head, base = (p.get("head") or {}).get("sha"), (p.get("base") or {}).get("sha")
    review, _ = _review_record(review_id)
    last = (review.get("heads") or [[]])[-1]
    pk = review.get("packet") or {}
    repos = pk.get("repos") or []
    problems = [m for ok, m in [
        (review.get("outcome") in {"no_blocking_findings", "fixes_verified"}, f"review {review_id} ended {review.get('outcome')}, not clean"),
        (head in last, f"review {review_id} passed at {', '.join(h[:12] for h in last) or 'nothing'}, not the pull request's head {str(head)[:12]}"),
        (len(repos) == 1 and Path(repos[0].get("path", "")).resolve() == Path(ch.get("path") or ".").resolve(),
         f"review {review_id} is not of {ch.get('path')}"),
    ] if not ok]
    if problems:
        raise Refused("; ".join(problems))
    ch.update(head=head, base=base, pr=p.get("number"), review_id=review_id)
    save(state)
    return {"companion": cid, "pr": p.get("number"), "head": head, "base": base, "review_id": review_id}


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


SANDBOXED = True   # GO-003.11; the unit tests set it False and test the container in test_goal_checks


def merged(repo, goal_id, head, item, unsure="", review_files=()):
    """Run the goal tests at head; stop on a failing invariant or a regressed outcome."""
    state = load(goal_id)
    remaining = current_item(state, item)
    if head in {r["head"] for r in state["results"]}:
        raise Refused(f"{head[:12]} was already recorded; one merge advances one item")
    goal = run_dir(goal_id) / "goal"
    wt = tempfile.mkdtemp(prefix="goal-head-")
    ge.git(repo, "worktree", "add", "--detach", wt, head)
    trusted = tempfile.mkdtemp(prefix="goal-main-") if SANDBOXED else None
    try:
        # GO-003.11: the same container, with the candidate's dependencies, that goal-tests uses in CI
        # and baseline uses at start. On the host the worktree has no node_modules, so a test that runs
        # the candidate's `tsc` failed here and stopped no-em-dashes-2 on a regression that wasn't one.
        # The verdict script runs from main as the run started, never from the candidate: a candidate's
        # scripts/json.py beside goal_checks.py would otherwise print its own results (review F1).
        if SANDBOXED:
            ge.git(repo, "worktree", "add", "--detach", trusted, state["main_at_start"])
            run = gb.sandboxed(goal, trusted, candidate=wt)
        else:
            run = gb.run_test
        results = {tid: run(wt, goal, tid) for tid, _ in state["tests"]}
    finally:
        for d in (wt, trusted):
            if d:
                subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", d], capture_output=True)
    state["done"].append(remaining[0]["n"])
    state["results"].append({"item": remaining[0]["n"], "head": head, "results": results, "unsure": unsure,
                             "blocking_files": sorted(set(review_files))})
    kinds = dict(state["tests"])
    bad = [f"invariant {t} {r}" for t, r in results.items() if kinds[t] == "invariant" and r != "passed"]
    bad += [f"outcome {t} passed before and is now {r}" for t, r in results.items()
            if kinds[t] == "outcome" and t in state["passing"] and r != "passed"]
    state["passing"] = sorted(t for t, r in results.items() if r == "passed")
    if bad:
        digest(state, item=remaining[0]["n"], unsure=unsure)
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
    left = [i["n"] for i in state["items"] if i["n"] not in state["done"]]
    if left and len(state["done"]) < state["max_items"]:
        raise Refused(f"the finish needs every plan item built; item {left[0]} isn't")
    return state


def holdout_path(goal_id):
    return f"goal-runs/{goal_id}/holdout.py"


def holdout_source(goal_id):
    """GO-002.8: the approved holdout, read by code from GSTACK_GOAL_HOLDOUTS (default ~/.goal-holdouts) only
    when the run finishes, and only if it matches the holdout.sha256 Dorian approved with the goal. Never
    printed. Refused, naming why, when it's missing or doesn't match."""
    import hashlib
    f = Path(os.environ.get("GSTACK_GOAL_HOLDOUTS", "~/.goal-holdouts")).expanduser() / f"{goal_id}.py"
    if not f.is_file() or f.is_symlink():
        raise Refused(f"no holdout at {f}; it's drafted with the goal (goal_new.py holdout) and kept there until the run finishes")
    src = f.read_text()
    want = (run_dir(goal_id) / "goal" / "holdout.sha256").read_text().strip()
    if hashlib.sha256(src.encode()).hexdigest() != want:
        raise Refused(f"{f} doesn't match the approved holdout.sha256; nothing was committed")
    return src


def finalize(repo, goal_id, post, repo_name=REPO, *, environments, base="origin/main"):
    """Commit RESULT.md and the approved holdout on goal-finalize/<id> from goal/<id>'s head and open its pull request."""
    state = finishing(goal_id)
    if state.get("finalize_pr"):
        raise Refused(f"the finalize pull request is already #{state['finalize_pr']}")
    branch, path = f"goal-finalize/{goal_id}", f"goal-runs/{goal_id}/RESULT.md"
    ge.git(repo, "fetch", "--no-tags", "origin", f"+refs/heads/{state['branch']}:refs/remotes/origin/{state['branch']}")
    head = ge.git(repo, "rev-parse", f"origin/{state['branch']}").strip()
    if head != state["results"][-1]["head"]:
        raise Refused(f"{state['branch']} is at {head[:12]}, not {state['results'][-1]['head'][:12]} where the goal tests passed")
    hold = holdout_source(goal_id)
    act(repo, goal_id, "vcs.push", branch, environments, base)
    act(repo, goal_id, "pr.open", f"{state['branch']}<-{branch}", environments, base)
    wt = tempfile.mkdtemp(prefix="goal-finalize-")
    ge.git(repo, "worktree", "add", "-b", branch, wt, head)
    try:
        Path(wt, path).parent.mkdir(parents=True, exist_ok=True)
        Path(wt, path).write_text(record(goal_id))
        Path(wt, holdout_path(goal_id)).write_text(hold)
        ge.git(wt, "add", path, holdout_path(goal_id))
        ge.git(wt, "commit", "-q", "-m", f"Run record and holdout for goal {goal_id}")
        ge.git(wt, "push", "origin", f"HEAD:refs/heads/{branch}")
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", wt], capture_output=True)
    pr = post(f"repos/{repo_name}/pulls", {"title": f"Run record for goal {goal_id}", "head": branch, "base": state["branch"],
                                           "body": f"The finalize pull request (GO-003.7): only `{path}` and the "
                                                   f"approved holdout `{holdout_path(goal_id)}` (GO-002.8) change."})
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
    if sorted(files) != sorted([f"goal-runs/{goal_id}/RESULT.md", holdout_path(goal_id)]):
        raise Refused(f"between the tested head and {final[:12]}, {state['branch']} changed {files}, not only the run record")
    act(repo, goal_id, "pr.open", f"main<-{state['branch']}", environments, base)
    state = load(goal_id)
    state["finalized_head"] = final
    pr = post(f"repos/{repo_name}/pulls", {
        "title": f"Goal {goal_id}", "head": state["branch"], "base": "main",
        "body": record(goal_id) + "\nThis pull request reaches main only with goal-envelope, goal-tests and goal-holdout "
                                  "green and a fresh whole-goal cross-vendor review with no blocking findings; then it merges as the bot (GO-011.2)."})
    state["final_pr"] = pr["number"]
    save(state)
    bind_final(state, head=final, pr=pr["number"], base=ge.git(repo, "rev-parse", f"{base}^{{commit}}").strip())   # GO-012.2: main as the PR opened
    return {"final_pr": pr["number"]}


def from_main(repo, commit, base):
    """A commit on main, or a sync's empty commit whose one parent is on main (GO-004.1)."""
    def on_main(c):
        return subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", c, base]).returncode == 0
    if on_main(commit):
        return True
    parents = ge.git(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
    return (len(parents) == 1 and on_main(parents[0])
            and ge.git(repo, "rev-parse", f"{commit}^{{tree}}").strip() == ge.git(repo, "rev-parse", f"{parents[0]}^{{tree}}").strip())


def resync(repo, goal_id, head, base="origin/main"):
    """Rebind the goal pull request to a head that only a sync from main moved."""
    state = finishing(goal_id)
    refuse_if_held(state)
    if not (state.get("final_pr") and state.get("finalized_head")):
        raise Refused("resync applies only after propose")
    parents = ge.git(repo, "rev-list", "--parents", "-n", "1", head).split()
    record_path = f"goal-runs/{goal_id}/RESULT.md"
    if len(parents) != 3 or parents[1] != state["finalized_head"]:
        raise Refused(f"{head[:12]} isn't a merge onto the recorded head {state['finalized_head'][:12]}")
    if not from_main(repo, parents[2], base):
        raise Refused(f"{head[:12]} merges {parents[2][:12]}, which isn't on main or main's tip plus an empty commit")
    if ge.git(repo, "diff", "--name-only", state["finalized_head"], head, "--", record_path).strip():
        raise Refused(f"{head[:12]} changes the run record")
    errors, _ = ge.check(repo, goal_id, head, base)
    if errors:
        escalate(state, "outside_envelope", f"The goal branch moved to {head[:12]} with changes outside the envelope: "
                 + "; ".join(errors), waits=True)
        save(state)
        raise Refused("the envelope check refuses the new head: " + "; ".join(errors))
    state.setdefault("resyncs", []).append({"from": state["finalized_head"], "to": head})
    state["finalized_head"] = head
    save(state)
    # GO-012.2 (review F1): the delivery's final change follows the moved head; the review that passed
    # at the old head is unbound, because GO-011.2 needs a fresh review of the new head without its holdout
    bind_final(state, head=head, base=ge.git(repo, "rev-parse", f"{base}^{{commit}}").strip(), review_id=None, unbind=("review_id",))
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


def refused(goal_id, pr, get, repo_name=REPO):
    """GO-006.2's change outside the envelope, for an item pull request: escalates with goal-envelope's
    refusal quoted from its newest run at the pull request's head, reached for this pull request.
    The escalation holds the run until Dorian acknowledges it."""
    state = load(goal_id)
    p = get(f"repos/{repo_name}/pulls/{pr}")
    if p["base"]["ref"] != state["branch"]:
        raise Refused(f"PR #{pr} targets {p['base']['ref']}, not {state['branch']}")
    if pr in state.get("refusals", []):
        raise Refused(f"PR #{pr}'s refusal is already in the run record")
    head = p["head"]["sha"]
    bound = f"pr={pr};base_ref={state['branch']}"    # checks sit on the head sha, which other PRs can share
    # filter=all: GitHub's default lists only the newest run of a name, which may be another PR's.
    # ponytail: one page of 100 goal-envelope runs on one head; page if a head ever carries more.
    runs = [r for r in get(f"repos/{repo_name}/commits/{head}/check-runs?check_name=goal-envelope&filter=all&per_page=100")["check_runs"]
            if r["name"] == "goal-envelope" and (r.get("external_id") or "").split(";base=")[0] == bound]
    run = max(runs, key=lambda r: r["id"], default=None)
    if not run:
        raise Refused(f"no goal-envelope run for PR #{pr} into {state['branch']} at {head[:12]}")
    if run.get("status") != "completed" or run.get("conclusion") != "failure":
        raise Refused(f"goal-envelope didn't refuse PR #{pr} at {head[:12]}: {run.get('conclusion') or run.get('status')}")
    out = run.get("output") or {}
    escalate(state, "outside_envelope", f"PR #{pr} ({p.get('title', '')}) at {head[:12]}, refused by goal-envelope: "
           f"{out.get('title', '')}\n{out.get('summary', '')}".rstrip(), waits=True)
    state.setdefault("refusals", []).append(pr)
    save(state)
    return {"refused": pr, "check": run["id"]}


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
    p = get(f"repos/{repo_name}/pulls/{pr}")
    final = ((state.get("delivery") or {}).get("changes") or {}).get("final") or {}
    review = _review_record(final.get("review_id"))[0] if final.get("review_id") else None
    if review is None:
        raise Refused("complete needs the goal merge's review bound in the delivery record; `may merge main` binds it")
    # GO-012.3: the same relationship the merge gate read, not a second comparison
    relation = release_relation(Path(final.get("path") or "."), goal_id, state, review, p["head"]["sha"],
                                {"number": pr, "base": (p.get("base") or {}).get("sha")})
    problems = list(relation["problems"]) + [m for ok, m in [
        (p["base"]["ref"] == "main", f"PR #{pr} targets {p['base']['ref']}, not main"),
        (p["head"]["ref"] == state["branch"], f"PR #{pr} is from {p['head']['ref']}, not {state['branch']}"),
        (p.get("merged") is True, f"PR #{pr} is not merged"),
        (p.get("merge_commit_sha") == merge_sha, f"PR #{pr} merged as {(p.get('merge_commit_sha') or 'nothing')[:12]}, not {merge_sha[:12]}"),
    ] if not ok]
    if problems:
        raise Refused("; ".join(problems))
    state["merge"], state["final_pr"] = merge_sha, pr
    if isinstance(state.get("delivery"), dict):
        # GO-011.8 / GO-012.4: the goal merge is recorded here, and only resume ends the run, once the
        # release record, the release companion and every required checkout are observed complete
        import goal_delivery as gd
        save(state)
        return {"merge_recorded": merge_sha, "pr": pr, **gd.delivery_status(state["delivery"])}
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
    dl = state.get("delivery")
    if isinstance(dl, dict):                            # GO-011.8: merge, record and sync, each on its own line
        lines += ["", "## Delivery", ""]
        for cid, ch in (dl.get("changes") or {}).items():
            m, r = ch.get("merge") or {}, ch.get("release_record") or {}
            lines.append(f"- {cid} (PR #{ch.get('pr')} into {ch.get('target')}"
                         + (", release companion" if cid == dl.get("release_companion") else "") + ")")
            lines.append(f"  - merge: " + (f"verified, {str(m.get('sha'))[:12]} from {m.get('observed_from')}" if m.get("verified")
                                           else "contradicted by GitHub" if m.get("contradicted") else
                                           "requested, not yet observed" if ch.get("merge_requested") else "not merged"))
            lines.append(f"  - release record: " + (f"{r.get('outcome') or 'recorded'}, {r.get('path')}" if r.get("verified") else "not recorded"))
        for spec in dl.get("required_checkouts") or ():
            s = spec.get("sync") or {}
            lines.append(f"- checkout {spec.get('name')} ({spec.get('path')}), as last recorded, not a fresh observation: "
                         + (f"synced at {str(s.get('sha'))[:12]}" if s.get("status") == "synced"
                            else f"{s.get('status')}: {s.get('reason')}" if s else "not synchronized"))
    if state["merge"]:
        lines += ["", "## Rolling back", "", "```", ge.revert_commands(state["merge"]), "```"]
    return "\n".join(lines) + "\n"


GITHUB_API = os.environ.get("GSTACK_GITHUB_API", "https://api.github.com").rstrip("/")


def _github_get(token):
    """A reader of GitHub for the delivery: the configured API base (GSTACK_GITHUB_API, so a fixture
    can stand in), 404 as None, any other failure raised, never read as an answer."""
    import urllib.request, urllib.error
    def get(path):
        req = urllib.request.Request(f"{GITHUB_API}/{path}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
    return get


def observe(delivery, get, repo_name):
    """What the delivery can see right now, read from GitHub and the review records, never from a
    declaration, keyed by change id (review F5: two repositories may share a pull request number or
    a commit). A review is observed with the repository and head it passed at (review F2). A read
    that fails is reported as unobserved, not as false."""
    observed = {"prs": {}, "checks": {}, "reviews": {}, "checkouts": {}, "errors": []}
    rdir = os.environ.get("GSTACK_PEER_REVIEW_DIR")
    for cid, ch in (delivery.get("changes") or {}).items():
        name = ch.get("repo") or repo_name
        try:
            pr = get(f"repos/{name}/pulls/{ch['pr']}")
            if pr is not None:
                observed["prs"][cid] = pr
            runs = get(f"repos/{name}/commits/{ch['head']}/check-runs") or {}
            observed["checks"][cid] = gguard.latest_checks(runs.get("check_runs") or [])   # repair 2: (conclusion, binding)
        except Exception as e:   # the observation failed; next_action sees nothing, which is pending
            observed["errors"].append(f"{cid}: {type(e).__name__}: {e}")
        if rdir and ch.get("review_id"):
            observed["reviews"][cid] = review_evidence(Path(rdir, ch["review_id"]), ch, observed["errors"], cid)
    return observed


def _observe_checkouts(delivery, observed, repo_name=None):
    """Repair 5: each required checkout is read as it is now (goal_delivery.observe_checkout); a saved
    synced record is history, not an observation. Repair 8: against every verified merge of its own
    repository into its branch (goal_delivery.required_merges), never another repository's, never only
    the newest. A checkout that can't be bound to a repository is pending, with the reason."""
    import goal_delivery as gd
    for spec in delivery.get("required_checkouts") or ():
        try:
            merges = gd.required_merges(delivery, spec, repo_name)
        except gd.Blocked as e:
            observed["checkouts"][spec["name"]] = {"status": "sync_pending", "name": spec["name"], "reason": str(e)}
            continue
        if merges:
            observed["checkouts"][spec["name"]] = gd.observe_checkout(spec, merges)


def _observe_finalized(goal_id, state, delivery, observed):
    """GO-012.3: for the goal pull request's change (`final`), the release relationship as the merge
    gate reads it (release_relation), judged against the observed pull request. next_action reads
    this instead of the exact-head rule, for that change only; the comparison isn't restated here."""
    for cid, ch in (delivery.get("changes") or {}).items():
        ev = (observed.get("reviews") or {}).get(cid)
        if not ch.get("final") or not isinstance(ev, dict):
            continue
        try:
            review, _ = _review_record(ch.get("review_id"))
            seen = (observed.get("prs") or {}).get(cid) or {}
            prd = {"number": seen.get("number", ch.get("pr")), "base": (seen.get("base") or {}).get("sha")}   # act's shape
            ev["finalized"] = release_relation(Path(ch.get("path") or "."), goal_id, state, review, ch.get("head"), prd)
        except (Refused, KeyError, IndexError, ValueError, OSError) as e:
            ev["finalized"] = {"ok": False, "finalized_head": state.get("finalized_head"), "problems": [f"{type(e).__name__}: {e}"]}


def review_evidence(d, ch, errors, cid):
    """What a review record says about THIS change's repository (review F2, F8): its outcome, the
    head it passed at and the base it reviewed from, read at the index of the change's repository
    in the retained packet. A record with no packet, no matching repository or an ambiguous match
    is incomplete evidence, and says so, rather than defaulting to the first repository."""
    if not (d / "state.json").is_file():
        return None
    try:
        st = json.loads((d / "state.json").read_text())
        pk = json.loads((d / "packet.json").read_text()) if (d / "packet.json").is_file() else None
    except ValueError:
        errors.append(f"{cid}: review record {d.name} unreadable")
        return {"outcome": None, "review_id": d.name, "incomplete": "unreadable"}
    out = {"outcome": st.get("outcome"), "review_id": d.name}
    if not pk or not pk.get("repos"):
        return dict(out, incomplete="the review record has no packet, so its repository and range are unknown")
    want = Path(ch.get("path") or "").resolve() if ch.get("path") else None
    matches = [i for i, r in enumerate(pk["repos"]) if want is not None and Path(r.get("path", "")).resolve() == want]
    if len(matches) != 1:
        return dict(out, incomplete=f"{len(matches)} of the review's {len(pk['repos'])} repositories match {ch.get('path')}")
    i = matches[0]; r = pk["repos"][i]; heads = st.get("heads") or []
    head = heads[-1][i] if heads and i < len(heads[-1]) else r.get("head")
    return dict(out, head=head, base=r.get("review_base") or r.get("base"), repo=r.get("path"))


def establish_authority(goal_id, state, delivery, get, repo_name):
    """Review F1: the delivery acts under one approval and one ledger, and resume establishes both
    before anything else. The embedded approval must be the run's (same pull request, review id,
    approved head), GitHub must still show that review as APPROVED by the owner at that head, the
    goal ledger must grant pushes to the goal branch, and the spend ledger must be under its stops.
    Anything that can't be read or doesn't agree blocks; nothing defaults."""
    d = run_dir(goal_id)
    approval = delivery.get("approval") or {}
    for key, mine in (("pr", state.get("pr")), ("review_id", state.get("review_id")), ("head", state.get("approved_head"))):
        if approval.get(key) != mine:
            raise Refused(f"the delivery's approval {key} ({approval.get(key)}) is not this run's ({mine}); authority not established")
    name = approval.get("repo") or repo_name
    try:
        review = get(f"repos/{name}/pulls/{approval['pr']}/reviews/{approval['review_id']}")
    except Exception as e:
        raise Refused(f"the approval could not be read from GitHub ({type(e).__name__}: {e}); authority not established")
    if not review or review.get("state") != "APPROVED" or review.get("commit_id") != approval["head"]             or (review.get("user") or {}).get("login") != approval.get("owner"):
        raise Refused(f"GitHub does not show review {approval['review_id']} on #{approval['pr']} as APPROVED by "
                      f"{approval.get('owner')} at {str(approval['head'])[:12]}; authority not established")
    try:
        gguard.granted(d / "ledger.jsonl", "vcs.push", state.get("branch") or f"goal/{goal_id}", state.get("spent") or [])
    except Refused as e:
        raise Refused(f"the goal ledger grants no push to the goal branch ({e}); authority not established")
    brief = d / "goal" / "GOAL.md"
    if not brief.is_file():
        raise Refused("the run's copy of GOAL.md is missing; the budget cannot be read")
    stop, reasons, totals = gs.status(d / "spend.jsonl", brief.read_text())
    if stop:
        raise Refused("the budget blocks: " + "; ".join(reasons))
    return {"approval": {"review": review.get("id"), "state": review.get("state"), "commit_id": review.get("commit_id"),
                         "by": (review.get("user") or {}).get("login")}, "spend": totals}


def _mark_merges(delivery, observed, repo_name):
    """A merge is verified only by GitHub's own answer about THIS change's pull request, repository
    and target (repair 1), and unmarked when GitHub contradicts it."""
    import goal_delivery as gd
    for cid, ch in delivery["changes"].items():
        pr = observed["prs"].get(cid)
        if pr is None:
            continue
        if gd.merged_here(ch, pr):
            if not (ch.get("merge") or {}).get("verified"):
                ch["merge"] = {"verified": True, "head": ch["head"], "sha": pr.get("merge_commit_sha"),
                               "merged_by": (pr.get("merged_by") or {}).get("login"), "merged_at": pr.get("merged_at"),
                               "observed_from": f"{GITHUB_API}/repos/{ch.get('repo') or repo_name}/pulls/{ch['pr']}"}
        elif (ch.get("merge") or {}).get("verified"):
            # review F3: GitHub contradicts the record; the record loses, and says so
            ch["merge"] = {"verified": False, "contradicted": True, "was": ch["merge"],
                           "observed": {"merged": pr.get("merged"), "head": pr.get("head", {}).get("sha")}}


def _review_record(review_id):
    rdir = os.environ.get("GSTACK_PEER_REVIEW_DIR")
    f = Path(rdir or "", review_id or "", "state.json")
    if not rdir or not review_id or not f.is_file():
        raise Refused(f"no review record {review_id} under GSTACK_PEER_REVIEW_DIR")
    review = json.loads(f.read_text())
    pk = f.with_name("packet.json")
    review["packet"] = json.loads(pk.read_text()) if pk.is_file() else None
    return review, f.parent


AUTHORIZED_RELEASE = {"human_merge_recorded", "agent_merge_on_instruction", "agent_merge_autonomous"}


def _execute(goal_id, state, action, observed, get, put, repo_name):
    """GO-003.12 / GO-011.8: carry out the one allowed delivery action through the existing gates.
    Returns (state, stop): stop is a reason the loop ends without another action. A merge goes
    through act() (the same gate `may merge` uses), is persisted as requested before the request is
    sent, and is requested once per observation that GitHub has not merged it; a lost response is
    found by the next observation, never answered with a second request. record-release only reads
    GitHub (peer_review.py), and an existing record of this merge is reused, not rewritten."""
    import goal_delivery as gd
    delivery = state["delivery"]
    kind = action.get("action")
    if kind == "merge":
        cid = action["change"]; ch = delivery["changes"][cid]; name = ch.get("repo") or repo_name
        pr = observed["prs"][cid]
        review, _ = _review_record(ch.get("review_id"))
        runs = get(f"repos/{name}/commits/{ch['head']}/check-runs?per_page=100") or {}
        checks = gguard.latest_checks(runs.get("check_runs") or [])
        prd = {"number": pr["number"], "head": pr["head"]["sha"], "base_ref": pr["base"]["ref"], "base": pr["base"]["sha"]}
        save(state)
        act(Path(ch.get("path") or "."), goal_id, "merge", ch["target"], environments_of(get, name),
            base=prd["base"], head=ch["head"], review=review, checks=checks, pr=prd)
        state = load(goal_id); delivery = state["delivery"]; ch = delivery["changes"][cid]
        ch["merge_requested"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "head": ch["head"], "pr": ch["pr"]}
        save(state)
        try:
            put(f"repos/{name}/pulls/{ch['pr']}/merge", {"sha": ch["head"], "merge_method": "merge"})
        except Exception as e:   # the answer is GitHub's next observation, not this response
            ch["merge_requested"]["response"] = f"{type(e).__name__}: {e}"
            save(state)
        return state, None
    if kind == "record_release":
        cid = action["change"]; ch = delivery["changes"][cid]; name = ch.get("repo") or repo_name
        _, rdir = _review_record(ch.get("review_id"))
        f = rdir / f"release-{name.replace('/', '-')}-{ch['pr']}.json"
        if not f.is_file():
            p = subprocess.run([sys.executable, str(Path(__file__).with_name("peer_review.py")), "record-release",
                                ch["review_id"], "--repo", str(ch.get("path") or "."), "--pr", str(ch["pr"])],
                               capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
            if p.returncode or not f.is_file():
                return state, f"record-release for {cid} refused: {(p.stderr or p.stdout).strip()[-300:]}"
        rec = json.loads(f.read_text())
        merge = ch.get("merge") or {}
        if rec.get("head") != ch["head"] or (merge.get("sha") and rec.get("merge_commit") != merge["sha"]):
            return state, f"{f.name} records {str(rec.get('head'))[:12]} merged as {str(rec.get('merge_commit'))[:12]}, not this change's merge"
        # review F3 (20261027-124210): a record speaks for this change only when it is this change's review
        # and repository and its outcome is an authorized merge; an out-of-lane record is kept, and blocks
        if rec.get("review_id") != ch.get("review_id") or rec.get("repo") != name:
            return state, f"{f.name} is the record of review {rec.get('review_id')} in {rec.get('repo')}, not {ch.get('review_id')} in {name}"
        if rec.get("outcome") not in AUTHORIZED_RELEASE:
            return state, f"{f.name} records {rec.get('outcome')!r}, not an authorized merge; it is kept unchanged and delivery stops here"
        ch["release_record"] = {"verified": True, "path": str(f), "merge_commit": rec.get("merge_commit"), "outcome": rec.get("outcome")}
        save(state)
        return state, None
    if kind == "sync_checkout":
        spec = next(s for s in delivery.get("required_checkouts") or () if s.get("name") == action["checkout"])
        try:
            merges = gd.required_merges(delivery, spec, repo_name)   # repair 8: this repository's, all of them
        except gd.Blocked as e:
            return state, str(e)
        if not merges:
            return state, f"no verified merge of {spec.get('repo') or spec.get('remote')} into {spec.get('branch') or 'main'} to synchronize {spec.get('name')} to"
        spec["sync"] = gd.sync_checkout(spec, merges)
        save(state)
        return state, None if spec["sync"]["status"] == "synced" else spec["sync"]["reason"]
    return state, None


def resume(goal_id, get, repo_name, put=None):
    """GO-003.12: pick the delivery up from its persisted record. Loads the run state, establishes
    the approval and the ledgers (readable and meaning what they must), re-observes GitHub and the
    local prerequisites, records what was observed into the delivery, and saves. Without `put` it
    returns the next supervisor action and executes nothing. With `put` (the CLI's GitHub writer) it
    carries out each allowed action in turn, re-observing after each, until the delivery is
    complete, pending, blocked or stopped; when it is complete the run ends complete with the goal
    merge recorded (GO-011.8)."""
    import goal_delivery as gd
    state = load(goal_id)
    delivery = state.get("delivery")
    if not isinstance(delivery, dict):
        raise Refused(f"{goal_id} has no delivery record to resume")
    d = run_dir(goal_id)
    for required in ("spend.jsonl", "ledger.jsonl"):
        f = d / required
        if not f.is_file():
            raise Refused(f"{required} is missing: an unreadable budget or authority record blocks further action")
        try:
            [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        except ValueError as e:
            raise Refused(f"{required} is unreadable ({e}): the budget or authority record blocks further action")
    authority = establish_authority(goal_id, state, delivery, get, repo_name)
    refused = (f"the run has ended ({state['outcome']})" if state.get("outcome")
               else f"escalation {held(state)[0]['n']} holds the run until Dorian acknowledges it" if held(state) else None)
    if refused:
        # Repair 3: an ended or held run advances nothing: no merge, release record or sync, and
        # its persisted delivery state is left exactly as it is. It can still be read.
        observed = observe(delivery, get, repo_name)
        _mark_merges(delivery, observed, repo_name); _observe_checkouts(delivery, observed, repo_name)
        _observe_finalized(goal_id, state, delivery, observed)
        status, decision = gd.delivery_status(delivery, observed), gd.next_action(delivery, observed)
        if decision.get("action") != "complete" and status["delivery_status"] == "complete":
            status = dict(status, delivery_status="in_progress",
                          missing=[decision.get("pending") or decision.get("blocked") or f"next action {decision.get('action')}"])
        return {"goal": goal_id, "next": decision, **status, "executed": [], "stopped_by": None,
                "refused": refused, "observation_errors": observed["errors"]}
    stop, steps, requested = None, [], set()
    for _ in range(12):   # ponytail: each pass is one action; a delivery has a handful
        observed = observe(delivery, get, repo_name)
        _mark_merges(delivery, observed, repo_name)
        _observe_checkouts(delivery, observed, repo_name)
        _observe_finalized(goal_id, state, delivery, observed)
        action = gd.next_action(delivery, observed)
        status = gd.delivery_status(delivery, observed)
        state["delivery"] = delivery
        save(state)
        if put is None or "action" not in action or action["action"] == "complete" or stop:
            break
        if action["action"] == "merge" and action["change"] in requested:
            # one request per change per process: GitHub still showing it unmerged is an answer to
            # read again later, never a reason to ask twice (a lost response looks exactly like this)
            stop = f"merge of {action['change']} was requested and GitHub doesn't show it merged yet; resume again to re-observe"
            break
        earlier = delivery["changes"][action["change"]].get("merge_requested") if action["action"] == "merge" else None
        if earlier and earlier.get("head") == delivery["changes"][action["change"]]["head"]:
            # Repair 4: a request an earlier process persisted (it may have died mid-request, or lost the
            # answer) is never sent again automatically; GitHub's next observation answers it
            stop = (f"a merge of {action['change']} at {earlier['head'][:12]} was requested by an earlier process at "
                    f"{earlier.get('at')} and GitHub doesn't show it merged; it is not sent again. Re-observe, or Dorian decides")
            break
        if action["action"] == "merge":
            requested.add(action["change"])
        state, stop = _execute(goal_id, state, action, observed, get, put, repo_name)
        delivery = state["delivery"]
        steps.append({k: action.get(k) for k in ("action", "change", "checkout") if action.get(k)})
    if action.get("action") != "complete" and status["delivery_status"] == "complete":
        # review F2 (20261027-124210): the decision governs; saved records don't make a pending one complete
        status = dict(status, delivery_status="in_progress",
                      missing=[action.get("pending") or action.get("blocked") or f"next action {action.get('action')}"])
    if put is not None and action.get("action") == "complete" and status["delivery_status"] == "complete" and not state.get("outcome"):
        final = next((c for c in delivery["changes"].values() if c.get("pr") == state.get("final_pr")), None)
        if final and (final.get("merge") or {}).get("verified"):
            state["merge"] = final["merge"]["sha"]
            end(state, "complete", f"PR #{final['pr']} merged to main in {final['merge']['sha'][:12]}; "
                                   "release recorded and required checkouts synchronized")
            state = load(goal_id); delivery = state["delivery"]
    delivery["last_observed"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "errors": observed["errors"],
                                 "authority": authority, "next": action, "delivery_status": status["delivery_status"],
                                 "steps": steps, "stopped_by": stop}
    state["delivery"] = delivery
    save(state)
    return {"goal": goal_id, "next": action, **status, "executed": steps, "stopped_by": stop,
            "observation_errors": observed["errors"]}


def _api(token, method, path, data):
    import urllib.request
    req = urllib.request.Request(f"{GITHUB_API}/" + path, method=method, data=json.dumps(data).encode(),
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
        envs, deps = get(f"repos/{name}/environments"), get(f"repos/{name}/deployments?per_page=100")
        if not isinstance(envs, dict) or not isinstance(deps, list):   # a 404 or an odd answer is unread, never none
            raise Refused(f"can't read {name}'s deployment environments; the gate can't assess what a merge sets off")
        return sorted({e["name"] for e in envs.get("environments") or []} | {x["environment"] for x in deps})
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
        if cmd == "companion" and goal_id and {"--pr", "--review"} <= set(opts) <= {"--pr", "--review", "--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise Refused("companion needs GITHUB_TOKEN to read the pull request: run it under agent_token.py exec --")
            print(json.dumps(bind_companion(goal_id, gb.github(token), int(opts["--pr"]), opts["--review"], opts.get("--repo", REPO))))
            return 0
        if cmd == "resume" and goal_id and set(opts) <= {"--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token or os.environ.get("GSTACK_GOAL_RUN_TOKEN") != "1":
                raise Refused("resume needs a goal-run token: run it under agent_token.py exec --goal-run --")
            out = resume(goal_id, _github_get(token), opts.get("--repo", REPO),
                         put=lambda path, data: _api(token, "PUT", path, data))
            print(json.dumps(out, indent=1))
            return 0 if out.get("delivery_status") == "complete" or ("action" in out.get("next", {}) and not out.get("refused")) else 3
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
        if cmd == "may" and goal_id and {"--action", "--resource"} <= set(opts) <= {"--action", "--resource", "--head", "--review", "--pr", "--repo", "--sync"}:
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
                pk = f.with_name("packet.json")
                review["packet"] = json.loads(pk.read_text()) if pk.is_file() else None
            ge.git(repo, "fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
            get, name = gb.github(token), opts.get("--repo", REPO)
            checks = pr = None
            if opts["--action"] == "merge" and "--head" in opts and "--pr" in opts:
                checks = gguard.latest_checks(get(f"repos/{name}/commits/{opts['--head']}/check-runs?per_page=100")["check_runs"])
                p = get(f"repos/{name}/pulls/{int(opts['--pr'])}")
                pr = {"number": p["number"], "head": p["head"]["sha"], "base_ref": p["base"]["ref"], "base": p["base"]["sha"]}
                ge.git(repo, "fetch", "--no-tags", "origin", f"+refs/pull/{pr['number']}/head:refs/remotes/origin/pr/{pr['number']}")
            print(json.dumps(act(repo, goal_id, opts["--action"], opts["--resource"], environments_of(get, name),
                                 head=opts.get("--head"), review=review, checks=checks, pr=pr, sync="--sync" in opts)))
            return 0
        if cmd == "resync" and goal_id and set(opts) == {"--head"}:
            print(json.dumps(resync(repo, goal_id, opts["--head"])))
            return 0
        if cmd == "refused" and goal_id and {"--pr"} <= set(opts) <= {"--pr", "--repo"}:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise Refused("refused needs GITHUB_TOKEN: run it under agent_token.py exec --")
            print(json.dumps(refused(goal_id, int(opts["--pr"]), gb.github(token), opts.get("--repo", REPO))))
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
