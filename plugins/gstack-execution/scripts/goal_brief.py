#!/usr/bin/env python3
"""GO-001: a goal is a brief Dorian approved, under one objective, and the approval binds to one tree.

  goal_brief.py check <goal dir>        reads DESIGN.md and CODEOWNERS from origin/main, never the
                                        working tree; fails closed if main can't be read
  goal_brief.py baseline <goal dir>     GO-002: runs the goal tests against origin/main; every outcome
                                        test must fail there and every invariant test must pass
  goal_brief.py verify <id> --pr N [--repo owner/name]
                                        needs GITHUB_TOKEN: run it under `agent_token.py exec --`
  goal_brief.py --selftest

`check` parses the brief, the plan and the folder against the limits below, which are the project
charter's limits as code: a brief outside them is refused, not negotiated (criterion 5). It reports
how many sections and files it examined, and examining none is a failure (EV-001). `verify` reads
the approving review through the GitHub API and prints the run-record fields. Formats are in
goals/README.md.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from decimal import Decimal
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".github"))
from test_codeowners import rules  # noqa: E402  one CODEOWNERS parser, not two

OWNER = "dorianatmoxywolf"   # the Release Owner; not a flag, so no caller can name someone else
SECTIONS = ["Serves", "Outcome", "Non-goals", "Scenarios", "Goal tests", "Allowed paths",
            "Spend cap", "Provider budgets", "Max calls", "Max items",
            "Max review rounds per item", "Stop conditions", "Pre-mortem"]
FILES = ["GOAL.md", "PLAN.md", "holdout.sha256"]
NOT_OBJECTIVES = {"Goal", "Constraints and settled decisions", "Boundary tests", "Validation",
                  "Amendments log"}
BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
MONEY = re.compile(r"^\$?(\d+(?:\.\d{1,2})?)$")
INT = re.compile(r"^\d+$")
TEST_ID = re.compile(r"^`?([\w./:\[\]-]+)`?\s*(?:[:(-]\s*)?(outcome|invariant)\)?(?:\s*[:-]\s*.+)?$", re.I)
META = re.compile(r"[*?\[]")


def sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def bullet_lines(name, body, errors):
    """Every non-blank line must be a bullet; an unparsed line is an error, not silently dropped."""
    items = []
    for line in body.splitlines():
        if not line.strip():
            continue
        m = BULLET.match(line)
        if m:
            items.append(m.group(1).strip())
        else:
            errors.append(f"{name}: line is not a '- ' bullet: {line.strip()}")
    return items


def objectives(design_text):
    return [h for h in re.findall(r"^## (.+?)\s*$", design_text, re.M) if h not in NOT_OBJECTIVES]


# --- paths: * stays inside one folder, ** spans folders (GO-004's envelope check uses the same rules)
def to_glob(codeowners_pattern):
    p = codeowners_pattern.lstrip("/")
    return p + "*/**" if p.endswith("/") else p   # a folder rule covers what's inside it, not the folder name


def _seg_overlap(a, b):
    if not META.search(a) and not META.search(b):
        return a == b
    if not META.search(a):
        return fnmatchcase(a, b)
    if not META.search(b):
        return fnmatchcase(b, a)
    return True   # ponytail: two wildcard segments are assumed to overlap; errs toward refusing


def globs_overlap(a, b):
    """Can any path match both globs? Exact for **, conservative for paired wildcards."""
    def go(x, y):
        if not x and not y:
            return True
        if x and x[0] == "**":
            return go(x[1:], y) or (bool(y) and go(x, y[1:]))
        if y and y[0] == "**":
            return go(x, y[1:]) or (bool(x) and go(x[1:], y))
        if not x or not y:
            return False
        return _seg_overlap(x[0], y[0]) and go(x[1:], y[1:])
    return go(a.strip("/").split("/"), b.strip("/").split("/"))


DRAFTED = re.compile(r"^#\s*drafted-by:\s*([a-z0-9][\w.-]*)/(\S+)\s*$", re.I | re.M)
READ_BY = re.compile(r"^\s*read by:\s*([a-z0-9][\w.-]*)/(\S+)\s*$", re.I | re.M)


def goal_tests(brief_body, errors):
    """[(test_id, kind)] from the Goal tests section; test_id is '<file under tests/>::<Class.method>'."""
    out = []
    for t in bullet_lines("Goal tests", brief_body, errors):
        m = TEST_ID.match(t)
        if m:
            out.append((m.group(1), m.group(2).lower()))
        else:
            errors.append(f"Goal tests: expected '<test id> (outcome|invariant)', got: {t}")
    return out


TEST_REF = re.compile(r"tests/[\w.-]+\.py::\w+\.\w+")


_LIST = """import importlib.util, json, re, sys, unittest
sys.dont_write_bytecode = True
out = {}
for path in sys.argv[1:]:
    name = path.rsplit("/", 1)[-1]
    try:
        spec = importlib.util.spec_from_file_location("goal_" + name[:-3], path)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    except BaseException as e:
        out["error:" + name] = repr(e); continue
    stack = [suite]
    while stack:
        t = stack.pop()
        if isinstance(t, unittest.TestSuite):
            stack.extend(t); continue
        if type(t).__name__ == "_FailedTest":
            out["error:" + name] = str(getattr(t, "_exception", "load failed")); continue
        doc = getattr(type(t), t._testMethodName).__doc__ or ""
        m = re.search(r"^\\s*Scenario:\\s*(.+?)\\s*$", doc, re.M)
        out["tests/%s::%s.%s" % (name, type(t).__name__, t._testMethodName)] = m.group(1) if m else ""
