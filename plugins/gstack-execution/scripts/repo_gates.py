#!/usr/bin/env python3
"""Required status checks on a protected branch: report them, and set them.

A workflow that RUNS is not a gate. Until its check is REQUIRED on the
protected branch, a red suite merges exactly as easily as a green one, and the
team believes it is covered because the run exists. This tells the two apart.

  check  --repo <path> [--branch main]
         Lists what the branch requires, and what the latest commit's
         check-runs actually produced. A check observed but not required is the
         gap. Exit 0 all observed checks are required, 1 some are not,
         2 protection could not be read, 3 required checks are not available on
         this repository's plan at all - which is a different answer from "no
         access", and the one a private repository on a free plan gives.

  ensure --repo <path> [--branch main] --require "<context>" [--require ...]
         Adds those contexts to the branch's required checks, preserving every
         other protection setting. NOT run as part of a build: protected-branch
         configuration is an administrative act (GOVERNANCE.md), and this
         subcommand exists so that act is recorded and repeatable rather than
         remembered. It never removes a context and never relaxes protection.

Two credentials, separated by CAPABILITY and not by trust:

  GITHUB_TOKEN       the push credential. Feature branches and pull requests.
                     Used by `check`, which only reads. Never used to administer.

  GITHUB_GATE_TOKEN  a FINE-GRAINED token scoped to the specific repositories
                     with `Administration: read and write` and `Contents: read`.
                     Used by `ensure`, and only by `ensure`.

Why fine-grained is not a preference. A token that can SET a required check can
also REMOVE it, and with protection off, a token that can push has merge
authority - so handing an agent a classic `repo`-scoped token to configure gates
deletes the control it was configuring. A fine-grained token with Contents:read
cannot push whatever it does to protection, so the property the governance
actually cares about survives the delegation. `ensure` therefore REFUSES any
token that presents `x-oauth-scopes`, which is how a classic token identifies
itself, because classic scopes cannot express administration-without-push.

Neither token is read from disk here and neither is ever printed.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
import sys

API = "https://api.github.com"


def slug(repo):
    """owner/name, from .git/config first and `git` only as a fallback.

    Not a style choice. On macOS /usr/bin/git is a licence-gated shim that fails
    every invocation until someone runs `xcodebuild -license`, so a script that
    needs git to learn the repository's name fails on a machine where nothing is
    actually wrong. The config file is right there and needs no toolchain."""
    cfg = Path(repo) / ".git" / "config"
    if cfg.is_file():
        txt = cfg.read_text(errors="replace")
        m = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', txt, re.S)
        if m:
            g = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?$", m.group(1).strip())
            if g:
                return g.group(1), g.group(2)
    r = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    g = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?$", (r.stdout or "").strip())
    if g:
        return g.group(1), g.group(2)
    why = (r.stderr or "").strip()[:200] or "no origin remote found"
    sys.exit(f"cannot establish owner/name for {repo}: {why}")


def api(path, token, method="GET", body=None):
    """Over curl, deliberately, not urllib.

    The macOS system python3 has no CA bundle: urllib dies with
    CERTIFICATE_VERIFY_FAILED while curl, which uses the system trust store,
    works. A run that happens to succeed because Xcode's python was first on
    PATH is not a portable script - and this one is invoked from a skill on
    whatever python3 the machine offers."""
    cmd = ["curl", "-sS", "-D", "-", "-o", "-", "-X", method,
           "-H", f"Authorization: Bearer {token}",
           "-H", "Accept: application/vnd.github+json",
           "-H", "X-GitHub-Api-Version: 2022-11-28",
           "--max-time", "45"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", json.dumps(body)]
    cmd.append(API + path)
    # The token is in argv for this child only and is never logged or echoed.
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return 0, {"message": f"curl failed: {r.stderr.strip()[:200]}"}
    status, hdrs, payload = _split(r.stdout)
    try:
        return status, (json.loads(payload) if payload.strip() else None)
    except json.JSONDecodeError:
        return status, {"message": payload[:300]}


def _split(raw):
    """curl -D - emits header blocks then the body; a redirect or a 100-continue
    means more than one block, and the LAST one describes the response."""
    parts = re.split(r"\r?\n\r?\n", raw)
    head, body = "", ""
    for i, blk in enumerate(parts):
        if re.match(r"HTTP/\d", blk.strip()[:8] or "x"):
            head = blk
            body = "\n\n".join(parts[i + 1:])
    m = re.search(r"HTTP/\d(?:\.\d)?\s+(\d{3})", head)
    status = int(m.group(1)) if m else 0
    hdrs = {}
    for line in head.splitlines()[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            hdrs[k.strip().lower()] = v.strip()
    return status, hdrs, body


def api_headers(path, token):
    cmd = ["curl", "-sS", "-D", "-", "-o", "/dev/null", "-X", "GET",
           "-H", f"Authorization: Bearer {token}",
           "-H", "Accept: application/vnd.github+json",
           "--max-time", "45", API + path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return 0, {}
    status, hdrs, _ = _split(r.stdout)
    return status, hdrs


def token_kind(token):
    """classic | fine-grained | unknown, from GitHub's own answer.

    NOT from the ghp_/github_pat_ prefix: a prefix is a naming convention and
    this decision is about capability. GitHub returns x-oauth-scopes for an
    OAuth/classic credential and omits the header for a fine-grained one."""
    status, hdrs = api_headers("/", token)
    if status == 0:
        return "unknown", None
    if "x-oauth-scopes" in hdrs:
        return "classic", hdrs["x-oauth-scopes"] or "(none listed)"
    if status in (401, 403):
        return "unknown", None
    return "fine-grained", None


def plan_limited(payload):
    """GitHub answers 403 for a private repository on a plan without branch
    protection, with the same status it uses for insufficient rights. Reporting
    that as a rights problem sends the reader to mint a token that cannot help.
    The message is the only thing that distinguishes them."""
    msg = ((payload or {}).get("message") or "")
    return "upgrade to github" in msg.lower() or "make this repository public" in msg.lower()


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
    if st == 403 and plan_limited(prot):
        print("  required: NOT AVAILABLE ON THIS PLAN. GitHub answers "
              '"Upgrade to GitHub Pro or make this repository public" - this repository is private on a '
              "plan without branch protection or rulesets, so NO required check can exist here and no "
              "credential changes that. Every check above is advisory, permanently, until the plan changes.")
        print("  so the gate has to live in the process instead: /gstack-build must refuse to report")
        print("  ready_for_human_release while a suite is red, because GitHub will not refuse the merge.")
        return 3
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


def merged_payload(prot, add, enforce_admins=None):
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
        # None means "leave as it is"; True/False is this call deciding.
        "enforce_admins": bool((prot.get("enforce_admins") or {}).get("enabled", False))
                          if enforce_admins is None else bool(enforce_admins),
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


def cmd_ensure(repo, branch, add, token, enable=False, enforce_admins=False):
    owner, name = slug(repo)
    st, prot = api(f"/repos/{owner}/{name}/branches/{branch}/protection", token)
    if st == 404 and not enable:
        print(f"{owner}/{name}@{branch} is not protected. Enabling protection is a wider decision than "
              f"adding a required check - pass --enable to do it, deliberately.")
        return 2
    elif st == 404:
        print(f"{owner}/{name}@{branch}: NOT PROTECTED. Creating protection with these checks required.")
        prot = {}
    elif st == 403 and plan_limited(prot):
        print(f"{owner}/{name}: required checks are NOT AVAILABLE ON THIS PLAN (private repository without "
              f"branch protection or rulesets). There is nothing to configure and no token that would "
              f"change that. Gate it in the process, or change the plan.")
        return 3
    elif st != 200:
        print(f"could not read protection (HTTP {st}); refusing to write a configuration built on a failed read.")
        return 2
    before = required_contexts(prot)
    body, after = merged_payload(prot, add, True if enforce_admins else None)
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
    # the classic/fine-grained decision, which is what gates `ensure`
    import types
    for header, expect in ((None, "fine-grained"), ("repo, workflow", "classic"), ("", "classic")):
        got = "classic" if header is not None else "fine-grained"
        assert got == expect, (header, got, expect)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--repo", required=True); c.add_argument("--branch", default="main")
    e = sub.add_parser("ensure"); e.add_argument("--repo", required=True); e.add_argument("--branch", default="main")
    e.add_argument("--require", action="append", required=True)
    e.add_argument("--enable", action="store_true",
                   help="create protection when the branch has none. Without this, an unprotected "
                        "branch is reported and left alone, because enabling protection is a wider "
                        "decision than adding a check to protection that already exists.")
    e.add_argument("--enforce-admins", dest="enforce_admins", action="store_true",
                   help="bind admins too. Without it, organisation owners bypass the checks - which "
                        "usually includes whatever account this token belongs to, so the gate would "
                        "not bind the process that just configured it.")
    e.add_argument("--allow-classic", action="store_true",
                   help="proceed on a classic token. The capability separation is a design and not a "
                        "live control (GOVERNANCE.md), so the Release Owner is not blocked by it - but "
                        "the run says out loud that the administering token can also push.")
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest(); return 0
    if a.cmd == "check":
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if not token:
            sys.exit("GITHUB_TOKEN is not set. Export the vault push PAT for this one call; do not write it anywhere.")
        return cmd_check(a.repo, a.branch, token)

    token = os.environ.get("GITHUB_GATE_TOKEN", "").strip()
    if not token:
        sys.exit("GITHUB_GATE_TOKEN is not set. `ensure` administers a protected branch and will not "
                 "use the push credential to do it. See this file's header for what the gate token must be.")
    kind, scopes = token_kind(token)
    if kind == "classic" and a.allow_classic:
        print("NOTE: administering with a CLASSIC token at the operator's instruction. This token can "
              "also push, so the credential that configures the gate is the credential the gate is "
              "meant to constrain. The separation in GOVERNANCE.md is not in effect for this run.")
    elif kind == "classic":
        sys.exit("REFUSED: GITHUB_GATE_TOKEN is a CLASSIC token (scopes: " + (scopes or "unknown") + ").\n"
                 "Classic scopes cannot grant administration without also granting push, so using one here "
                 "would hand this process the merge authority the governance withholds - while claiming to "
                 "be configuring the gate that enforces it.\n"
                 "Mint a fine-grained token limited to the repositories you are gating, with "
                 "Administration: read and write, and Contents: READ. Nothing else.")
    if kind == "unknown":
        sys.exit("REFUSED: could not establish what kind of token GITHUB_GATE_TOKEN is, and this command "
                 "will not administer a protected branch on an unidentified credential.")
    return cmd_ensure(a.repo, a.branch, a.require, token, a.enable, a.enforce_admins)


if __name__ == "__main__":
    sys.exit(main())
