"""GO-005 criteria 4 and 5: the ledger a goal run acts under, and what its pushes, pull requests and
merges would set off.

The ledger is attention, not containment (DESIGN.md, Constraints): it's written by the agent it
governs, so a refusal here sends an action to Dorian, and GitHub's rulesets and the app's
permissions are what actually hold. The trigger check reads the workflows on main and the
deployment environments GitHub reports; a deployment wired up somewhere GitHub doesn't report it
(an app that deploys on push without an environment) is outside what it can see.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import goal_brief as gb
import goal_envelope as ge
import governance as gov

# The repository's checks and the goal checks, pinned to the content reviewed as checks and nothing
# else. A file name proves nothing about what a workflow does; a changed check is a new workflow
# until this pin moves with it, in a change Dorian approves (this file is a CODEOWNERS path), and
# test_goal_guard fails CI while a pin and its workflow disagree.
CHECKS = {
    "tests.yml": "3d665e3dca8e37afacf7775e278eef9692f5d67896c29946b90eb73191a256b2",
    "goal-envelope.yml": "03c4d6e7e6ee8a5aca467cbea7899b22f1a00b1cae72d36b0d65bbfe412823d5",
    "goal-tests.yml": "27bfd7ad9b61ee9cb491ee5abee6b9b8899af7a616ea851da7c92004900460a5",
    "goal-holdout.yml": "76ab3029baef7a5b42911dcd9eb0071992260c79fe71a328ba926a2e1192f21b",
}
CHECK_ENVS = {"goal-holdout"}
# Any of these anywhere in a workflow counts as a trigger. ponytail: `git push` in a step counts
# too, which refuses on the safe side; a real parse is the upgrade if that ever bites.
EVENTS = re.compile(r"\b(push|pull_request_target|pull_request|workflow_run|merge_group)\b")
ENV_USE = re.compile(r"^\s*environment:\s*(?:\n\s*name:\s*)?['\"]?([\w.-]+)", re.M)
INLINE_BRANCHES = re.compile(r"branches:\s*\[([^\]]*)\]")
BLOCK_BRANCHES = re.compile(r"branches:\s*\n((?:[ \t]*-[^\n]*\n?)+)")
# Hosts each reviewer reaches: OpenRouter for the openrouter transport, the vendor for a CLI.
CLI_HOSTS = {"gpt": ["api.openai.com", "chatgpt.com"], "claude": ["api.anthropic.com"],
             "gemini": ["generativelanguage.googleapis.com"]}


class Refused(Exception):
    pass


# --- criterion 4: the goal ledger ---------------------------------------------------------

def reviewers(builder):
    """[(tool, model, family, hosts)] for every configured reviewer outside the builder's family."""
    import peer_review
    import goal_calls
    fam = goal_calls.family(builder)
    out = []
    for name, cfg in peer_review.REVIEWERS.items():
        if cfg["family"] == fam:
            continue
        hosts = ["openrouter.ai"] if cfg["transport"] == "openrouter" else CLI_HOSTS.get(cfg["family"], [])
        out.append((name, cfg["model"], cfg["family"], hosts))
    return out


def open_ledger(path, goal_id, pr, builder):
    """The grants a run of goal_id acts under. merge is never granted: it's ONE_SHOT_ONLY, and an
    item merge into goal/<id> rests on DR-113 (merge_allowed), not on the ledger."""
    who = f"Dorian, approving goal {goal_id} in PR #{pr}"
    rows = [("vcs.push", f"goal/{goal_id}", "project"), ("vcs.push", "build/*", "project"),
            ("vcs.push", f"goal-finalize/{goal_id}", "project"),
            ("pr.open", f"goal/{goal_id}<-*", "project"), ("pr.open", f"main<-goal/{goal_id}", "once")]
    for tool, model, _, hosts in reviewers(builder):
        rows += [("review.send_code", tool, "project"), ("external.model_call", model, "project")]
        rows += [("net.connect", h, "project") for h in hosts]
    Path(path).unlink(missing_ok=True)
    return [gov.grant(path, k, r, who, scope=s) for k, r, s in rows]


