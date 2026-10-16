#!/usr/bin/env python3
"""BP-001: ship a Release-Owner-signed post. The writer never pushes, merges or pulls.

  ship.py push        --repo <path> --branch <name> [--state <state.md>]
  ship.py merge       --repo <path> --slug <owner/name> --branch <name> --base <name> --head <sha>
                      --checks <a,b> [--title T] [--body B] [--deadline S] [--state <state.md>]
  ship.py verify-live --url <post url> --hub-path <path> --term <hub term>
                      [--deadline S] [--state <state.md>]

Exit codes: 0 done; 1 refused, with the reason on stderr; 2 usage.

push    pushes the branch, then requires `git ls-remote` to equal local HEAD. A push to GitHub runs
        through gstack-execution's agent_token.py (GA-005), so it acts as moxywolf-agent; a push to
        any other remote (a local bare repository in the tests) runs plain git. With --state (an
        unprotected target, where the push is the publish) it writes published_pr: none,
        published_merge: <the pushed SHA> and live_verified_at: pending. A protected target's push
        omits --state, so a merge that never happens leaves the previous record alone.
merge   opens (or reuses) the pull request, waits until every named check has completed, merges
        pinned to the head it was given only when every one concluded success, then pulls the base
        branch back into the local clone with --ff-only and requires remote == local. --head is the
        SHA push printed; it's passed through unchanged, so a branch that moved after the push can't
        be merged in its place. A check that
        never appears before the deadline is a failure, never a pass.
verify-live fetches the live post until it answers 200, then requires an <a> whose href ends in the
        hub path and whose whole text, whitespace collapsed and case ignored, equals the hub term. It writes live_verified_at only on success.

ponytail: stdlib only; the GitHub calls go through one `api` function so the tests can serve fixtures
without reaching GitHub (XE-019).
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

AGENT_TOKEN = Path(__file__).resolve().parents[2] / "gstack-execution" / "scripts" / "agent_token.py"


class Refusal(Exception):
    pass


def _on_github(repo):
    url = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                         capture_output=True, text=True).stdout.strip()
    return "github.com" in url


def git(repo, *args, auth=False):
    cmd = ["git", "-C", str(repo), *args]
    if auth and _on_github(repo):
        cmd = [sys.executable, str(AGENT_TOKEN), "exec", "--", *cmd]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        err = (r.stderr or r.stdout).strip()
        if "protected branch" in err:
            raise Refusal(f"push refused: {args[-1]} is protected. Set default_branch_protected: true "
                          "in the target descriptor so /blog-publish ships through a pull request.")
        raise Refusal(f"git {' '.join(args)} failed: {err[-400:]}")
    return r.stdout.strip()


def remote_sha(repo, branch):
    out = git(repo, "ls-remote", "origin", f"refs/heads/{branch}", auth=True)
    return out.split()[0] if out else ""


def push(repo, branch):
    git(repo, "push", "-u", "origin", branch, auth=True)
    local, remote = git(repo, "rev-parse", "HEAD"), remote_sha(repo, branch)
    if local != remote:
        raise Refusal(f"after push, remote {branch} is {remote or 'absent'} and local HEAD is {local}")
    return local


def pull_back(repo, base):
    git(repo, "fetch", "origin", auth=True)
    git(repo, "switch", base)
    git(repo, "pull", "--ff-only", "origin", base, auth=True)
    local, remote = git(repo, "rev-parse", "HEAD"), remote_sha(repo, base)
    if local != remote:
        raise Refusal(f"after pull-back, remote {base} is {remote} and local is {local}")
    return local


def agent_api(method, path, data=None):
    cmd = [sys.executable, str(AGENT_TOKEN), "api", method, path]
    if data is not None:
        cmd += ["--data", "-"]
    r = subprocess.run(cmd, input=json.dumps(data) if data is not None else None,
                       capture_output=True, text=True)
    if r.returncode:
        raise Refusal(f"{method} {path} failed: {(r.stderr or r.stdout).strip()[-400:]}")
    return json.loads(r.stdout or "null")


def wait_for_checks(api, slug, head, checks, deadline, poll):
    """Return when every named check concluded success; refuse on any other conclusion or at the deadline."""
    end = time.monotonic() + deadline
    while True:
        runs = api("GET", f"repos/{slug}/commits/{head}/check-runs?per_page=100").get("check_runs", [])
        latest = {}
        for run in sorted(runs, key=lambda r: r.get("id", 0)):
            latest[run["name"]] = run
        bad = [f"{n}: {latest[n].get('conclusion')}" for n in checks
               if n in latest and latest[n].get("status") == "completed"
               and latest[n].get("conclusion") != "success"]
        if bad:
            raise Refusal("required check failed: " + "; ".join(bad))
        waiting = [n for n in checks if n not in latest or latest[n].get("status") != "completed"]
        if not waiting:
            return
        if time.monotonic() >= end:
            raise Refusal("required check not complete at the deadline: " + ", ".join(
                f"{n} ({'never appeared' if n not in latest else latest[n].get('status')})" for n in waiting))
        time.sleep(poll)


def merge(api, repo, slug, branch, base, head, checks, title, body, deadline=1800, poll=20):
    owner = slug.split("/")[0]
    prs = api("GET", f"repos/{slug}/pulls?head={owner}:{branch}&state=open")
    pr = prs[0] if prs else api("POST", f"repos/{slug}/pulls",
                                {"title": title, "head": branch, "base": base, "body": body})
    if pr["head"]["sha"] != head:
        raise Refusal(f"pull request #{pr['number']} head is {pr['head']['sha']}, not the pushed {head}")
    wait_for_checks(api, slug, head, checks, deadline, poll)
    res = api("PUT", f"repos/{slug}/pulls/{pr['number']}/merge", {"sha": head, "merge_method": "merge"})
    if not res.get("merged"):
        raise Refusal(f"merge of #{pr['number']} refused: {res.get('message')}")
    local = pull_back(repo, base)
    if local != res["sha"]:
        raise Refusal(f"merge commit {res['sha']} is not the pulled-back head {local}")
    return pr["number"], res["sha"]


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href") or "", []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text)))
            self._href = None


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError:
        return 0, ""


def verify_live(url, hub_path, term, deadline=600, poll=20, get=fetch):
    end = time.monotonic() + deadline
    while True:
        status, html = get(url)
        if status == 200:
            break
        if time.monotonic() >= end:
            raise Refusal(f"not_live: {url} answered {status or 'nothing'} at the deadline")
        time.sleep(poll)
    p = _Anchors()
    p.feed(html)
    want, norm = hub_path.rstrip("/"), (lambda x: " ".join(x.split()).lower())
    if not any(h.split("#")[0].split("?")[0].rstrip("/").endswith(want) and norm(t) == norm(term)
               for h, t in p.links):
        raise Refusal(f"hub_link_missing: {url} has no link to {hub_path} on the term '{term}'")


def set_state(path, fields):
    """Set frontmatter keys in a piece's state.md, adding any that are absent."""
    p = Path(path)
    text = p.read_text()
    head, sep, rest = text.partition("\n---\n")
    for k, v in fields.items():
        line = f"{k}: {v}"
        head, n = re.subn(rf"^{re.escape(k)}:.*$", line, head, flags=re.M)
        if not n:
            head += "\n" + line
    p.write_text(head + sep + rest)


