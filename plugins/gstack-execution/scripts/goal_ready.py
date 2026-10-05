#!/usr/bin/env python3
"""GO-008: is a repository ready for goal mode? Read-only, through the GitHub API.

  agent_token.py exec -- python3 plugins/gstack-execution/scripts/goal_ready.py <owner>/<repo>

Run it from a moxywolf-plugins checkout: the goal workflows and scripts a governed repository needs are
compared with this checkout's HEAD. One line per requirement, `ready`, `missing` or `unknown` (the API
wouldn't say), then a count. Exit 0 only when every requirement is ready; unknown is not ready.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_brief as gb  # noqa: E402
import goal_guard  # noqa: E402
import test_codeowners as co  # noqa: E402  goal_brief put .github on the path; one CODEOWNERS reader

ROOT = Path(__file__).resolve().parents[3]
OWNER = "@dorianatmoxywolf"
SCRIPTS = "plugins/gstack-execution/scripts/"
CHECKS = ["tests"] + [w[:-4] for w in goal_guard.GOAL_WORKFLOWS]


class Unknown(Exception):
    pass


def api(token):
    def get(path):
        req = urllib.request.Request("https://api.github.com/" + path, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise Unknown(f"HTTP {e.code} on {path}")
    return get


def local_tree(prefix):
    """{path: blob sha} for tracked files under prefix at this checkout's HEAD, tests left out."""
    out = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-r", "HEAD", prefix], text=True)
    rows = (ln.split(None, 3) for ln in out.splitlines())
    return {p: sha for _, _, sha, p in rows if not Path(p).name.startswith("test_")}


def gate_paths():
    """Every file this checkout tracks that its own CODEOWNERS gives Dorian: the gate a governed repository
    must keep under his review, workflows, scripts, goal folders and hooks alike."""
    rs = co.rules((ROOT / ".github/CODEOWNERS").read_text())
    files = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True).splitlines()
    return [p for p in files if OWNER in co.owners(rs, p)]


def text_at(get, repo, path, ref):
    c = get(f"repos/{repo}/contents/{path}?ref={ref}")
    return base64.b64decode(c["content"]).decode() if c and c.get("content") is not None else None


