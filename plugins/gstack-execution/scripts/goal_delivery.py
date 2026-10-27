#!/usr/bin/env python3
"""Goal `gstack-delivery-through-merge`: delivery state, the dispatch gate, bounded recovery and
synchronization. A delivery document (one JSON file, kept with the goal run's state) names the
approval it acts under, each change (candidate head, base, target, pull request, review chain),
the declared release companion and the required working copies. Everything here reads what is
observed (GitHub, git, the ledger) and never what a model declared.

  goal_delivery.py reserve-review --delivery FILE --change-id ID --review-id ID
      Record one review attempt for the change, under the cumulative limit; exhaustion exits
      nonzero and writes nothing. Prints {"reserved": true, "attempts_used": N}.
  goal_delivery.py sync-checkout --checkout FILE --merge SHA[,SHA...]
      Fast-forward the required checkout FILE names ({name, path, host, remote, branch}) to the
      branch tip containing every SHA, or change nothing. Prints {"status": "synced", ...} and exits 0,
      or {"status": "sync_pending", "name", "reason", ...} and exits 3.
  goal_delivery.py status --delivery FILE
      Observes each required checkout against its repository's required merges, then prints {"delivery_status": "complete" | "in_progress" | "sync_pending" | "blocked", ...}.

Library: next_action(delivery, observed), reserve_review(delivery, change_id, review_id),
sync_checkout(checkout, merge_sha), delivery_status(delivery, observed).
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import goal_guard   # the merge gate's check reading (checks_green), shared rather than restated

CLEAN_REVIEW = {"no_blocking_findings", "fixes_verified"}
MERGE_CHECKS = ("tests", "goal-envelope", "goal-tests")


class Blocked(Exception):
    """A delivery step that must not proceed; the message says why, naming what was read."""


# ---- persistence: one document, read whole, written whole, never partially ----

def read_delivery(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Blocked(f"delivery document unreadable: {e}")
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 or not isinstance(doc.get("changes"), dict):
        raise Blocked("delivery document is not a schema_version 1 delivery")
    approval = doc.get("approval") or {}
    if not all(approval.get(k) for k in ("repo", "pr", "review_id", "head", "owner")):
        raise Blocked("delivery approval is incomplete: repo, pr, review_id, head and owner are required")
    return doc


def write_delivery(path, doc):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


class _Lock:
    """One writer at a time per document: the first to create the lock file wins; the rest refuse.
    ponytail: a lock file, not a lease; a crashed holder leaves it, and the next run reports it."""
    def __init__(self, path, wait=5.0):
        self.path = Path(str(path) + ".lock"); self.wait = wait; self.fd = None
    def __enter__(self):
        deadline = time.time() + self.wait
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode()); return self
            except FileExistsError:
                if time.time() > deadline:
                    raise Blocked(f"another process holds {self.path.name}; one owner at a time")
                time.sleep(0.05)
    def __exit__(self, *a):
        if self.fd is not None:
            os.close(self.fd)
        try: self.path.unlink()
        except FileNotFoundError: pass


# ---- the cumulative review limit ----

def reserve_review(delivery, change_id, review_id):
    """One review attempt for one change, counted cumulatively: a replacement review id is one more
    attempt against the same budget, never a fresh one. Returns the attempts used after reserving;
    raises Blocked at the limit without changing the document."""
    change = (delivery.get("changes") or {}).get(change_id)
    if change is None:
        raise Blocked(f"no change {change_id!r} in this delivery")
    limit = delivery.get("max_review_rounds")
    if not isinstance(limit, int) or limit < 1:
        raise Blocked("max_review_rounds is missing or unreadable; the limit blocks, it never defaults")
    attempts = change.setdefault("review_attempts", [])
    if any(a.get("review_id") == review_id for a in attempts):
        raise Blocked(f"review {review_id} is already reserved for {change_id}")
    if len(attempts) >= limit:
        raise Blocked(f"review limit exhausted for {change_id}: {len(attempts)} of {limit} passes used "
                      f"({', '.join(a['review_id'] for a in attempts)}); a replacement review id does not reset it")
    attempts.append({"review_id": review_id, "reserved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "attempt": len(attempts) + 1})
    return len(attempts)


# ---- the one allowed next action ----

def pr_identity_problems(ch, pr):
    """Repair 1: an observed pull request speaks for this change only when it is this change's pull
    request (number), in this change's repository (its base repository) and into this change's target.
    Anything missing is a mismatch, never a default match."""
    base = (pr or {}).get("base") or {}
    problems = []
    if ch.get("pr") is not None and pr.get("number") != ch["pr"]:
        problems.append(f"pull request #{pr.get('number')} is not #{ch['pr']}")
    if ch.get("target") and base.get("ref") != ch["target"]:
        problems.append(f"it targets {base.get('ref')}, not {ch['target']}")
    if ch.get("repo") and (base.get("repo") or {}).get("full_name") != ch["repo"]:
        problems.append(f"it belongs to {(base.get('repo') or {}).get('full_name')}, not {ch['repo']}")
    return problems


def merged_here(ch, pr):
    """GitHub reports this change's own pull request merged at this change's candidate head."""
    return (pr is not None and bool(pr.get("merged")) and not pr_identity_problems(ch, pr)
            and (pr.get("head", {}).get("sha") == ch.get("head") or pr.get("merge_commit_sha") == ch.get("head")))


def _check_problems(ch, pr, observed_checks):
    """Repair 2: required checks are green for THIS pull request, target and current base, using the
    existing merge-gate reading (goal_guard.checks_green): each check is (conclusion, external_id),
    and a goal check's binding must name this PR, target and base."""
    checks = {k: (tuple(v) if isinstance(v, (list, tuple)) else (v, None)) for k, v in (observed_checks or {}).items()}
    prd = {"number": pr.get("number"), "head": pr.get("head", {}).get("sha"),
           "base_ref": (pr.get("base") or {}).get("ref"), "base": (pr.get("base") or {}).get("sha")}
    return goal_guard.checks_green(ch.get("target"), ch.get("head"), checks, prd)


