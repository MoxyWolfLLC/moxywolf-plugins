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


SECRETS = ("MOXYWOLF_AGENT_APP_KEY", "GSTACK_WATCH_ANTHROPIC_KEY")


def preflight(log_path):
    """GA-013 review F8/F9: both secrets, checked every run before any work, whether or not a pull request
    needs fixing. Their presence is recorded on the run's log, which is the artifact; a missing one fails the run."""
    missing = [k for k in SECRETS if not os.environ.get(k, "").strip()]
    log(log_path, step="preflight", missing=missing)
    if missing:
        sys.exit(f"missing secret(s) {', '.join(missing)}: the watcher can't run (GA-013.12)")
    return 0


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


THREADS = """query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n){pullRequest(number:$p){
reviewThreads(first:100){nodes{isResolved comments(first:50){nodes{author{login} body createdAt url path line}}}}}}}"""


def required_checks(call, name, branch):
    """The status checks the base branch's rulesets require, or None when they can't be read. ponytail: classic
    branch protection isn't readable by the app, so a repository protected only that way has none here."""
    try:
        rules = call("GET", f"repos/{name}/rules/branches/{branch}") or []
    except Exception:
        return None
    return sorted({c["context"] for r in rules if r.get("type") == "required_status_checks"
                   for c in (r.get("parameters") or {}).get("required_status_checks") or []})


def triggers(call, name, p):
    """GA-013.9's three triggers for one pull request (review F6): a failing REQUIRED check, a merge conflict,
    and an UNRESOLVED review thread with a comment newer than the head that the agent didn't write. Ordinary
    conversation comments don't count. What can't be read is recorded, never a trigger."""
    n, head, out = p["number"], p["head"]["sha"], []
    required = required_checks(call, name, p["base"]["ref"])
    if required is None:
        out.append({"kind": "required_checks_unreadable"})
    elif required:
        try:
            runs = call("GET", f"repos/{name}/commits/{head}/check-runs?per_page=100").get("check_runs") or []
            failed = sorted({r["name"] for r in runs if r["name"] in required and r.get("conclusion") in ("failure", "timed_out")})
            if failed:
                out.append({"kind": "failing_check", "checks": failed})
        except Exception as e:
            out.append({"kind": "checks_unreadable", "why": str(e)[:200]})
    if call("GET", f"repos/{name}/pulls/{n}").get("mergeable") is False:
        out.append({"kind": "merge_conflict"})
    since = call("GET", f"repos/{name}/commits/{head}")["commit"]["committer"]["date"]
    owner, repo = name.split("/")
    data = call("POST", "graphql", {"query": THREADS, "variables": {"o": owner, "n": repo, "p": n}}) or {}
    threads = ((((data.get("data") or {}).get("repository") or {}).get("pullRequest") or {}).get("reviewThreads") or {}).get("nodes")
    if threads is None:
        out.append({"kind": "threads_unreadable"})
        threads = []
    comments = [c for t in threads if not t.get("isResolved") for c in (t.get("comments") or {}).get("nodes") or []
                if ((c.get("author") or {}).get("login") or "") not in (AGENT, "moxywolf-agent") and c.get("createdAt", "") > since]
    if comments:
        out.append({"kind": "review_comment", "comments": [
            {"by": (c.get("author") or {}).get("login"), "body": c.get("body", "")[:4000], "path": c.get("path"),
             "line": c.get("line"), "url": c.get("url")} for c in comments]})
    return out


NOT_TRIGGERS = {"required_checks_unreadable", "checks_unreadable", "threads_unreadable"}


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
            act = [t for t in found if t["kind"] not in NOT_TRIGGERS]
            log(log_path, step="scan", repo=name, pr=p["number"], triggers=[t["kind"] for t in found])
            if act:
                items.append({"repo": name, "number": p["number"], "branch": p["head"]["ref"], "head": p["head"]["sha"],
                              "base": p["base"]["ref"], "triggers": act})
    return items