def requirements(repo, get):
    """[(name, status, detail)] for every requirement, in order. Never raises for one requirement's failure."""
    out = []

    def req(name, fn):
        try:
            ok, detail = fn()
            out.append((name, "ready" if ok else "missing", detail))
        except Unknown as e:
            out.append((name, "unknown", str(e)))

    meta = {}

    def access():
        r = get(f"repos/{repo}")
        if not r:
            return False, "the token can't see this repository; install the moxywolf-agent app on it"
        meta.update(r)
        get(f"repos/{repo}/commits/main/check-runs?per_page=1")      # a refusal here is unknown, never ready:
        get(f"repos/{repo}/deployments?per_page=1")                 # a run decides merges and deploys from both
        return r.get("default_branch") == "main", (f"default branch {r.get('default_branch')!r} (goal mode needs main); "
                                                   "checks and deployments readable")
    req("app can read it, default branch main", access)
    if not meta:
        return out

    def design():
        t = text_at(get, repo, "DESIGN.md", "main")
        objs = gb.objectives(t) if t else []
        return bool(objs), f"{len(objs)} objective headings in DESIGN.md" if t else "no DESIGN.md on main"
    req("DESIGN.md with objectives (a goal serves one)", design)

    def codeowners():
        need = gate_paths()
        rs = co.rules(text_at(get, repo, ".github/CODEOWNERS", "main") or "")
        # ponytail: test_codeowners matches anchored paths, dir/ and **/name/ only. A pattern outside that
        # subset (a catch-all, an unanchored glob) could override Dorian unseen, so it's refused, not guessed.
        odd = [pat for pat, _ in rs if not (pat.startswith("/") and "**" not in pat)
               and not (pat.startswith("**/") and pat.endswith("/") and "*" not in pat[3:])]
        if odd:
            return False, f"CODEOWNERS uses patterns this check can't evaluate, so ownership can't be shown: {odd[:5]}"
        lack = [p for p in need if OWNER not in co.owners(rs, p)]   # last matching rule wins, as on GitHub
        return bool(need) and not lack, f"{len(need) - len(lack)}/{len(need)} gate paths owned by {OWNER}" + \
            (f"; not: {lack[:5]}{' ...' if len(lack) > 5 else ''}" if lack else "")
    req("CODEOWNERS names Dorian on goal mode's gate paths", codeowners)

    def workflows():
        text = text_at(get, repo, goal_guard.PIN_FILE, "main")
        if text is None:
            return False, f"no {goal_guard.PIN_FILE} pinning the repository's own checks (tests.yml first)"
        try:
            own = goal_guard.own_pins(text)                  # the same rules goal_run start applies
        except ValueError as e:
            return False, str(e)
        pins = {**own, **goal_guard.GOAL_WORKFLOWS}
        texts = {w: text_at(get, repo, f".github/workflows/{w}", "main") for w in pins}
        bad = [w for w in pins if texts[w] is None or hashlib.sha256(texts[w].encode()).hexdigest() != pins[w]]
        return not bad, (f"{len(pins)} workflows match their pins ({len(own)} in {goal_guard.PIN_FILE})" if not bad else
                         f"absent or not the pinned content: {bad} (goal_run start refuses a check that isn't pinned)")
    req("checks pinned: the goal workflows and the repository's own", workflows)

    def scripts():
        tree = get(f"repos/{repo}/git/trees/main?recursive=1") or {}
        if tree.get("truncated"):
            raise Unknown("the repository tree is too large to list in one call")
        theirs = {e["path"]: e["sha"] for e in tree.get("tree", []) if e.get("type") == "blob"}
        mine = local_tree(SCRIPTS)
        lack = sorted(p for p, sha in mine.items() if theirs.get(p) != sha)
        return not lack, f"{len(mine) - len(lack)}/{len(mine)} goal-mode scripts match this checkout" + \
            (f"; differ or absent: {len(lack)} (first: {lack[0]})" if lack else "")
    req("goal-mode scripts, same as this checkout", scripts)

    def ruleset():
        rules, page = [], 1
        while True:   # every applicable rule from every ruleset, all pages
            batch = get(f"repos/{repo}/rules/branches/main?per_page=100&page={page}") or []
            rules += batch
            if len(batch) < 100:
                break
            page += 1
        kinds = {r["type"] for r in rules}
        ctx = {c["context"] for r in rules if r["type"] == "required_status_checks"
               for c in (r.get("parameters") or {}).get("required_status_checks", [])}
        lack = [c for c in CHECKS if c not in ctx]
        if not any((r.get("parameters") or {}).get("require_code_owner_review") for r in rules if r["type"] == "pull_request"):
            lack.insert(0, "code-owner review")
        for k in ("non_fast_forward", "deletion"):
            if k not in kinds:
                lack.append(f"{k} blocked")
        return not lack, "main requires a pull request, code-owner review and " + ", ".join(CHECKS) if not lack \
            else f"main's rules lack: {lack}"
    req("main's ruleset", ruleset)

    def environment():
        env = get(f"repos/{repo}/environments/goal-holdout")
        if not env:
            return False, "no goal-holdout environment"
        pol = env.get("deployment_branch_policy") or {}
        pols = (get(f"repos/{repo}/environments/goal-holdout/deployment-branch-policies?per_page=100") or {}) \
            .get("branch_policies", []) if pol.get("custom_branch_policies") else []
        seen = [(p.get("type", "?"), p["name"]) for p in pols]
        return seen == [("branch", "main")], f"deploys from {seen or 'anywhere'} (must be the branch main only)"
    req("goal-holdout environment, main only", environment)
    return out


def main(argv):
    if len(argv) != 1 or "/" not in argv[0]:
        print(__doc__, file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("refused: no GITHUB_TOKEN; run it under agent_token.py exec", file=sys.stderr)
        return 2
    rows = requirements(argv[0], api(token))
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], text=True).strip()
    if len(rows) == 1 and rows[0][1] != "ready":
        name, status, detail = rows[0]
        print(f"{status:8} {name}: {detail}; stopped, examined 1 of 7 requirements")
        return 1
    print(f"compared with moxywolf-plugins at {head}")
    for name, status, detail in rows:
        print(f"{status:8} {name}: {detail}")
    ready = sum(s == "ready" for _, s, _ in rows)
    print(f"examined {len(rows)} requirements for {argv[0]}: {ready} ready")
    return 0 if rows and ready == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