def next_action(delivery, observed):
    """One allowed phase or action, or a specific blocked or pending state, from the approval, the
    changes' candidate and base, the source bindings, the checkouts, the attempt counts, and what
    was observed outside (GitHub pull requests and checks, checkout states). `observed` is
    {"prs": {pr_number: pr_json}, "checks": {sha: {name: conclusion}}, "checkouts": {name: status}}
    as read by the caller from GitHub and git; nothing a model wrote counts.

    Returns {"action": ..., "change": id} or {"blocked": why} or {"pending": why, "change": id}."""
    approval = delivery.get("approval") or {}
    if not approval.get("head"):
        return {"blocked": "no approval head: the authority record is missing or unreadable"}
    if not isinstance(delivery.get("max_review_rounds"), int):
        return {"blocked": "max_review_rounds unreadable: the budget record blocks further action"}
    for b in delivery.get("source_bindings") or ():
        if b.get("stale"):
            return {"blocked": f"stale source binding {b.get('id')}: refresh the evidence before dispatch"}
    order = list(delivery["changes"])
    companion = delivery.get("release_companion")
    if companion and companion in order:   # the companion follows every implementation change
        order.remove(companion); order.append(companion)
    for cid in order:
        ch = delivery["changes"][cid]
        # Observations are keyed by change id (review F5): two repositories may share a pull request
        # number or a commit, and one must never answer for the other.
        pr = (observed.get("prs") or {}).get(cid)
        here = merged_here(ch, pr)
        if pr is not None and pr.get("merged") and pr_identity_problems(ch, pr):
            return {"blocked": f"{cid}: GitHub reports a merge that is not this change's: " + "; ".join(pr_identity_problems(ch, pr))
                               + "; it is not recorded, released or synchronized"}
        merge = ch.get("merge") or {}
        if merge.get("verified") and pr is not None and not here:
            # review F3: a persisted verification contradicted by GitHub is not progress
            return {"blocked": f"{cid}: the record says merged at {str(merge.get('head'))[:12]} but pull request "
                               f"#{ch.get('pr')} is {'merged at ' + str(pr.get('head', {}).get('sha'))[:12] if pr.get('merged') else 'not merged'}; "
                               "the persisted merge is invalid"}
        if merge.get("verified") and pr is None:
            return {"pending": f"{cid}: merge recorded but not re-verified; pull request #{ch.get('pr')} not observed", "change": cid}
        if not merge.get("verified"):
            if pr is None:
                return {"pending": f"pull request #{ch.get('pr')} for {cid} not observed", "change": cid}
            if pr.get("merged"):
                if not here:
                    return {"blocked": f"pull request #{ch['pr']} merged at {str(pr.get('head', {}).get('sha'))[:12]}, "
                                       f"not the candidate head {str(ch.get('head'))[:12]}"}
                return {"action": "record_merge", "change": cid, "sha": pr.get("merge_commit_sha")}
            if pr_identity_problems(ch, pr):
                return {"blocked": f"{cid}: the observed pull request is not this change's: " + "; ".join(pr_identity_problems(ch, pr))}
            if pr.get("head", {}).get("sha") != ch.get("head"):
                return {"blocked": f"pull request #{ch['pr']} is at {str(pr.get('head', {}).get('sha'))[:12]}, "
                                   f"not the candidate head {str(ch.get('head'))[:12]}; a moved head is not merged"}
            base = pr.get("base") or {}
            if ch.get("target") and base.get("ref") not in (None, ch["target"]):
                return {"blocked": f"pull request #{ch['pr']} targets {base.get('ref')}, not {ch['target']}; a retargeted pull request is not the approved change"}
            if ch.get("base") and base.get("sha") not in (None, ch["base"]):
                return {"pending": f"pull request #{ch['pr']} base is {str(base.get('sha'))[:12]}, not the recorded base {str(ch['base'])[:12]}; sync and re-verify", "change": cid}
            # review F2: a clean review counts only for this repository at this candidate head
            review = (observed.get("reviews") or {}).get(cid) or {}
            if review.get("outcome") not in CLEAN_REVIEW:
                return {"pending": f"review {ch.get('review_id')} is {review.get('outcome') or 'not observed'}, not clean", "change": cid}
            if review.get("incomplete") or not (review.get("repo") and review.get("head") and review.get("base")):
                return {"pending": f"review {ch.get('review_id')} evidence is incomplete: {review.get('incomplete') or 'no repository, head or base'}", "change": cid}
            if ch.get("final"):
                # Repair 6: the goal pull request merges its finalized head, one commit past the head the
                # whole-goal review passed at. It counts only in the GO-011.2 relationship, which the
                # runner observes with goal_run.final_review_pinned; nothing is restated here.
                fin = review.get("finalized") or {}
                if fin.get("pinned") is not True:
                    return {"pending": f"review {ch.get('review_id')} is not pinned to the tested head without its holdout (GO-011.2)"
                                       + (f": {fin['why']}" if fin.get("why") else ""), "change": cid}
                if fin.get("finalized_head") != ch.get("head"):
                    return {"pending": f"the candidate head {str(ch.get('head'))[:12]} is not the recorded finalized head "
                                       f"{str(fin.get('finalized_head'))[:12]}", "change": cid}
            elif review.get("head") != ch.get("head"):
                return {"pending": f"review {ch.get('review_id')} passed at {str(review.get('head'))[:12]}, not the candidate head {str(ch.get('head'))[:12]}", "change": cid}
            if Path(review["repo"]).resolve() != Path(ch.get("path") or "").resolve():
                return {"blocked": f"review {ch.get('review_id')} is of {review['repo']}, not {ch.get('path')}"}
            if ch.get("base") and review["base"] != ch["base"]:
                return {"pending": f"review {ch.get('review_id')} reviewed from base {str(review['base'])[:12]}, not the candidate range from {str(ch['base'])[:12]}", "change": cid}
            missing = _check_problems(ch, pr, (observed.get("checks") or {}).get(cid))
            if missing:
                return {"pending": f"checks not green for this pull request at {str(ch.get('head'))[:12]}: {'; '.join(missing)}", "change": cid}
            if pr.get("mergeable_state") not in (None, "clean", "unstable"):
                return {"pending": f"pull request #{ch['pr']} is {pr.get('mergeable_state')}", "change": cid}
            return {"action": "merge", "change": cid, "head": ch["head"], "pr": ch["pr"]}
        if not (ch.get("release_record") or {}).get("verified"):
            return {"action": "record_release", "change": cid, "pr": ch.get("pr")}
    for spec in delivery.get("required_checkouts") or ():
        status = (observed.get("checkouts") or {}).get(spec.get("name")) or {}
        if status.get("status") != "synced":
            return {"action": "sync_checkout", "checkout": spec.get("name")}
    return {"action": "complete"}