def _blob(d, rev, path):
    r = subprocess.run(["git", "-C", d, "rev-parse", "-q", "--verify", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def is_protected(d, heads, paths, effects=None):
    """The paths, of `paths`, that are protected at ANY of `heads` (review F13: the old head as well as the new,
    so removing or replacing a submodule or symlink, or a rule that protected it, still counts): owned by the
    table or CODEOWNERS, matched by the closed lane, or a symlink or submodule."""
    heads = [heads] if isinstance(heads, str) else list(heads)
    effects = effects or {}
    checks = []
    for h in heads:
        table, _ = pr.lane_table({"path": d, "head": h})
        closed = ((table.get("lanes") or {}).get("closed") or {})
        checks.append((h, closed.get("paths") or (), set(closed.get("effects") or ()),
                       pr.owned_check({"path": d, "head": h}, table)))
    hit = []
    for path in sorted(paths):
        for h, closed, closed_effects, owned in checks:
            mode = subprocess.run(["git", "-C", d, "ls-tree", h, "--", path], capture_output=True, text=True).stdout.split()[:1]
            if (pr._lane_matches(path, closed) or owned(path) or mode in (["120000"], ["160000"])
                    or closed_effects & set(effects.get(path, ()))):   # review r3 F2: a closed effect, such as a deletion
                hit.append(path)
                break
    return hit


def protected(dirpath, old, new, merged_base=None, base_ref="main"):
    """Review F7: the watcher's own change is every path old..new touches, less only what a merge of the specific
    base commit `merged_base` brought in cleanly (a path the base changed since the fork, with the base's exact
    content at the new head). A path reverted to the base, or deleted when the base never had it, is still the
    watcher's. Any protected path among them and nothing is pushed."""
    d = str(dirpath)
    mine = set(pr.changed_paths(d, old, new))
    if merged_base and verified_merge(d, old, new, merged_base, base_ref):
        fork = pr.git(d, "merge-base", old, merged_base)
        mine -= {p for p in pr.changed_paths(d, fork, merged_base) if _blob(d, new, p) == _blob(d, merged_base, p)}
    effects = {}
    for path, eff, _ in pr.diff_entries(pr.git(d, "diff", "--raw", "-z", f"{old}..{new}")):
        effects.setdefault(path, set()).update(eff)
    return is_protected(d, [old, new], mine, effects)


def verified_merge(d, old, new, merged_base, base_ref):
    """Review F7: the fix step's claim of which base commit it merged is believed only when this runner can see
    it is true: the commit is on the base branch as fetched here, and a merge commit in old..new has it as a
    parent. Otherwise nothing is exempt."""
    on_base = not subprocess.run(["git", "-C", d, "merge-base", "--is-ancestor", merged_base, f"origin/{base_ref}"]).returncode
    merges = pr.git(d, "rev-list", "--merges", "--parents", f"{old}..{new}").splitlines()
    return on_base and any(merged_base in line.split()[2:] for line in merges)


def fix_contract():
    """The Fix Contract section of plugins/gstack-execution/commands/gstack-ship.md, given to Claude."""
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
    d, out = str(dirpath), Path(out).resolve()   # review r3 F1: git runs in the clone, so a relative out would land there
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", d, "fetch", "-q", "origin", item["base"]], capture_output=True)
    merged_base = None
    if any(t["kind"] == "merge_conflict" for t in item["triggers"]):
        merged_base = pr.git(d, "rev-parse", f"origin/{item['base']}")
        subprocess.run(["git", "-C", d, "merge", "--no-edit", merged_base], capture_output=True)
        conflicted = [f for f in pr.git(d, "diff", "--name-only", "--diff-filter=U").split("\n") if f]
        hit = is_protected(d, [item["head"], merged_base], conflicted)   # review F7/F13: refused before Claude sees it
        if hit:
            subprocess.run(["git", "-C", d, "merge", "--abort"], capture_output=True)
            result = {"outcome": "judgment", "note": f"the merge with the base conflicts in protected paths {hit}"}
            (out / "result.json").write_text(json.dumps(result))
            return result
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
        if merged_base:
            result["merged_base"] = merged_base
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
        hit = protected(d, old, new, result.get("merged_base"), item["base"])
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
    missing = [m for r in rows if r.get("step") == "preflight" for m in r.get("missing") or []]
    lines = [f"gstack-watch: {len({r['repo'] for r in rows if r.get('repo')})} repositories, {len(prs)} pull requests examined"]
    if missing:
        lines.append(f"run failed: missing secret(s) {', '.join(missing)}")
    elif not any(r.get("step") == "preflight" for r in rows):
        lines.append("run failed before its preflight was recorded")
    if not prs:
        lines.append("examined no pull requests (EV-001)")
    # review r3 F3: a triggered pull request whose fix job died before logging is still named
    done = {(r["repo"], r["pr"]) for r in rows if r.get("step") in ("fix", "push") and r.get("pr")}
    for r in rows:
        if r.get("step") == "fix":
            lines.append(f"{r['repo']}#{r['pr']} fix: {r.get('outcome')}: {r.get('note') or ''}")
    for r in rows:
        if (r.get("step") == "scan" and r.get("pr") and (r["repo"], r["pr"]) not in done
                and any(k not in NOT_TRIGGERS for k in r.get("triggers") or ())):
            lines.append(f"{r['repo']}#{r['pr']}: triggered, but no fix or push outcome was recorded")
    return "\n".join(lines + [json.dumps(r) for r in rows])


def fetch_bundle(d, result_path):
    """Fetch the fix job's commits, if it made any, from the bundle beside result.json."""
    bundle = Path(result_path).resolve().with_name("watch.bundle")   # review r3 F11: git runs in the clone
    if bundle.exists():
        subprocess.run(["git", "-C", d, "fetch", "-q", str(bundle), "HEAD"], check=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("preflight", "scan", "clone", "fix", "push", "summary"))
    for flag in ("--out", "--log", "--work", "--dir", "--result"):
        ap.add_argument(flag)
    ap.add_argument("--item", type=int)
    a = ap.parse_args(argv)
    if a.action == "preflight":
        return preflight(a.log)
    if a.action == "summary":
        text = summary(a.log)
        print(text)
        if a.out:
            Path(a.out).write_text(text + "\n")
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
        try:
            result = fix(item, a.dir, a.out)
        except Exception as e:   # review r3 F3: a timeout or a failed bundle is an outcome, recorded like any other
            result = {"outcome": "failed", "note": f"{type(e).__name__}: {e}"[:500]}
            Path(a.out).mkdir(parents=True, exist_ok=True)
            (Path(a.out) / "result.json").write_text(json.dumps(result))
        if a.log:
            log(a.log, step="fix", repo=item["repo"], pr=item["number"], outcome=result.get("outcome"), note=result.get("note"))
        print(json.dumps(result))
        return 0
    result = json.loads(Path(a.result).read_text())
    token = mint(item["repo"], WRITE)
    env = agent_token.token_env(token)
    subprocess.run(["git", "clone", "-q", "--branch", item["branch"], f"https://github.com/{item['repo']}.git", a.dir],
                   check=True, env=env)
    subprocess.run(["git", "-C", a.dir, "fetch", "-q", "origin", item["base"]], check=True, env=env)
    fetch_bundle(a.dir, a.result)
    print(push(item, result, a.dir, rest(token), env, a.log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
