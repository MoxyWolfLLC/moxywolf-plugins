#!/usr/bin/env python3
"""Required status checks on a protected branch: report them, and set them.

A workflow that RUNS is not a gate. Until its check is REQUIRED on the
protected branch, a red suite merges exactly as easily as a green one, and the
team believes it is covered because the run exists. This tells the two apart.

  check  --repo <path> [--branch main]
         Lists what the branch requires, and what the latest commit's
         check-runs actually produced. A check observed but not required is the
         gap. Exit 0 all observed checks are required, 1 some are not,
         2 no protection or no access to read it.

  ensure --repo <path> [--branch main] --require "<context>" [--require ...]
         Adds those contexts to the branch's required checks, preserving every
         other protection setting. NOT run as part of a build: protected-branch
         configuration is an administrative act (GOVERNANCE.md), and this
         subcommand exists so that act is recorded and repeatable rather than
         remembered. It never removes a context and never relaxes protection.

Auth: GITHUB_TOKEN in the environment. The token is never read from disk here
and never printed; the caller supplies it for the one call and it is not
persisted. A token without admin rights can still run `check` - it will report
what it could not read rather than claiming the branch is unprotected.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def slug(repo):
    """owner/name from the git remote, which is the only place it is not a guess."""
    url = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                         capture_output=True, text=True).stdout.strip()
    m = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?$", url)
    if not m:
        sys.exit(f"cannot read an owner/name out of the origin remote: {url!r}")
    return m.group(1), m.group(2)


def api(path, token, method="GET", body=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        detail = (e.read() or b"").decode()[:300]
        return e.code, {"message": detail}


def required_contexts(prot):
    """Both shapes GitHub returns: legacy `contexts`, and `checks` with app ids."""
    rsc = (prot or {}).get("required_status_checks") or {}
    out = list(rsc.get("contexts") or [])
    for c in rsc.get("checks") or []:
        if c.get("context") and c["context"] not in out:
            out.append(c["context"])
    return out


def observed_contexts(owner, name, branch, token):
    st, ref = api(f"/repos/{owner}/{name}/commits/{branch}", token)
    if st != 200:
        return None, f"could not read the tip of {branch}: HTTP {st}"
    sha = ref.get("sha")
    st, runs = api(f"/repos/{owner}/{name}/commits/{sha}/check-runs?per_page=100", token)
    if st != 200:
        return None, f"could not read check-runs for {sha[:7]}: HTTP {st}"
    seen = []
    for r in runs.get("check_runs") or []:
        nm = r.get("name")
        if nm and nm not in seen:
            seen.append(nm)
    return seen, sha


def cmd_check(repo, branch, token):
    """Observed FIRST, protection second, because the two need different rights.
    Reading branch protection needs admin; the agent PAT deliberately does not
    have it (GOVERNANCE.md). A run that cannot read protection can still say
    which checks exist and who has to make them gates, and that is worth more
    than an exit code with no detail."""
    owner, name = slug(repo)
    seen, sha = observed_contexts(owner, name, branch, token)
    print(f"{owner}/{name}@{branch}")
    if seen is None:
        print(f"  observed: unavailable - {sha}")
    else:
        print(f"  observed on {sha[:7]}: {', '.join(seen) if seen else '(none)'}")

    st, prot = api(f"/repos/{owner}/{name}/branches/{branch}/protection", token)
    if st == 404:
        print("  required: NO BRANCH PROTECTION. Nothing gates a merge; every check above is advisory.")
        if seen:
            print("  the Release Owner makes them gates in Settings > Branches, or with an admin token:")
            print(f"    repo_gates.py ensure --repo {repo} --branch {branch} "
                  + " ".join(f'--require "{c}"' for c in seen))
        return 2
    if st != 200:
        print(f"  required: UNREADABLE (HTTP {st}). Reading protection needs admin rights, which the agent "
              f"token is not meant to have - so this is NOT evidence that nothing is required, and not "
              f"evidence that anything is. The Release Owner confirms it in Settings > Branches.")
        return 2
    req = required_contexts(prot)
    print(f"  required: {', '.join(req) if req else '(none)'}")
    if seen is None:
        return 1 if not req else 0
    gap = [c for c in seen if c not in req]
    if gap:
        print("  NOT REQUIRED, so they do not gate a merge:")
        for c in gap:
            print(f"    - {c}")
        print("  make them gates:")
        args = " ".join(f'--require "{c}"' for c in gap)
        print(f"    repo_gates.py ensure --repo {repo} --branch {branch} {args}")
        return 1
    print("  every observed check is required.")
    return 0


def merged_payload(prot, add):
    """The PUT replaces the whole object, so every existing setting is carried
    over deliberately. Anything dropped here is protection silently removed."""
    rsc = (prot or {}).get("required_status_checks") or {}
    contexts = required_contexts(prot)
    for c in add:
        if c not in contexts:
            contexts.append(c)
    pr = prot.get("required_pull_request_reviews") or None
    body = {
        "required_status_checks": {
            "strict": bool(rsc.get("strict", False)),
            "contexts": contexts,
        },
        "enforce_admins": bool((prot.get("enforce_admins") or {}).get("enabled", False)),
        "required_pull_request_reviews": None if pr is None else {
            "dismiss_stale_reviews": bool(pr.get("dismiss_stale_reviews", False)),
            "require_code_owner_reviews": bool(pr.get("require_code_owner_reviews", False)),
            "required_approving_review_count": int(pr.get("required_approving_review_count", 0) or 0),
        },
        "restrictions": None,
    }
    for k in ("required_linear_history", "allow_force_pushes", "allow_deletions",
              "block_creations", "required_conversation_resolution"):
        v = prot.get(k)
        if isinstance(v, dict) and "enabled" in v:
            body[k] = bool(v["enabled"])
    return body, contexts


def cmd_ensure(repo, branch, add, token):
    owner, name = slug(repo)
    st, prot = api(f"/repos/{owner}/{name}/branches/{branch}/protection", token)
    if st == 404:
        print(f"{owner}/{name}@{branch} is not protected. Enabling protection is a wider decision than "
              f"adding a required check - do it deliberately, then run this again.")
        return 2
    if st != 200:
        print(f"could not read protection (HTTP {st}); refusing to write a configuration built on a failed read.")
        return 2
    before = required_contexts(prot)
    body, after = merged_payload(prot, add)
    if set(after) == set(before):
        print(f"{owner}/{name}@{branch}: already required: {', '.join(before)}")
        return 0
    st, res = api(f"/repos/{owner}/{name}/branches/{branch}/protection", token, "PUT", body)
    if st not in (200, 201):
        print(f"FAILED to set required checks (HTTP {st}): {res.get('message','')[:200]}")
        return 2
    now = required_contexts(res)
    print(f"{owner}/{name}@{branch}")
    print(f"  was required: {', '.join(before) if before else '(none)'}")
    print(f"  now required: {', '.join(now)}")
    missing = [c for c in add if c not in now]
    if missing:
        print(f"  NOT APPLIED: {', '.join(missing)} - the API accepted the call without them")
        return 1
    return 0


def selftest():
    """The merge is the part that can silently destroy protection, so that is
    what is tested. No network."""
    prot = {
        "required_status_checks": {"strict": True, "contexts": ["old"]},
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {"required_approving_review_count": 2,
                                          "dismiss_stale_reviews": True,
                                          "require_code_owner_reviews": False},
        "required_linear_history": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
    }
    body, after = merged_payload(prot, ["new", "old"])
    assert after == ["old", "new"], after
    assert body["required_status_checks"]["strict"] is True
    assert body["enforce_admins"] is True
    assert body["required_pull_request_reviews"]["required_approving_review_count"] == 2
    assert body["required_linear_history"] is True and body["allow_force_pushes"] is False
    # the newer `checks` shape is read too
    p2 = {"required_status_checks": {"checks": [{"context": "a", "app_id": 1}]}}
    assert required_contexts(p2) == ["a"]
    # nothing to add is not a rewrite
    b3, a3 = merged_payload(prot, ["old"])
    assert a3 == ["old"]
    # an unprotected branch has no contexts and does not crash
    assert required_contexts({}) == [] and required_contexts(None) == []
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--repo", required=True); c.add_argument("--branch", default="main")
    e = sub.add_parser("ensure"); e.add_argument("--repo", required=True); e.add_argument("--branch", default="main")
    e.add_argument("--require", action="append", required=True)
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest(); return 0
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        sys.exit("GITHUB_TOKEN is not set. Export the vault PAT for this one call; do not write it anywhere.")
    if a.cmd == "check":
        return cmd_check(a.repo, a.branch, token)
    return cmd_ensure(a.repo, a.branch, a.require, token)


if __name__ == "__main__":
    sys.exit(main())