def delivery_status(delivery, observed=None):
    """`complete` only when every change is merged (verified from GitHub) and its release record
    is verified, the declared release companion among them, and every required checkout has been
    observed synced; otherwise the applicable phase, blocker or sync_pending, naming what is missing.
    Nothing here trusts a flag a model set: a merge is verified by the observation that set it."""
    out = {"changes": {}, "required_checkouts": []}
    missing = []
    companion = delivery.get("release_companion")
    if companion and companion not in (delivery.get("changes") or {}):
        return {"delivery_status": "blocked", "reason": f"release companion {companion!r} is declared but not a change", **out}
    for cid, ch in (delivery.get("changes") or {}).items():
        merged = bool((ch.get("merge") or {}).get("verified"))
        recorded = bool((ch.get("release_record") or {}).get("verified"))
        out["changes"][cid] = {"merged": merged, "recorded": recorded, "release_companion": cid == companion}
        if not merged:
            missing.append(f"{cid}: not merged")
        elif not recorded:
            missing.append(f"{cid}: merged, release not recorded")
    for spec in delivery.get("required_checkouts") or ():
        st = ((observed or {}).get("checkouts") or {}).get(spec.get("name")) or {}   # repair 5: observed, never a saved flag
        out["required_checkouts"].append({"name": spec.get("name"), "status": st.get("status") or "not_observed", "reason": st.get("reason")})
        if st.get("status") != "synced":
            missing.append(f"checkout {spec.get('name')}: {st.get('status') or 'not synchronized'}")
    if not missing:
        return {"delivery_status": "complete", **out}
    phase = "sync_pending" if all(m.startswith("checkout ") for m in missing) else "in_progress"
    return {"delivery_status": phase, "missing": missing, **out}


