#!/usr/bin/env python3
"""GA-013 part C: the watcher, run by .github/workflows/gstack-watch.yml.

  watch.py scan  --out work.json --log watch.jsonl        find moxywolf-agent's own pull requests that need work
  watch.py clone --work work.json --item N --dir D         clone item N's branch with a read-only token (not persisted)
  watch.py fix   --work work.json --item N --dir D --out R  run the Fix Contract with Claude; writes a bundle, pushes nothing
  watch.py push  --work work.json --item N --result R --dir D --log watch.jsonl   on a fresh runner: check, push, comment
  watch.py summary --log watch.jsonl                        one line per repository and pull request examined

Isolation (GA-013.11): the app key (MOXYWOLF_AGENT_APP_KEY) is used only inside scan, clone and push, by
this process, and never written anywhere a branch's code can read: its temp directory is removed before the
command returns. scan and clone mint read-only tokens; push mints the write token on a runner where no
branch code has run. fix runs the branch's code and has only the Anthropic key.
Never: merge, approve, close, force-push, or change a path the table owns or the closed lane matches.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import enclosure  # noqa: E402
import peer_review as pr  # noqa: E402

AGENT = "moxywolf-agent[bot]"
APP_ID = os.environ.get("GSTACK_WATCH_APP_ID", "5007349")
DEFAULT_INSTALLATION = os.environ.get("GSTACK_WATCH_INSTALLATION", "163156626")   # mint() resolves the real one per repo
LIST = ROOT / ".github" / "gstack-watch.json"
READ = {"contents": "read", "pull_requests": "read", "checks": "read"}
WRITE = {"contents": "write", "pull_requests": "write"}
MAX_TURNS = 40
API = os.environ.get("GSTACK_GITHUB_API", "https://api.github.com").rstrip("/")


def log(path, **entry):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def mint(repo, permissions):
    """A one-hour installation token for `repo`, from the app key in the environment. The key and the
    settings file live in a temp directory this call removes, so nothing outlasts it."""
    key = os.environ.get("MOXYWOLF_AGENT_APP_KEY", "").strip()
    if not key:
        sys.exit("missing secret MOXYWOLF_AGENT_APP_KEY: the watcher can't mint a token (GA-013.12)")
    import agent_token
    with tempfile.TemporaryDirectory() as d:
        Path(d, "key.pem").write_text(key + "\n")
        os.chmod(Path(d, "key.pem"), 0o600)
        Path(d, "github-app.env").write_text(f"GITHUB_APP_ID={APP_ID}\nGITHUB_APP_INSTALLATION_ID={DEFAULT_INSTALLATION}\n"
                                             "GITHUB_APP_KEY_FILE=key.pem\n")
        old = os.environ.get("GSTACK_AGENT_APP_ENV")
        os.environ["GSTACK_AGENT_APP_ENV"] = str(Path(d, "github-app.env"))
        try:
            return agent_token.mint(repo, permissions)
        finally:
            if old is None:
                os.environ.pop("GSTACK_AGENT_APP_ENV", None)
            else:
                os.environ["GSTACK_AGENT_APP_ENV"] = old


def rest(token):
    def call(method, path, body=None):
        req = urllib.request.Request(f"{API}/{path}", method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": "token " + token, "Accept": "application/vnd.github+json",
                                              "User-Agent": "gstack-watch"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"null")
    return call


def listed(path=None):
    path = Path(path or LIST)
    names = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(names, list) or not all(isinstance(n, str) and n.count("/") == 1 for n in names):
        sys.exit(f"{path} must be a JSON list of owner/name strings")
    return names


def triggers(call, name, p):
    """GA-013.9's three triggers for one pull request. ponytail: any failing check run counts, because the
    app can't read which checks branch protection requires; a check that can't be read is recorded, not a trigger."""
    n, head, out = p["number"], p["head"]["sha"], []
    try:
        runs = call("GET", f"repos/{name}/commits/{head}/check-runs?per_page=100").get("check_runs") or []
        failed = sorted({r["name"] for r in runs if r.get("conclusion") in ("failure", "timed_out")})
        if failed:
            out.append({"kind": "failing_check", "checks": failed})
    except Exception as e:
        out.append({"kind": "checks_unreadable", "why": str(e)[:200]})
    if call("GET", f"repos/{name}/pulls/{n}").get("mergeable") is False:
        out.append({"kind": "merge_conflict"})
    since = call("GET", f"repos/{name}/commits/{head}")["commit"]["committer"]["date"]
    comments = [c for c in (call("GET", f"repos/{name}/pulls/{n}/comments?per_page=100") or [])
                + (call("GET", f"repos/{name}/issues/{n}/comments?per_page=100") or [])
                if (c.get("user") or {}).get("login") != AGENT and c.get("created_at", "") > since]
    if comments:
        out.append({"kind": "review_comment", "comments": [
            {"by": c["user"]["login"], "body": c.get("body", "")[:4000], "path": c.get("path"), "line": c.get("line"),
             "url": c.get("html_url")} for c in comments]})
    return out


def scan(names, call_for, log_path):
    """Work items for the listed repositories. Every pull request examined is logged, skipped or not."""
    items = []
    for name in names:
        call = call_for(name)
        prs = call("GET", f"repos/{name}/pulls?state=open&per_page=100") or []
        log(log_path, step="scan", repo=name, open_pulls=len(prs))
        for p in prs:
            why = ("not opened by the agent" if (p.get("user") or {}).get("login") != AGENT
                   else "from a fork" if ((p.get("head") or {}).get("repo") or {}).get("full_name") != name
                   else "not a build/ or goal/ branch" if not p["head"]["ref"].startswith(("build/", "goal/"))
                   else None)
            if why:
                log(log_path, step="scan", repo=name, pr=p["number"], skipped=why)
                continue
            found = triggers(call, name, p)
            act = [t for t in found if t["kind"] != "checks_unreadable"]
            log(log_path, step="scan", repo=name, pr=p["number"], triggers=[t["kind"] for t in found])
            if act:
                items.append({"repo": name, "number": p["number"], "branch": p["head"]["ref"], "head": p["head"]["sha"],
                              "base": p["base"]["ref"], "triggers": act})
    return items


def protected(dirpath, old, new, base_ref):
    """The watcher's own changed paths (changed from both the old head and the base, so a path that arrived
    from the base through a merge isn't the watcher's) that the table owns, CODEOWNERS owns, the closed lane
    matches, or that are a symlink or submodule. Any of these and nothing is pushed."""
    d = str(dirpath)
    mine = set(pr.git(d, "diff", "--name-only", "-z", old, new).split("\0")) & \
        set(pr.git(d, "diff", "--name-only", "-z", f"origin/{base_ref}", new).split("\0"))
    mine.discard("")
    table, _ = pr.lane_table({"path": d, "head": new})
    closed = (table.get("lanes") or {}).get("closed") or {}
    owned = pr._owned_globs({"path": d, "head": new})
    modes = {}
    for line in pr.git(d, "diff", "--raw", old, new).splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            modes[parts[-1]] = [x.lstrip(":") for x in parts[0].split()[:2]]
    return [path for path in sorted(mine)
            if pr._lane_matches(path, closed.get("paths") or ()) or pr.owners_for(path, table.get("owned"))
            or pr._lane_matches(path, owned) or {"120000", "160000"} & set(modes.get(path, []))]


def fix_contract():
    text = (HERE.parent / "commands" / "gstack-ship.md").read_text(encoding="utf-8")
    m = re.search(r"^## The Fix Contract.*?(?=^## )", text, re.S | re.M)
    return m.group(0) if m else ""


def prompt(item):
    parts = [f"You are the gstack watcher on {item['repo']} pull request #{item['number']} (branch {item['branch']}).",
             "Work only on the triggers below, in this checkout. Commit what you change, with a plain-text message. "
             "Never push, merge, approve, force-push, rebase or close anything. Never change .github/, any hooks/ "
             "directory, migrations, CODEOWNERS, .gitattributes, .gitmodules, .gstack/ or a release-lanes.json; "
             "if a trigger needs that, make no change and say so.", fix_contract(), "Triggers:"]
    for t in item["triggers"]:
        if t["kind"] == "review_comment":
            for c in t["comments"]:
                parts.append(enclosure.enclose(f"review comment by {c['by']} on {c.get('path') or 'the pull request'}",
                                               c["body"]))
        else:
            parts.append(json.dumps(t))
    parts.append('End with one line of JSON: {"outcome": "fixed" | "judgment" | "nothing", "note": "<one sentence>"}.')
    return "\n\n".join(parts)


def run_claude(text, cwd):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("missing secret GSTACK_WATCH_ANTHROPIC_KEY: the fix step has no Anthropic key (GA-013.12)")
    return subprocess.run(["claude", "-p", text, "--max-turns", str(MAX_TURNS), "--permission-mode", "bypassPermissions"],
                          cwd=cwd, capture_output=True, text=True, timeout=3000).stdout


def fix(item, dirpath, out, claude=run_claude):
    """Merge the base in for a conflict (never a rebase), then let Claude work the triggers. Writes
    out/result.json and, when there are new commits, out/watch.bundle. Pushes nothing."""
    d, out = str(dirpath), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", d, "fetch", "-q", "origin", item["base"]], capture_output=True)
    if any(t["kind"] == "merge_conflict" for t in item["triggers"]):
        subprocess.run(["git", "-C", d, "merge", "--no-edit", f"origin/{item['base']}"], capture_output=True)
    said = claude(prompt(item), d) or ""
    last = next((l for l in reversed(said.strip().splitlines()) if l.strip().startswith("{")), "")
    try:
        result = json.loads(last)
    except json.JSONDecodeError:
        result = {"outcome": "judgment", "note": "the fix step ended without an outcome line"}
    if pr.git(d, "diff", "--name-only", "--diff-filter=U"):
        subprocess.run(["git", "-C", d, "merge", "--abort"], capture_output=True)
        result = {"outcome": "judgment", "note": "the merge with the base left conflicts"}
    new = pr.git(d, "rev-parse", "HEAD")
    if new != item["head"] and result.get("outcome") == "fixed":
        pr.git(d, "bundle", "create", str(out / "watch.bundle"), f"{item['head']}..HEAD")
        result["new_head"] = new
    (out / "result.json").write_text(json.dumps(result))
    return result


def push(item, result, dirpath, call, git_env, log_path):
    """On a fresh runner: check the watcher's change, then push it as a fast-forward and comment; or comment the
    judgment. Never merges, approves, force-pushes or closes."""
    d, name, n, old = str(dirpath), item["repo"], item["number"], item["head"]
    kinds = ", ".join(t["kind"] for t in item["triggers"])
    new = result.get("new_head")
    if not new:
        call("POST", f"repos/{name}/issues/{n}/comments",
             {"body": f"gstack-watch: no change pushed for {kinds}: {result.get('note', '')}"[:3000]})
        log(log_path, step="push", repo=name, pr=n, outcome=result.get("outcome"), note=result.get("note"))
        return "commented"
    if subprocess.run(["git", "-C", d, "merge-base", "--is-ancestor", old, new]).returncode:
        reason = "the new head doesn't descend from the reviewed head, and the watcher never force-pushes"
    else:
        hit = protected(d, old, new, item["base"])
        reason = f"it changes protected paths {hit}" if hit else None
    if reason:
        call("POST", f"repos/{name}/issues/{n}/comments", {"body": f"gstack-watch: not pushed, because {reason}."})
        log(log_path, step="push", repo=name, pr=n, outcome="refused", note=reason)
        return "refused"
    subprocess.run(["git", "-C", d, "push", "origin", f"{new}:refs/heads/{item['branch']}"], check=True, env=git_env)
    call("POST", f"repos/{name}/issues/{n}/comments", {"body": (
        f"gstack-watch pushed {new[:7]} for {kinds}: {result.get('note', '')}\n\n"
        f"Any gstack review of this pull request covers {old[:7]}, an old head now; a new round is needed.")[:3000]})
    log(log_path, step="push", repo=name, pr=n, outcome="pushed", head=new)
    return "pushed"


def summary(log_path):
    p = Path(log_path)
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
    prs = {(r["repo"], r["pr"]) for r in rows if r.get("pr")}
    lines = [f"gstack-watch: {len({r['repo'] for r in rows})} repositories, {len(prs)} pull requests examined"]
    if not prs:
        lines.append("examined no pull requests (EV-001)")
    return "\n".join(lines + [json.dumps(r) for r in rows])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("scan", "clone", "fix", "push", "summary"))
    for flag in ("--out", "--log", "--work", "--dir", "--result"):
        ap.add_argument(flag)
    ap.add_argument("--item", type=int)
    a = ap.parse_args(argv)
    if a.action == "summary":
        text = summary(a.log)
        print(text)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
                f.write("```\n" + text + "\n```\n")
        return 0
    if a.action == "scan":
        items = scan(listed(), lambda name: rest(mint(name, READ)), a.log)
        Path(a.out).write_text(json.dumps(items))
        print(json.dumps(list(range(len(items)))))   # the workflow's matrix
        return 0
    item = json.loads(Path(a.work).read_text())[a.item]
    import agent_token
    if a.action == "clone":
        env = agent_token.token_env(mint(item["repo"], READ))
        subprocess.run(["git", "clone", "-q", "--branch", item["branch"], f"https://github.com/{item['repo']}.git", a.dir],
                       check=True, env=env)
        return 0
    if a.action == "fix":
        print(json.dumps(fix(item, a.dir, a.out)))
        return 0
    result = json.loads(Path(a.result).read_text())
    token = mint(item["repo"], WRITE)
    env = agent_token.token_env(token)
    subprocess.run(["git", "clone", "-q", "--branch", item["branch"], f"https://github.com/{item['repo']}.git", a.dir],
                   check=True, env=env)
    subprocess.run(["git", "-C", a.dir, "fetch", "-q", "origin", item["base"]], check=True, env=env)
    bundle = Path(a.result).with_name("watch.bundle")
    if bundle.exists():
        subprocess.run(["git", "-C", a.dir, "fetch", "-q", str(bundle), "HEAD"], check=True)
    print(push(item, result, a.dir, rest(token), env, a.log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