def granted(path, klass, resource, spent):
    """The grant row for this action, or Refused naming it as Dorian's. A once grant is spent by
    using it: the caller records the returned row's id in `spent`."""
    if klass == "merge":
        raise Refused("merge is never granted by the goal ledger (ONE_SHOT_ONLY); an item merge into the "
                      "goal branch goes through merge_allowed")
    if klass == "net.connect":
        try:
            gov.check_egress({"data_use": {"destinations": []}}, [resource], ledger=path)
        except gov.MissingGrantError as e:
            raise Refused(f"{e}; that's Dorian's call")
        return gov.resolve(path, klass, gov.destination_host(resource))
    if klass not in gov.GRANT_CLASSES:
        raise Refused(f"unknown action class {klass}")
    row = gov.resolve(path, klass, resource, consume=spent)
    if not row:
        raise Refused(f"the goal ledger doesn't grant {klass} on {resource}; that's Dorian's call")
    return row


def merge_allowed(branch, target, head, review):
    """DR-113 for an item: into the goal branch only, pinned to head, after a clean cross-vendor
    review at that head with coverage checked. `review` is the review's state.json."""
    if target != branch:
        raise Refused(f"an item merges into {branch}, not {target}; the merge into main is the goal pull "
                      f"request's, with Dorian's approval (GO-003.7)")
    problems = [m for ok, m in [
        (review.get("outcome") in {"no_blocking_findings", "fixes_verified"},
         f"the review ended {review.get('outcome')}, not clean"),
        (review.get("coverage_checked") is True and review.get("coverage_status") == "covered"
         and not review.get("coverage_overridden"), "the review's coverage wasn't checked and covered"),
        (any(head in hs for hs in (review.get("heads") or [])[-1:]), f"the review's last head isn't {head[:12]}"),
    ] if not ok]
    if problems:
        raise Refused("; ".join(problems))


# --- criterion 5: what a push, pull request or merge would set off --------------------------

def workflows(repo, ref):
    """{name: text} for every workflow file on ref."""
    out = subprocess.run(["git", "-C", str(repo), "ls-tree", "--name-only", f"{ref}:.github/workflows/"],
                         capture_output=True, text=True).stdout.split()
    return {n: ge.at(repo, ref, f".github/workflows/{n}") or "" for n in out if n.endswith((".yml", ".yaml"))}


def main_only(text, events):
    """A workflow that runs only on a push to main: its deploy is the goal pull request's merge."""
    names = [b.strip().strip("'\"") for m in INLINE_BRANCHES.findall(text) for b in m.split(",")]
    names += [ln.strip()[1:].strip().strip("'\"") for m in BLOCK_BRANCHES.findall(text) for ln in m.splitlines() if ln.strip()]
    return events == {"push"} and bool(names) and set(names) == {"main"}


def assess(repo, ref, brief, environments):
    """(problems, fingerprint). A problem is a workflow or deployment environment that a goal push,
    pull request or merge would set off beyond the repository's checks, unless it runs only on a
    push to main and the brief's Stop conditions name it as Dorian's call. The fingerprint covers
    everything that triggers, so any change to it mid-run is seen."""
    stops = gb.sections(brief).get("Stop conditions", "")
    problems, seen = [], {}
    for name, text in sorted(workflows(repo, ref).items()):
        events = set(EVENTS.findall(text))
        if not events:
            continue                                     # schedule or manual only
        seen[name] = hashlib.sha256(text.encode()).hexdigest()
        envs = sorted(set(ENV_USE.findall(text)) - CHECK_ENVS)
        if CHECKS.get(name) == seen[name]:
            continue
        if main_only(text, events) and name in stops:
            continue
        problems.append(f".github/workflows/{name} runs on {', '.join(sorted(events))}"
                        + (f" with environment {', '.join(envs)}" if envs else "")
                        + (" and its content isn't the check pinned in goal_guard.CHECKS" if name in CHECKS
                           else " and isn't one of the repository's checks"))
    for env in sorted(set(environments) - CHECK_ENVS):
        if env not in stops:
            problems.append(f"deployment environment {env} isn't named in the brief's Stop conditions")
    fingerprint = hashlib.sha256(json.dumps([seen, sorted(environments)], sort_keys=True).encode()).hexdigest()
    return problems, fingerprint