def _git(path, *args, check=False):
    p = subprocess.run(["git", "--no-optional-locks", "-C", str(path), *args], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    if check and p.returncode:
        raise Blocked(f"git {' '.join(args[:2])} failed in {path}: {(p.stderr or p.stdout).strip()[:200]}")
    return p


class _Unreadable(Exception):
    """Repair 7: a Git read that failed. Its output is never interpreted; the checkout is pending."""


def _read(path, *args):
    """stdout of a Git read that succeeded, or _Unreadable naming the command and Git's own words."""
    p = _git(path, *args)
    if p.returncode:
        raise _Unreadable(f"git {' '.join(args[:2])} failed in {path} ({p.returncode}): "
                          f"{(p.stderr or p.stdout).strip()[:200] or 'no output'}")
    return p.stdout


def _ancestor(path, a, b):
    """merge-base --is-ancestor: 0 is yes, 1 is no, anything else is a read that failed."""
    p = _git(path, "merge-base", "--is-ancestor", a, b)
    if p.returncode not in (0, 1):
        raise _Unreadable(f"git merge-base failed in {path} ({p.returncode}): {(p.stderr or p.stdout).strip()[:200] or 'no output'}")
    return p.returncode == 0


def _contains(path, sha, head):
    """Whether head contains sha. A commit this object store doesn't have is not contained (it can't
    be an ancestor of anything here); any other failed read is _Unreadable."""
    if _git(path, "cat-file", "-e", f"{sha}^{{commit}}").returncode:
        return False
    return _ancestor(path, sha, head)


GITHUB_REMOTE = re.compile(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?")


def github_repo(url):
    """owner/name of a github.com remote URL, lower-cased (GitHub names ignore case), or None."""
    m = GITHUB_REMOTE.fullmatch((url or "").strip())
    return m.group(1).lower() if m else None


def required_merges(delivery, spec, default_repo=None):
    """Repair 8: the merges a required checkout must contain. The checkout is bound to its repository
    (its `repo`, or the github.com repository its `remote` names), and its required merges are every
    verified merge of THAT repository's changes into its branch. Another repository's merge never
    counts, and none is chosen by record order. A checkout with no repository identity blocks."""
    repo = (spec.get("repo") or github_repo(spec.get("remote")) or "").lower()
    if not repo:
        raise Blocked(f"checkout {spec.get('name')} isn't bound to a repository: no repo, and its remote "
                      f"{spec.get('remote')!r} names no github.com repository")
    branch = spec.get("branch") or "main"
    return [c["merge"]["sha"] for c in (delivery.get("changes") or {}).values()
            if (c.get("merge") or {}).get("verified") and c["merge"].get("sha") and c.get("target") == branch
            and (c.get("repo") or default_repo or "").lower() == repo]


def _shas(merge_shas):
    shas = [merge_shas] if isinstance(merge_shas, str) else list(merge_shas or ())
    if not shas or not all(isinstance(s, str) and s for s in shas):
        raise Blocked("no required merge to check the checkout against")
    return shas


def _pending_for(checkout):
    name, path = checkout.get("name"), str(checkout.get("path") or "")
    def pending(reason):
        return {"status": "sync_pending", "name": name, "path": path, "reason": reason,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    return pending


def _inspect(checkout, pending):
    """The reads observe_checkout and sync_checkout share before anything is written: host, path,
    remote, branch and tracked/untracked state, each Git read checked for its exit code (repair 7).
    Returns (path, remote, branch, head), or a pending result."""
    name, path = checkout.get("name"), Path(str(checkout.get("path") or ""))
    here = socket.gethostname()
    if checkout.get("host") and checkout["host"] != here:
        return pending(f"wrong host: {name} is on {checkout['host']}, this is {here}; nothing touched")
    if not path.is_dir():
        return pending(f"unavailable: {path} is missing")
    git_dir = _git(path, "rev-parse", "--git-dir")
    if git_dir.returncode:
        return pending(f"unavailable: {path} is not a readable Git checkout: {(git_dir.stderr or git_dir.stdout).strip()[:200]}")
    remote = _read(path, "remote", "get-url", "origin").strip()
    if checkout.get("remote") and remote != checkout["remote"]:
        return pending(f"remote mismatch: origin is {remote or 'unset'}, not {checkout['remote']}")
    want = checkout.get("branch") or "main"
    ref = _git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
    if ref.returncode == 1 and not (ref.stderr or "").strip():
        return pending(f"unexpected branch: {name} is on a detached HEAD, not {want}")
    if ref.returncode:
        raise _Unreadable(f"git symbolic-ref failed in {path} ({ref.returncode}): {(ref.stderr or ref.stdout).strip()[:200]}")
    branch = ref.stdout.strip()
    if branch != want:
        return pending(f"unexpected branch: {name} is on {branch}, not {want}")
    dirt = _read(path, "status", "--porcelain=v1", "--untracked-files=all")
    if dirt.strip():
        return pending(f"dirty: {name} has uncommitted or untracked changes ({len(dirt.splitlines())} entries); nothing touched")
    head = _read(path, "rev-parse", "HEAD").strip()
    return path, remote, want, head


def sync_checkout(checkout, merge_shas):
    """GO-003.12: bring one required checkout to the branch tip that contains every required merge
    (repair 8: all of them, not the newest), by fast-forward only, or report sync_pending naming the
    checkout and why. Every refusal happens before anything in the checkout is written: the host, the
    path, the remote, the branch and the tracked and untracked state are read with
    --no-optional-locks, each read checked for its exit code (repair 7), and the remote tip and the
    ancestry are worked out in a throwaway object store, so a refused checkout's files, status and Git
    metadata are exactly as they were. Only a clean checkout on the expected branch whose HEAD is an
    ancestor of a remote tip containing every merge is fetched into and fast-forwarded."""
    pending = _pending_for(checkout)
    name = checkout.get("name")
    try:
        shas = _shas(merge_shas)
        seen = _inspect(checkout, pending)
        if isinstance(seen, dict):
            return seen
        path, remote, want, head = seen
        # ponytail: a throwaway bare store holds both sides, so ancestry is known without writing the checkout
        with tempfile.TemporaryDirectory(prefix="gstack-sync-") as tmp:
            _read(tmp, "init", "--bare", "-q")
            got = _git(tmp, "fetch", "-q", "--no-tags", remote, f"+refs/heads/{want}:refs/remote-tip")
            if got.returncode:
                return pending(f"unavailable: can't read {want} from {remote}: {(got.stderr or '').strip()[:160]}")
            _read(tmp, "fetch", "-q", "--no-tags", str(path.resolve()), f"+{head}:refs/local-head")
            tip = _read(tmp, "rev-parse", "refs/remote-tip").strip()
            missing = [s for s in shas if not _contains(tmp, s, tip)]
            if missing:
                return pending(f"required merge(s) {', '.join(s[:12] for s in missing)} not on {remote} {want} ({tip[:12]}) yet; nothing touched")
            if not _ancestor(tmp, head, tip):
                return pending(f"diverged: {name} at {head[:12]} has commits not on {want}; a fast-forward is impossible, nothing touched")
        if head != tip:
            _read(path, "fetch", "-q", "--no-tags", "origin", f"refs/heads/{want}")
            _read(path, "merge", "--ff-only", "-q", tip)
        now = _read(path, "rev-parse", "HEAD").strip()
        status = _read(path, "status", "--porcelain=v1", "--untracked-files=all")
        if now != tip or status.strip():
            return pending(f"after the fast-forward {name} is at {now[:12]} with status {status.strip()[:80]!r}, not clean at {tip[:12]}")
    except _Unreadable as e:
        return pending(f"unreadable: {e}; not synchronized")
    return {"status": "synced", "name": name, "path": str(path), "host": socket.gethostname(), "branch": want, "remote": remote,
            "sha": now, "contains": shas, "git_status": "", "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def observe_checkout(checkout, merge_shas):
    """Repair 5: what the required checkout is right now, read-only: the same host, path, remote,
    branch and tracked/untracked checks sync_checkout makes before writing, each read checked for its
    exit code (repair 7), whether its HEAD contains every required merge (repair 8), and whether it is
    at the live remote tip. A saved `synced` record is never consulted."""
    pending = _pending_for(checkout)
    name = checkout.get("name")
    try:
        shas = _shas(merge_shas)
        seen = _inspect(checkout, pending)
        if isinstance(seen, dict):
            return seen
        path, remote, want, head = seen
        missing = [s for s in shas if not _contains(path, s, head)]
        if missing:
            return pending(f"{name} at {head[:12]} does not contain the required merge(s) {', '.join(s[:12] for s in missing)}")
        # review F1 (20261027-124210): containing the merges isn't enough; synced means at the live remote
        # tip. ls-remote reads the remote without writing the checkout.
        tip = (_read(path, "ls-remote", "origin", f"refs/heads/{want}").split() or [""])[0]
        if not tip:
            return pending(f"remote unreadable: {remote} has no {want}; not synchronized")
        if tip != head:
            return pending(f"not at the remote tip: {name} is at {head[:12]}, remote {want} is at {tip[:12]} (behind, ahead or diverged)")
    except _Unreadable as e:
        return pending(f"unreadable: {e}; not synchronized")
    return {"status": "synced", "name": name, "path": str(path), "host": socket.gethostname(), "branch": want, "remote": remote,
            "sha": head, "remote_tip": tip, "contains": shas, "git_status": "", "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


# ---- CLI ----

def _cli_reserve(opts):
    path = opts["--delivery"]
    with _Lock(path):
        doc = read_delivery(path)
        doc["active_seconds"] = int(doc.get("active_seconds") or 0)   # elapsed time is carried, never reset
        used = reserve_review(doc, opts["--change-id"], opts["--review-id"])
        write_delivery(path, doc)
    print(json.dumps({"reserved": True, "attempts_used": used, "limit": doc["max_review_rounds"]}))
    return 0


def main(argv):
    cmd, opts = (argv + [None])[0], dict(zip(argv[1::2], argv[2::2]))
    try:
        if cmd == "reserve-review" and set(opts) == {"--delivery", "--change-id", "--review-id"}:
            return _cli_reserve(opts)
        if cmd == "sync-checkout" and set(opts) == {"--checkout", "--merge"}:
            out = sync_checkout(json.loads(Path(opts["--checkout"]).read_text()), [m for m in opts["--merge"].split(",") if m])
            print(json.dumps(out)); return 0 if out["status"] == "synced" else 3
        if cmd == "status" and set(opts) == {"--delivery"}:
            doc = read_delivery(opts["--delivery"])
            observed = {"checkouts": {}}       # repair 8: the completion decision reads each checkout now
            for spec in doc.get("required_checkouts") or ():
                merges = required_merges(doc, spec, (doc.get("approval") or {}).get("repo"))
                if merges:
                    observed["checkouts"][spec.get("name")] = observe_checkout(spec, merges)
            print(json.dumps(delivery_status(doc, observed))); return 0
        print(__doc__, file=sys.stderr); return 2
    except Blocked as e:
        print(json.dumps({"blocked": str(e)}), file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
