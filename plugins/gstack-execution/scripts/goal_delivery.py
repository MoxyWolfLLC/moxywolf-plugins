#!/usr/bin/env python3
"""Goal `gstack-delivery-through-merge`: delivery state, the dispatch gate, bounded recovery and
synchronization. A delivery document (one JSON file, kept with the goal run's state) names the
approval it acts under, each change (candidate head, base, target, pull request, review chain),
the declared release companion and the required working copies. Everything here reads what is
observed (GitHub, git, the ledger) and never what a model declared.

  goal_delivery.py reserve-review --delivery FILE --change-id ID --review-id ID
      Record one review attempt for the change, under the cumulative limit; exhaustion exits
      nonzero and writes nothing. Prints {"reserved": true, "attempts_used": N}.
  goal_delivery.py sync-checkout --checkout FILE --merge SHA        (item 3)
  goal_delivery.py status --delivery FILE                           (item 3)

Library: next_action(delivery, observed), reserve_review(delivery, change_id, review_id).
"""
import json
import os
import sys
import time
from pathlib import Path

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

def _checks_green(observed_checks):
    missing = [c for c in MERGE_CHECKS if (observed_checks or {}).get(c) != "success"]
    return missing


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
        merged_here = pr is not None and pr.get("merged") and (
            pr.get("head", {}).get("sha") == ch.get("head") or pr.get("merge_commit_sha") == ch.get("head"))
        merge = ch.get("merge") or {}
        if merge.get("verified") and pr is not None and not merged_here:
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
                if not merged_here:
                    return {"blocked": f"pull request #{ch['pr']} merged at {str(pr.get('head', {}).get('sha'))[:12]}, "
                                       f"not the candidate head {str(ch.get('head'))[:12]}"}
                return {"action": "record_merge", "change": cid, "sha": pr.get("merge_commit_sha")}
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
            if review.get("head") != ch.get("head"):
                return {"pending": f"review {ch.get('review_id')} passed at {str(review.get('head'))[:12]}, not the candidate head {str(ch.get('head'))[:12]}", "change": cid}
            if Path(review["repo"]).resolve() != Path(ch.get("path") or "").resolve():
                return {"blocked": f"review {ch.get('review_id')} is of {review['repo']}, not {ch.get('path')}"}
            if ch.get("base") and review["base"] != ch["base"]:
                return {"pending": f"review {ch.get('review_id')} reviewed from base {str(review['base'])[:12]}, not the candidate range from {str(ch['base'])[:12]}", "change": cid}
            missing = _checks_green((observed.get("checks") or {}).get(cid))
            if missing:
                return {"pending": f"checks not green at {str(ch.get('head'))[:12]}: {', '.join(missing)}", "change": cid}
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
        st = ((observed or {}).get("checkouts") or {}).get(spec.get("name")) or spec.get("sync") or {}
        out["required_checkouts"].append({"name": spec.get("name"), "status": st.get("status") or "not_observed", "reason": st.get("reason")})
        if st.get("status") != "synced":
            missing.append(f"checkout {spec.get('name')}: {st.get('status') or 'not synchronized'}")
    if not missing:
        return {"delivery_status": "complete", **out}
    phase = "sync_pending" if all(m.startswith("checkout ") for m in missing) else "in_progress"
    return {"delivery_status": phase, "missing": missing, **out}


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
        if cmd == "status" and set(opts) == {"--delivery"}:
            print(json.dumps(delivery_status(read_delivery(opts["--delivery"])))); return 0
        print(__doc__, file=sys.stderr); return 2
    except Blocked as e:
        print(json.dumps({"blocked": str(e)}), file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