def main(argv=None):
    ap = argparse.ArgumentParser(description="BP-001 ship a signed post")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("push")
    a.add_argument("--repo", required=True)
    a.add_argument("--branch", required=True)
    a.add_argument("--state")
    m = sub.add_parser("merge")
    for f in ("--repo", "--slug", "--branch", "--base", "--head", "--checks"):
        m.add_argument(f, required=True)
    m.add_argument("--title", default="Publish")
    m.add_argument("--body", default="Published via /4d-blog-engine:blog-publish (BP-001).")
    m.add_argument("--deadline", type=int, default=1800)
    m.add_argument("--state")
    v = sub.add_parser("verify-live")
    for f in ("--url", "--hub-path", "--term"):
        v.add_argument(f, required=True)
    v.add_argument("--deadline", type=int, default=600)
    v.add_argument("--state")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "push":
            sha = push(args.repo, args.branch)
            if args.state:
                set_state(args.state, {"published_pr": "none", "published_merge": sha, "live_verified_at": "pending"})
            print(f"pushed {args.branch}: remote == local == {sha}")
        elif args.cmd == "merge":
            checks = [c.strip() for c in args.checks.split(",") if c.strip()]
            n, sha = merge(agent_api, args.repo, args.slug, args.branch, args.base, args.head, checks,
                           args.title, args.body, args.deadline)
            if args.state:
                set_state(args.state, {"published_pr": n, "published_merge": sha, "live_verified_at": "pending"})
            print(f"merged #{n} as {sha}; {args.base} pulled back, remote == local")
        else:
            verify_live(args.url, args.hub_path, args.term, args.deadline)
            if args.state:
                set_state(args.state, {"live_verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
            print(f"live: {args.url} links '{args.term}' to {args.hub_path}")
    except Refusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