print(json.dumps(out))
"""


def test_inventory(goal_dir, errors):
    """Every test unittest itself would run under tests/ (inheritance included), as
    {'tests/<file>.py::<Class>.<method>': scenario or ''}. Each file is loaded in an isolated
    interpreter with nothing but the stdlib on its path: a goal test drives the candidate as a
    separate program through GOAL_CANDIDATE and never imports it, so a file that needs the
    repository to load is refused. Goal tests live directly in tests/; a nested file is refused so
    check, baseline and verify see one set."""
    inv, tests = {}, Path(goal_dir, "tests").resolve()
    if not tests.is_dir():
        return inv
    for f in sorted(tests.rglob("*")):
        if f.is_file() and f.parent != tests and "__pycache__" not in f.relative_to(tests).parts:
            errors.append(f"goal tests live directly in tests/, not in a subfolder: tests/{f.relative_to(tests)}")
    files = [str(f) for f in sorted(tests.glob("*.py"))]
    if not files:
        return inv
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        r = subprocess.run([sys.executable, "-I", "-c", _LIST, *files], cwd=tests, env=env,
                           capture_output=True, text=True, timeout=120)
        found = json.loads(r.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
        errors.append(f"goal tests could not be listed: {e}")
        return inv
    for k, v in sorted(found.items()):
        if k.startswith("error:"):
            errors.append(f"tests/{k[6:]} does not load on its own ({v}); a goal test runs the candidate "
                          f"through GOAL_CANDIDATE and never imports it")
        else:
            inv[k] = v
    return inv


def drafter(goal_dir):
    """The model families named by '# drafted-by:' across tests/*.py (None for a file with no line)."""
    fams = set()
    for f in sorted(Path(goal_dir, "tests").glob("*.py")):
        m = DRAFTED.search(f.read_text())
        fams.add(m.group(1).lower() if m else None)
    return fams

def check(goal_dir, design_text, codeowners_text):
    goal_dir = Path(goal_dir)
    errors, examined = [], 0
    for f in FILES:
        if (goal_dir / f).is_file():
            examined += 1
        else:
            errors.append(f"missing file: {f}")
    tests_dir = goal_dir / "tests"
    if tests_dir.is_dir() and any(tests_dir.iterdir()):
        examined += 1
    else:
        errors.append("missing or empty tests/")
    brief = sections((goal_dir / "GOAL.md").read_text()) if (goal_dir / "GOAL.md").is_file() else {}
    for s in SECTIONS:
        if brief.get(s):
            examined += 1
        else:
            errors.append(f"missing or empty section: {s}")

    if (goal_dir / "holdout.sha256").is_file() and not re.fullmatch(
            r"[0-9a-f]{64}", (goal_dir / "holdout.sha256").read_text().strip()):
        errors.append("holdout.sha256 is not one 64-character lowercase hex SHA-256")

    serves = brief.get("Serves", "")
    if serves and (len(serves.splitlines()) != 1 or serves not in objectives(design_text)):
        errors.append(f"Serves must be exactly one objective heading from main's DESIGN.md, got: {serves}")

    if brief.get("Scenarios"):
        sc = bullet_lines("Scenarios", brief["Scenarios"], errors)
        if not any(re.search(r"\bgiven\b.+\bthen\b", s, re.I) for s in sc):
            errors.append("Scenarios needs at least one 'given ... then ...' line")
        if not any(re.search(r"must never happen", s, re.I) for s in sc):
            errors.append("Scenarios needs at least one 'must never happen' line")

    if brief.get("Goal tests"):
        listed = goal_tests(brief["Goal tests"], errors)                  # F3: malformed lines are errors
        if not listed:
            errors.append("Goal tests lists no test IDs")
        inv = test_inventory(goal_dir, errors)
        scen = set(bullet_lines("Scenarios", brief.get("Scenarios", ""), []))
        for tid, _ in listed:                                             # GO-002.1 and .4
            if tid not in inv:
                errors.append(f"Goal test {tid} is not a unittest TestCase method in tests/ ('tests/<file>.py::<Class>.<method>')")
            elif inv[tid] not in scen:
                errors.append(f"Goal test {tid} needs a 'Scenario:' docstring line that is one of the brief's Scenarios")
        for tid in sorted(set(inv) - {t for t, _ in listed}):            # F7: no unlisted test escapes
            errors.append(f"unittest method {tid} is not listed in Goal tests; every goal test is classified and read")
    if tests_dir.is_dir() and any(tests_dir.glob("*.py")):              # GO-002.1
        fams = drafter(goal_dir)
        if None in fams:
            errors.append("every goal test file needs a '# drafted-by: <family>/<model>' line")
        elif len(fams) > 1:
            errors.append(f"goal tests are drafted by one model family, found {sorted(fams)}")

    owned = [to_glob(p) for p, o in rules(codeowners_text) if o]
    if not owned:
        errors.append("CODEOWNERS on main has no rules; refusing to judge Allowed paths without them")
    for g in bullet_lines("Allowed paths", brief.get("Allowed paths", ""), errors):
        g = g.strip("`")
        hit = next((p for p in owned if globs_overlap(g, p)), None)
        if hit:
            errors.append(f"Allowed path {g} can reach CODEOWNERS path {hit}; a brief only narrows the charter")

    def whole(name, pattern, lo, hi):
        raw = brief.get(name, "").strip()
        m = pattern.match(raw)
        v = Decimal(m.group(1) if m.groups() else m.group()) if m else None
        if v is None or not lo <= v <= hi:
            errors.append(f"{name} must be a number from {lo} to {hi} written plainly, got: {raw or 'nothing'}")
            return None
        return v

    big = Decimal(10) ** 9
    max_items = whole("Max items", INT, 1, 10)
    whole("Max review rounds per item", INT, 1, 3)
    cap = whole("Spend cap", MONEY, Decimal("0.01"), big)
    whole("Max calls", INT, 1, big)
    total = Decimal(0)
    for line in bullet_lines("Provider budgets", brief.get("Provider budgets", ""), errors):
        name, _, amount = line.partition(":")
        m = MONEY.match(amount.strip())
        if not name.strip() or not m or Decimal(m.group(1)) <= 0:
            errors.append(f"Provider budget must read '<provider>: $<positive amount>', got: {line}")
        else:
            total += Decimal(m.group(1))
    if cap is not None and total > cap:
        errors.append(f"Provider budgets sum to ${total}, more than the Spend cap ${cap}")

    if (goal_dir / "PLAN.md").is_file():
        items, cur = [], None
        for line in (goal_dir / "PLAN.md").read_text().splitlines():
            if not line.strip() or (not items and line.startswith("# ")):
                continue                                   # blank lines and one leading title
            if re.match(r"^\d+\.\s+\S", line):           # an item starts at column 0
                cur = [line, 0]
                items.append(cur)
            elif cur and re.match(r"^\s+[-*]\s+\S", line):  # its indented acceptance criteria
                cur[1] += 1
            else:                                          # anything else is refused, never skipped
                errors.append(f"PLAN.md: line is neither a '1. ' item at column 0 nor an indented '- ' criterion under one: {line.strip()}")
        if not items:
            errors.append("PLAN.md lists no numbered items")
        for head, n in items:
            if n == 0:
                errors.append(f"PLAN.md item has no indented acceptance criteria: {head.strip()}")
        if max_items is not None and len(items) > max_items:
            errors.append(f"PLAN.md lists {len(items)} items, more than Max items {max_items}")
    return errors, examined


_HARNESS = """import sys
def _harness(nonce, out, path, name, root):
    import os, importlib.util, unittest
    root = os.path.realpath(root) + os.sep
    hits, busy = [], []
    def guard(event, args):
        if busy or not args or event not in ("open", "ctypes.dlopen") or not isinstance(args[0], (str, bytes)):
            return
        busy.append(1)
        try:
            p = os.path.realpath(os.fsdecode(args[0]))
        finally:
            busy.pop()
        if p.startswith(root) and (event == "ctypes.dlopen" or p.endswith((".py", ".pyc", ".pyo", ".so", ".pyd", ".pth"))):
            hits.append(p)
            raise PermissionError("a goal test runs the candidate as a program and never imports it: " + p)
    sys.addaudithook(guard)
    try:
        s = importlib.util.spec_from_file_location("goal_test", path); m = importlib.util.module_from_spec(s)
        sys.modules["goal_test"] = m; s.loader.exec_module(m)
        c, f = name.split(".", 1); getattr(getattr(m, c), f)
        suite = unittest.defaultTestLoader.loadTestsFromName(name, m)
    except Exception as e:
        print("not_run:", e); sys.exit(3)
    if suite.countTestCases() != 1:
        print("not_run: found", suite.countTestCases()); sys.exit(3)
    r = unittest.TextTestRunner(verbosity=0).run(suite)
    if hits:
        print("not_run: the test loaded candidate code into its own interpreter:", hits[0]); sys.exit(3)
    if r.testsRun - len(r.skipped) != 1:
        print("not_run: ran", r.testsRun - len(r.skipped)); sys.exit(3)
    out.write("\\ngoal-test-result %s %s\\n" % (nonce, "passed" if r.wasSuccessful() else "failed")); out.flush()
_h = _harness
del _harness
_h(sys.stdin.readline().strip(), sys.__stdout__, sys.argv[1], sys.argv[2], sys.argv[3])
"""


def run_test(repo_root, goal_dir, test_id, timeout=300):
    """Run one goal unittest against the candidate in repo_root: 'passed', 'failed', or 'not_run' when
    the named test couldn't be loaded or didn't run exactly once (missing file or name, a file that
    won't load on its own, a timeout), or when the test loaded candidate code into its own interpreter.
    A not_run test examined nothing.

    The candidate never runs in the test's interpreter (GO-002.1, Dorian's decision of 2026-10-02):
    the test runs isolated (-I), from an empty folder, with GOAL_CANDIDATE naming the candidate's
    checkout and an audit hook that refuses to open the candidate's code, so the only way to reach the
    candidate is to run it as a separate program. The verdict is the harness's line carrying a nonce
    read from stdin before the test loads; the exit code decides nothing, and a candidate process,
    which never sees the nonce, can't write a line that counts."""
    path, _, name = test_id.partition("::")
    test_file = Path(goal_dir, path).resolve()          # F1: the goal folder isn't in the main checkout
    if not test_file.is_file():
        return "not_run"
    nonce, root = secrets.token_hex(16), str(Path(repo_root).resolve())
    with tempfile.TemporaryDirectory(prefix="goal-test-") as cwd:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": cwd, "GOAL_CANDIDATE": root, "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            r = subprocess.run([sys.executable, "-I", "-B", "-c", _HARNESS, str(test_file), name, root], cwd=cwd,
                               input=nonce + "\n", env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "not_run"
    mine = [ln.split()[2] for ln in r.stdout.splitlines()
            if ln.startswith("goal-test-result ") and len(ln.split()) == 3 and ln.split()[1] == nonce]
    return mine[0] if len(mine) == 1 and mine[0] in ("passed", "failed") else "not_run"

def baseline(goal_dir, repo_root):
    """GO-002.2: against repo_root (a checkout of main), outcome tests fail and invariant tests pass."""
    errors, examined = [], 0
    brief = sections(Path(goal_dir, "GOAL.md").read_text()) if Path(goal_dir, "GOAL.md").is_file() else {}
    for tid, kind in goal_tests(brief.get("Goal tests", ""), errors):
        result = run_test(repo_root, goal_dir, tid)
        if result == "not_run":                                          # F2: unrun is not a fail
            errors.append(f"goal test {tid} could not be run against main (missing, failed to load, or timed out)")
            continue
        examined += 1
        passed = result == "passed"
        if kind == "outcome" and passed:
            errors.append(f"outcome test {tid} already passes on main; it can't show the goal happened")
        if kind == "invariant" and not passed:
            errors.append(f"invariant test {tid} fails on main; it must hold before and throughout the run")
    if examined == 0:
        errors.append("baseline examined no goal tests")
    return errors, examined


def main_checkout(ref="origin/main"):
    d = tempfile.mkdtemp(prefix="goal-baseline-")
    r = subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach", d, ref], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"cannot check out {ref}: {r.stderr.strip()}. Refusing to baseline against the working tree.")
    return d


def from_main(path, ref="origin/main"):
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{path}"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"cannot read {path} from {ref}; fetch main first. Refusing to check against the working tree.")
    return r.stdout


# --- verify
def github(token):
    def get(path):
        req = urllib.request.Request("https://api.github.com/" + path, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
    return get


def _decode(content_json):
    import base64
    return base64.b64decode(content_json.get("content", "")).decode() if content_json.get("content") else ""


def _tests_text(get, repo, goal_id, ref):
    files = get(f"repos/{repo}/contents/goals/{goal_id}/tests?ref={ref}") or []
    return "\n".join(_decode(get(f"repos/{repo}/contents/{f['path']}?ref={ref}") or {})
                     for f in files if f.get("name", "").endswith(".py"))


def verify(goal_id, pr, repo, get):
    """Criterion 3. Returns (record, errors)."""
    errors = []
    p = get(f"repos/{repo}/pulls/{pr}")
    head, base_sha = p["head"]["sha"], p["base"]["sha"]
    if p["base"]["ref"] != "main":
        errors.append(f"PR #{pr} targets {p['base']['ref']}, not main")
    if not p.get("merged"):
        errors.append(f"PR #{pr} is not merged")
    reviews, page = [], 1
    while True:   # every page: a later decision on page 2 overrides an approval on page 1
        batch = get(f"repos/{repo}/pulls/{pr}/reviews?per_page=100&page={page}") or []
        reviews += batch
        if len(batch) < 100:
            break
        page += 1
    mine = [r for r in reviews if r["user"]["login"] == OWNER
            and r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")]
    last = mine[-1] if mine else None   # his latest decision stands
    if not last or last["state"] != "APPROVED":
        errors.append(f"no standing APPROVED review by {OWNER} on PR #{pr}")
    elif last["commit_id"] != head:
        errors.append(f"{OWNER}'s approval is at {last['commit_id'][:7]}, not the head {head[:7]}")

    def tree(ref):
        listing = get(f"repos/{repo}/contents/goals?ref={ref}") or []
        hit = [e for e in listing if e["name"] == goal_id and e["type"] == "dir"]
        return hit[0]["sha"] if hit else None
    at_head, at_main, at_base = tree(head), tree("main"), tree(base_sha)
    if at_head is None:
        errors.append(f"goals/{goal_id}/ does not exist at the head")
    else:
        if at_base is not None:   # goals are immutable: a changed goal is a new goal folder with its own approval
            errors.append(f"goals/{goal_id}/ already existed before PR #{pr}; the approval must be of the PR that adds it")
        if at_head != at_main:
            errors.append(f"goals/{goal_id}/ on main ({(at_main or 'missing')[:7]}) differs from the approved tree ({at_head[:7]})")
    body = p.get("body") or ""                                       # GO-002.4
    drafted, reader = set(), None
    reading = body.split("## Plain-English reading", 1)
    listing = get(f"repos/{repo}/contents/goals/{goal_id}/GOAL.md?ref={head}") or {}
    ids = [t for t, _ in goal_tests(sections(_decode(listing)).get("Goal tests", ""), [])] if listing else []
    if len(reading) < 2:
        errors.append(f"PR #{pr} has no '## Plain-English reading' section")
    else:
        rd = reading[1].split("\n## ", 1)[0]
        missing = [t for t in ids if t not in set(TEST_REF.findall(rd))]   # F6: whole IDs, not substrings
        if missing:
            errors.append(f"the plain-English reading doesn't cover {missing}")
        m = READ_BY.search(rd)
        drafted = {d.group(1).lower() for d in DRAFTED.finditer(_tests_text(get, repo, goal_id, head))}
        reader = m.group(1).lower() if m else None
        if not m:
            errors.append("the plain-English reading needs a 'Read by: <family>/<model>' line")
        elif m.group(1).lower() in drafted:
            errors.append(f"the reading is by {m.group(1)}, the family that drafted the tests; it must be another family")
    record = {"goal": goal_id, "pr": pr, "review_id": last["id"] if last else None,
              "head": head, "tree": at_head, "drafted_by": sorted(drafted), "read_by": reader}
    return record, errors


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    if argv[:1] == ["check"] and len(argv) == 2:
        errors, examined = check(argv[1], from_main("DESIGN.md"), from_main(".github/CODEOWNERS"))
        print(f"examined {examined} sections and files in {argv[1]}")
        if examined == 0:
            errors.append("examined nothing")
        for e in errors:
            print("FAIL:", e)
        return 1 if errors else 0
    if argv[:1] == ["baseline"] and len(argv) == 2:
        wt = main_checkout()
        try:
            errors, examined = baseline(argv[1], wt)
        finally:
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", wt], capture_output=True)
        print(f"examined {examined} goal tests against origin/main")
        for e in errors:
            print("FAIL:", e)
        return 1 if errors else 0
    if argv[:1] == ["verify"] and len(argv) >= 2:
        args = dict(zip(argv[2::2], argv[3::2]))
        unknown = set(args) - {"--pr", "--repo"}
        token = os.environ.get("GITHUB_TOKEN")
        if unknown or "--pr" not in args or not token:
            print(f"verify takes --pr N [--repo owner/name] and needs GITHUB_TOKEN; refused {sorted(unknown) or ''}")
            return 2
        record, errors = verify(argv[1], int(args["--pr"]), args.get("--repo", "MoxyWolfLLC/moxywolf-plugins"), github(token))
        print(json.dumps(record))
        for e in errors:
            print("FAIL:", e)
        return 1 if errors else 0
    print(__doc__)
    return 2


def selftest():
    assert globs_overlap("plugins/foo/**", to_glob("**/hooks/"))            # ** reaches any hooks folder
    assert not globs_overlap("plugins/foo/*.py", to_glob("**/hooks/"))
    assert globs_overlap(".github/new/**", to_glob("/.github/"))       # a folder that doesn't exist yet
    assert not globs_overlap("plugins/foo/hooks.md", to_glob("**/hooks/"))
    assert not globs_overlap("plugins/foo/a.py", to_glob("/.github/"))
    assert globs_overlap("plugins/*/scripts/peer_review.py", "plugins/gstack-execution/scripts/peer_review.py")
    return print("selftest: 6 checks passed") or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
